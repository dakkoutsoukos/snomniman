"""Tests for the processing engine: ParameterSpec, ProcessingStep ABC, registry.

Synthetic operations are defined here for white-box testing of the framework
machinery.  They are NOT registered in the global registry; tests that need
registration manipulate the registry via monkeypatch so the global state is
never polluted.

Covered:
- Operation registration (register, get_step, list_steps)
- Duplicate-registration guard
- Unknown step lookup guard
- Parameter validation (valid, missing required, wrong type, unknown extra)
- Step with no parameters
- Optional parameters with defaults
- Dataset immutability (input arrays unchanged and still frozen after apply)
- Empty inputs guard
- Provenance: StepRecord content (step_id, version, params, deterministic,
  software, inputs map)
- Multi-input provenance (both input nodes referenced by name)
- Source is None for derived datasets
- is_raw is False for derived datasets
- params dict is JSON-serializable
- params round-trip (JSON -> reconstruct -> same step)
- Full provenance DAG serializes / deserializes after a processing step
"""

from __future__ import annotations

import json
from collections.abc import Mapping

import numpy as np
import pytest
import xarray as xr

from snomniman.core import DataKind, Dataset, Metadata, deserialize_dag, serialize_dag
from snomniman.core.exceptions import ProcessingError
from snomniman.processing import (
    InputSpec,
    ParameterSpec,
    ProcessingStep,
    get_step,
    list_steps,
    register,
)
from snomniman.processing import registry as _reg_module

# ---------------------------------------------------------------------------
# Synthetic operations (unregistered; framework testing only)
# ---------------------------------------------------------------------------


class _AddConstant(ProcessingStep):
    """Add a real scalar to every channel. Single input named ``"primary"``."""

    step_id = "test.add_constant"
    version = 1
    description = "Add a scalar constant to every channel (testing only)."
    deterministic = True

    @classmethod
    def param_specs(cls) -> list[ParameterSpec]:
        return [ParameterSpec("constant", "Value to add.", (float,))]

    def _execute(
        self, inputs: Mapping[str, Dataset]
    ) -> tuple[xr.Dataset, DataKind, Metadata]:
        primary = inputs["primary"]
        raw = primary.data
        new_vars: dict[str, xr.DataArray] = {}
        for raw_name, var in raw.data_vars.items():
            name = str(raw_name)
            arr = np.array(var.values, copy=True) + self._params["constant"]
            new_vars[name] = xr.DataArray(
                arr, coords=var.coords, dims=var.dims, attrs=dict(var.attrs)
            )
        new_data = xr.Dataset(new_vars, coords=raw.coords, attrs=dict(raw.attrs))
        return new_data, primary.kind, primary.metadata


class _ScaleOptional(ProcessingStep):
    """Multiply every channel by a scale factor; scale defaults to 1.0."""

    step_id = "test.scale_optional"
    version = 2
    description = "Scale every channel by a factor (testing only)."
    deterministic = True

    @classmethod
    def param_specs(cls) -> list[ParameterSpec]:
        return [
            ParameterSpec("scale", "Multiplicative factor.", (float,), required=False, default=1.0),
        ]

    def _execute(
        self, inputs: Mapping[str, Dataset]
    ) -> tuple[xr.Dataset, DataKind, Metadata]:
        primary = inputs["primary"]
        raw = primary.data
        scale: float = self._params["scale"]
        new_vars: dict[str, xr.DataArray] = {}
        for raw_name, var in raw.data_vars.items():
            name = str(raw_name)
            arr = np.array(var.values, copy=True) * scale
            new_vars[name] = xr.DataArray(
                arr, coords=var.coords, dims=var.dims, attrs=dict(var.attrs)
            )
        new_data = xr.Dataset(new_vars, coords=raw.coords, attrs=dict(raw.attrs))
        return new_data, primary.kind, primary.metadata


class _NoParams(ProcessingStep):
    """A step with no parameters at all (e.g. a normalisation with fixed behaviour)."""

    step_id = "test.no_params"
    version = 1
    description = "Identity transform with no parameters (testing only)."
    deterministic = True

    def _execute(
        self, inputs: Mapping[str, Dataset]
    ) -> tuple[xr.Dataset, DataKind, Metadata]:
        primary = inputs["primary"]
        return primary.data, primary.kind, primary.metadata


