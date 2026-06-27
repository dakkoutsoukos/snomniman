"""ProcessingStep ABC and ParameterSpec - the command pattern for operations.

Every scientific transformation (leveling, normalization, phase unwrap,
filtering, masking, crop, ...) is a :class:`ProcessingStep` subclass. Steps
are both *data* (step_id, version, params) and *behaviour* (apply). The data
half is JSON-serializable; behaviour is recovered from the step registry -
making the provenance DAG both executable and persistable
(architecture.md sec 4.2, ADR-0005).

Invariants
----------
- :meth:`ProcessingStep.apply` never mutates its input Datasets.
- :meth:`ProcessingStep.apply` always returns a new Dataset whose provenance
  records this step as a :class:`~snomniman.core.StepRecord`.
- ``params`` are JSON-serializable Python scalars (str, int, float, bool, None).
  No NumPy scalars or ndarrays.

Preview model
-------------
The processing engine has no special preview state - it is purely functional.
To preview a step before committing, call :meth:`apply` on a spatially-cropped
copy of the input Dataset (a sliced xr.Dataset); render the result; if the
researcher accepts, call :meth:`apply` on the full Dataset. The slice and the
full application are identical in behaviour - no extra flags needed.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, Final

import xarray as xr

from snomniman.core import (
    Capability,
    DataKind,
    Dataset,
    Metadata,
    ProvenanceNode,
    StepRecord,
    current_software,
)
from snomniman.core.exceptions import ProcessingError

#: ``channel_role`` values: a ``str`` parameter that names a dataset channel.
#: They let a consumer (e.g. the Explorer's generic operation form) offer a
#: channel picker filtered to the channels the operation can actually accept -
#: scientific knowledge that therefore lives with the operation, not the GUI
#: (Rule 4). They do not affect :meth:`ProcessingStep.validate` (the dataset is
#: not available then); each step still validates the chosen channel in
#: ``_execute``.
CHANNEL_ANY: Final = "any"  #: any channel of the dataset
CHANNEL_REAL: Final = "real"  #: real-valued channels only (e.g. topography Z)
CHANNEL_COMPLEX: Final = "complex"  #: complex channels only (e.g. optical O{n})

_CHANNEL_ROLES: Final = frozenset({CHANNEL_ANY, CHANNEL_REAL, CHANNEL_COMPLEX})


@dataclass(frozen=True)
class ParameterSpec:
    """Declares one parameter accepted by a :class:`ProcessingStep`.

    ``py_type`` is a tuple of accepted Python types, passed directly to
    :func:`isinstance`.  Use a single-element tuple for one type::

        ParameterSpec("order", "Harmonic order.", (int,))
        ParameterSpec("value", "A real number.", (int, float))

    ``choices`` and ``channel_role`` are optional, declarative *UI hints* that
    let a generic parameter editor build the right control without any
    operation-specific code:

    - ``choices`` - a fixed set of allowed values (an enum). When set, a value
      outside it is rejected by :meth:`validate`, and a consumer renders a
      selector rather than a free field.
    - ``channel_role`` - one of :data:`CHANNEL_ANY` / :data:`CHANNEL_REAL` /
      :data:`CHANNEL_COMPLEX`; marks a ``str`` parameter as naming a channel of
      that kind, so a consumer can offer a channel picker filtered to the
      channels the operation accepts (the operation still validates in
      ``_execute``).

    Both default to ``None`` (no hint); they never change an operation's
    computed result.
    """

    name: str
    description: str
    py_type: tuple[type[Any], ...]
    required: bool = True
    default: Any = None
    choices: tuple[Any, ...] | None = None
    channel_role: str | None = None

    def __post_init__(self) -> None:
        if self.channel_role is not None and self.channel_role not in _CHANNEL_ROLES:
            raise ValueError(
                f"ParameterSpec {self.name!r}: channel_role must be one of "
                f"{sorted(_CHANNEL_ROLES)} or None, got {self.channel_role!r}"
            )


class ProcessingStep(ABC):
    """Abstract base class for all SNOMNIMAN processing operations.

    **How to implement a step:**

    1. Subclass :class:`ProcessingStep`.
    2. Set the four class variables (``step_id``, ``version``,
       ``description``, ``deterministic``).
    3. Override :meth:`param_specs` if the step has parameters.
    4. Implement :meth:`_execute`.
    5. Register with :func:`snomniman.processing.register`.

    **Class variables (required on every concrete subclass)**

    ``step_id``
        Stable, dot-namespaced identifier (e.g. ``"image.plane_level"``).
        Never change a published step_id; create a new one instead.

    ``version``
        Monotonically increasing int. Bump whenever ``_execute`` behaviour
        changes so the provenance record can distinguish the implementations.

    ``description``
        One sentence for the UI and provenance panel.

    ``deterministic``
        ``True`` iff identical params + identical input arrays always produce
        bit-identical output.  Set ``False`` for steps that call random
        algorithms, external solvers, or AI inference.

    ``required_capabilities``
        The :class:`~snomniman.core.Capability` values a Dataset must have for
        this step to apply (hybrid dispatch, ADR-0017). A dataset supports the
        step iff its capabilities are a superset. Empty (the default) means the
        step has no structural prerequisites. This declaration is *data* - it is
        read by :mod:`snomniman.diagnostics` to report applicability without
        running anything; ``apply`` still validates its own preconditions.
    """

    step_id: ClassVar[str]
    version: ClassVar[int] = 1
    description: ClassVar[str]
    deterministic: ClassVar[bool] = True
    required_capabilities: ClassVar[tuple[Capability, ...]] = ()

    def __init__(self, **params: Any) -> None:
        self._params: dict[str, Any] = type(self).validate(params)

    @property
    def params(self) -> dict[str, Any]:
        """JSON-serializable parameter dict (frozen copy)."""
        return dict(self._params)

    @classmethod
    def param_specs(cls) -> Sequence[ParameterSpec]:
        """Declare the parameters this step accepts. Empty = no parameters."""
        return []

    @classmethod
    def validate(cls, params: Mapping[str, Any]) -> dict[str, Any]:
        """Validate *params* against :meth:`param_specs`; return filled dict.

        Raises :exc:`~snomniman.core.ProcessingError` for:

        - unknown parameter names
        - wrong Python type
        - missing required parameter
        """
        step_name = getattr(cls, "step_id", cls.__name__)
        specs: dict[str, ParameterSpec] = {s.name: s for s in cls.param_specs()}

        out: dict[str, Any] = {}
        for name, spec in specs.items():
            if not spec.required:
                out[name] = spec.default

        unknown = sorted(set(params) - set(specs))
        if unknown:
            raise ProcessingError(
                f"{step_name}: unknown parameter(s) {unknown!r}; "
                f"accepted: {sorted(specs)}"
            )

        for name, value in params.items():
            spec = specs[name]
            if not isinstance(value, spec.py_type):
                raise ProcessingError(
                    f"{step_name}: parameter {name!r} must be "
                    f"one of {spec.py_type!r}, got {type(value).__name__!r}"
                )
            if spec.choices is not None and value not in spec.choices:
                raise ProcessingError(
                    f"{step_name}: parameter {name!r} must be one of "
                    f"{list(spec.choices)!r}, got {value!r}"
                )
            out[name] = value

        missing = [
            name
            for name, spec in specs.items()
            if spec.required and name not in params
        ]
        if missing:
            raise ProcessingError(
                f"{step_name}: required parameter(s) {missing!r} not provided"
            )

        return out

    def apply(self, inputs: Mapping[str, Dataset]) -> Dataset:
        """Apply this step to *inputs*; return a new immutable Dataset.

        *inputs* is a ``{name: Dataset}`` mapping. Single-input steps use
        ``{"primary": dataset}``; multi-input steps (e.g. reference
        normalization) name their inputs according to their semantics
        (``{"sample": s, "reference": r}``).

        The returned Dataset's :attr:`~snomniman.core.Dataset.provenance`
        records this step and references all input provenance nodes. Input
        Datasets are never modified.
        """
        if not inputs:
            raise ProcessingError(
                f"{type(self).step_id}: inputs must not be empty"
            )

        result_data, result_kind, result_metadata = self._execute(inputs)

        input_nodes: dict[str, ProvenanceNode] = {
            name: ds.provenance for name, ds in inputs.items()
        }
        record = StepRecord(
            step_id=type(self).step_id,
            step_version=type(self).version,
            deterministic=type(self).deterministic,
            params=self._params,
            software=current_software(),
        )
        node = ProvenanceNode(
            node_id=str(uuid.uuid4()),
            record=record,
            inputs=input_nodes,
        )
        return Dataset(
            result_data,
            kind=result_kind,
            metadata=result_metadata,
            provenance=node,
            source=None,
        )

    @abstractmethod
    def _execute(
        self, inputs: Mapping[str, Dataset]
    ) -> tuple[xr.Dataset, DataKind, Metadata]:
        """Run the operation on *inputs*; return ``(array_data, kind, metadata)``.

        Rules:
        - Never modify any input Dataset or its backing arrays.
        - Return a fresh :class:`xarray.Dataset` with valid coordinates.
        - Access validated params via ``self._params``.
        """


__all__ = [
    "CHANNEL_ANY",
    "CHANNEL_COMPLEX",
    "CHANNEL_REAL",
    "ParameterSpec",
    "ProcessingStep",
]