class _CombineAdd(ProcessingStep):
    """Add channels from two named inputs (multi-input testing)."""

    step_id = "test.combine_add"
    version = 1
    description = "Add corresponding channels of two datasets (testing only)."
    deterministic = True

    @classmethod
    def input_specs(cls) -> list[InputSpec]:
        return [InputSpec("a", "First addend."), InputSpec("b", "Second addend.")]

    def _execute(
        self, inputs: Mapping[str, Dataset]
    ) -> tuple[xr.Dataset, DataKind, Metadata]:
        a = inputs["a"]
        b = inputs["b"]
        new_vars: dict[str, xr.DataArray] = {}
        for raw_name, var in a.data.data_vars.items():
            name = str(raw_name)
            if name in b.data.data_vars:
                arr = np.array(var.values, copy=True) + np.array(
                    b.data[name].values, copy=True
                )
                new_vars[name] = xr.DataArray(
                    arr, coords=var.coords, dims=var.dims, attrs=dict(var.attrs)
                )
        new_data = xr.Dataset(new_vars, coords=a.data.coords, attrs=dict(a.data.attrs))
        return new_data, a.kind, a.metadata


# ---------------------------------------------------------------------------
# Fixture: a fresh registry for each test that touches it
# ---------------------------------------------------------------------------


@pytest.fixture()
def clean_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate the global step registry for each test."""
    monkeypatch.setattr(_reg_module, "_REGISTRY", {})


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


def test_register_makes_step_discoverable(clean_registry: None) -> None:
    register(_AddConstant)
    assert get_step("test.add_constant") is _AddConstant


def test_registered_step_appears_in_list(clean_registry: None) -> None:
    register(_AddConstant)
    register(_NoParams)
    steps = list_steps()
    assert "test.add_constant" in steps
    assert "test.no_params" in steps
    assert steps == sorted(steps)  # list_steps is sorted


def test_duplicate_registration_raises(clean_registry: None) -> None:
    register(_AddConstant)
    with pytest.raises(ProcessingError, match="already registered"):
        register(_AddConstant)


def test_missing_step_id_raises(clean_registry: None) -> None:
    class _Bad(ProcessingStep):
        step_id = ""
        description = "missing step_id"
        deterministic = True

        def _execute(  # pragma: no cover
            self, inputs: Mapping[str, Dataset]
        ) -> tuple[xr.Dataset, DataKind, Metadata]:
            raise NotImplementedError

    with pytest.raises(ProcessingError, match="step_id is missing or empty"):
        register(_Bad)


def test_missing_description_raises(clean_registry: None) -> None:
    class _Bad(ProcessingStep):
        step_id = "test.no_description"
        description = ""
        deterministic = True

        def _execute(  # pragma: no cover
            self, inputs: Mapping[str, Dataset]
        ) -> tuple[xr.Dataset, DataKind, Metadata]:
            raise NotImplementedError

    with pytest.raises(ProcessingError, match="description is missing or empty"):
        register(_Bad)


def test_get_unknown_step_raises() -> None:
    with pytest.raises(ProcessingError, match="Unknown step"):
        get_step("this.step.does.not.exist.ever.12345")


# ---------------------------------------------------------------------------
# Parameter validation tests
# ---------------------------------------------------------------------------


def test_valid_params_accepted() -> None:
    step = _AddConstant(constant=3.0)
    assert step.params == {"constant": 3.0}


def test_missing_required_param_raises() -> None:
    with pytest.raises(ProcessingError, match="required parameter"):
        _AddConstant()


def test_wrong_param_type_raises() -> None:
    with pytest.raises(ProcessingError, match="must be one of"):
        _AddConstant(constant="not_a_float")


def test_unknown_param_raises() -> None:
    with pytest.raises(ProcessingError, match="unknown parameter"):
        _AddConstant(constant=1.0, extra=99)


def test_no_params_step_accepts_nothing() -> None:
    step = _NoParams()
    assert step.params == {}


def test_no_params_step_rejects_anything() -> None:
    with pytest.raises(ProcessingError, match="unknown parameter"):
        _NoParams(constant=1.0)


def test_optional_param_uses_default() -> None:
    step = _ScaleOptional()
    assert step.params["scale"] == 1.0


def test_optional_param_accepts_explicit_value() -> None:
    step = _ScaleOptional(scale=2.5)
    assert step.params["scale"] == 2.5


def test_int_accepted_for_int_float_type() -> None:
    class _IntOrFloat(ProcessingStep):
        step_id = "test._int_or_float"
        description = "int or float param test"
        deterministic = True

        @classmethod
        def param_specs(cls) -> list[ParameterSpec]:
            return [ParameterSpec("value", "Int or float.", (int, float))]

        def _execute(  # pragma: no cover
            self, inputs: Mapping[str, Dataset]
        ) -> tuple[xr.Dataset, DataKind, Metadata]:
            raise NotImplementedError

    step = _IntOrFloat(value=5)  # int
    assert step.params["value"] == 5
    step2 = _IntOrFloat(value=5.0)  # float
    assert step2.params["value"] == 5.0


def test_validate_classmethod_is_callable_directly() -> None:
    result = _AddConstant.validate({"constant": 7.0})
    assert result == {"constant": 7.0}


# ---------------------------------------------------------------------------
# apply() / immutability / provenance tests
# ---------------------------------------------------------------------------


def test_apply_returns_dataset(synthetic_dataset: Dataset) -> None:
    step = _AddConstant(constant=1.0)
    result = step.apply({"primary": synthetic_dataset})
    assert isinstance(result, Dataset)


def test_apply_does_not_mutate_input_values(synthetic_dataset: Dataset) -> None:
    ch = synthetic_dataset.channel_names[0]
    original = synthetic_dataset.channel(ch).values.copy()

    _AddConstant(constant=99.0).apply({"primary": synthetic_dataset})

    np.testing.assert_array_equal(synthetic_dataset.channel(ch).values, original)


def test_input_arrays_remain_frozen_after_apply(synthetic_dataset: Dataset) -> None:
    _AddConstant(constant=1.0).apply({"primary": synthetic_dataset})
    ch = synthetic_dataset.channel_names[0]
    arr = synthetic_dataset.channel(ch).data
    assert isinstance(arr, np.ndarray)
    assert not arr.flags.writeable


def test_result_is_not_same_object_as_input(synthetic_dataset: Dataset) -> None:
    result = _AddConstant(constant=0.0).apply({"primary": synthetic_dataset})
    assert result is not synthetic_dataset


def test_apply_empty_inputs_raises(synthetic_dataset: Dataset) -> None:
    with pytest.raises(ProcessingError, match="inputs must not be empty"):
        _AddConstant(constant=1.0).apply({})


def test_result_values_differ_from_input(synthetic_dataset: Dataset) -> None:
    # Z is a real float channel; adding 100 nm should change values
    original_z = synthetic_dataset.channel("Z").values.copy()
    result = _AddConstant(constant=100.0).apply({"primary": synthetic_dataset})
    result_z = result.channel("Z").values
    assert not np.allclose(result_z, original_z)


# ---------------------------------------------------------------------------
# Provenance tests
# ---------------------------------------------------------------------------


def test_provenance_step_id(synthetic_dataset: Dataset) -> None:
    result = _AddConstant(constant=5.0).apply({"primary": synthetic_dataset})
    assert result.provenance.record.step_id == "test.add_constant"


def test_provenance_step_version(synthetic_dataset: Dataset) -> None:
    result = _AddConstant(constant=5.0).apply({"primary": synthetic_dataset})
    assert result.provenance.record.step_version == 1


def test_provenance_step_version_class_var(synthetic_dataset: Dataset) -> None:
    result = _ScaleOptional(scale=2.0).apply({"primary": synthetic_dataset})
    assert result.provenance.record.step_version == 2


def test_provenance_params_recorded(synthetic_dataset: Dataset) -> None:
    result = _AddConstant(constant=5.25).apply({"primary": synthetic_dataset})
    assert result.provenance.record.params == {"constant": 5.25}


def test_provenance_deterministic_flag(synthetic_dataset: Dataset) -> None:
    result = _AddConstant(constant=1.0).apply({"primary": synthetic_dataset})
    assert result.provenance.record.deterministic is True


def test_provenance_software_captured(synthetic_dataset: Dataset) -> None:
    result = _AddConstant(constant=1.0).apply({"primary": synthetic_dataset})
    sw = result.provenance.record.software
    assert "snomniman" in sw
    assert "numpy" in sw


def test_provenance_inputs_reference_parent_node(synthetic_dataset: Dataset) -> None:
    result = _AddConstant(constant=1.0).apply({"primary": synthetic_dataset})
    assert "primary" in result.provenance.inputs
    assert result.provenance.inputs["primary"] is synthetic_dataset.provenance


def test_result_is_not_raw(synthetic_dataset: Dataset) -> None:
    result = _AddConstant(constant=1.0).apply({"primary": synthetic_dataset})
    assert not result.is_raw


def test_source_is_none_for_derived_dataset(synthetic_dataset: Dataset) -> None:
    result = _AddConstant(constant=1.0).apply({"primary": synthetic_dataset})
    assert result.source is None


def test_multi_input_both_nodes_referenced(synthetic_dataset: Dataset) -> None:
    result = _CombineAdd().apply({"a": synthetic_dataset, "b": synthetic_dataset})
    node = result.provenance
    assert "a" in node.inputs
    assert "b" in node.inputs
    assert node.inputs["a"] is synthetic_dataset.provenance
    assert node.inputs["b"] is synthetic_dataset.provenance


def test_multi_input_provenance_step_id(synthetic_dataset: Dataset) -> None:
    result = _CombineAdd().apply({"a": synthetic_dataset, "b": synthetic_dataset})
    assert result.provenance.record.step_id == "test.combine_add"


def test_default_input_spec_is_single_primary() -> None:
    specs = _AddConstant.input_specs()
    assert [s.name for s in specs] == ["primary"]


def test_multi_input_step_declares_its_slots() -> None:
    assert [s.name for s in _CombineAdd.input_specs()] == ["a", "b"]


def test_apply_rejects_inputs_that_do_not_match_declared_slots(
    synthetic_dataset: Dataset,
) -> None:
    # _CombineAdd declares slots {"a", "b"}; passing the single-input convention fails.
    with pytest.raises(ProcessingError, match=r"expected input\(s\) \['a', 'b'\]"):
        _CombineAdd().apply({"primary": synthetic_dataset})


def test_apply_enforces_check_compatibility(synthetic_dataset: Dataset) -> None:
    class _PickyCombine(_CombineAdd):
        step_id = "test.picky_combine"

        def check_compatibility(self, inputs: Mapping[str, Dataset]) -> tuple[str, ...]:
            return ("inputs are never compatible (test).",)

    with pytest.raises(ProcessingError, match="incompatible inputs - inputs are never"):
        _PickyCombine().apply({"a": synthetic_dataset, "b": synthetic_dataset})


def test_check_compatibility_default_is_empty(synthetic_dataset: Dataset) -> None:
    assert _AddConstant(constant=1.0).check_compatibility({"primary": synthetic_dataset}) == ()


def test_chained_steps_build_dag(synthetic_dataset: Dataset) -> None:
    step1 = _AddConstant(constant=1.0)
    result1 = step1.apply({"primary": synthetic_dataset})

    step2 = _AddConstant(constant=2.0)
    result2 = step2.apply({"primary": result1})

    # result2's provenance points to result1's provenance, which points to
    # synthetic_dataset's provenance
    assert result2.provenance.inputs["primary"] is result1.provenance
    assert result1.provenance.inputs["primary"] is synthetic_dataset.provenance


def test_node_ids_are_unique(synthetic_dataset: Dataset) -> None:
    step = _AddConstant(constant=1.0)
    r1 = step.apply({"primary": synthetic_dataset})
    r2 = step.apply({"primary": synthetic_dataset})
    assert r1.provenance.node_id != r2.provenance.node_id


# ---------------------------------------------------------------------------
# Serialization tests
# ---------------------------------------------------------------------------


def test_params_are_json_serializable(synthetic_dataset: Dataset) -> None:
    step = _AddConstant(constant=2.5)
    json.dumps(step.params)  # must not raise


def test_params_round_trip_via_json(synthetic_dataset: Dataset) -> None:
    step = _AddConstant(constant=7.5)
    restored_params = json.loads(json.dumps(step.params))
    step2 = _AddConstant(**restored_params)
    assert step2.params == step.params


def test_provenance_dag_serializes_after_step(synthetic_dataset: Dataset) -> None:
    result = _AddConstant(constant=3.0).apply({"primary": synthetic_dataset})
    serialized = serialize_dag(result.provenance)
    rebuilt = deserialize_dag(serialized)
    assert rebuilt.record.step_id == result.provenance.record.step_id
    assert rebuilt.record.params == result.provenance.record.params


def test_chained_dag_serializes(synthetic_dataset: Dataset) -> None:
    r1 = _AddConstant(constant=1.0).apply({"primary": synthetic_dataset})
    r2 = _AddConstant(constant=2.0).apply({"primary": r1})
    serialized = serialize_dag(r2.provenance)
    rebuilt = deserialize_dag(serialized)
    # 3 nodes: raw read + step1 + step2
    nodes = list(rebuilt.iter_nodes())
    assert len(nodes) == 3
    assert rebuilt.record.step_id == "test.add_constant"
    assert rebuilt.record.params == {"constant": 2.0}
