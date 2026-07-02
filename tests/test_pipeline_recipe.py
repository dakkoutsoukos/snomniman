"""Tests for Processing Recipes (Phase 4A): capture, replay, editing, persistence.

Covered:
- Capture from a real single-primary-input history (plane_level -> fix_zero)
- Capture rejects a raw dataset (no history)
- Capture rejects a chain through a multi-input step (image.arithmetic)
- Replay reproduces the same channel values and step-by-step provenance as
  applying the steps manually, one at a time (the golden "replay == manual" test)
- Replay honestly fails (ProcessingError, names the step) when a step does not
  apply to the target dataset
- Recipe JSON round-trip (to_dict/from_dict), including via save_recipe/load_recipe
- renamed / duplicated / with_step_params editing helpers
- with_step_params revalidates against the registered ProcessingStep
- save_recipe respects overwrite=False; load_recipe rejects a non-recipe file
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import snomniman.processing.image  # noqa: F401  (registers image ops)
from snomniman.core import Dataset
from snomniman.core.exceptions import ProcessingError, ReaderError
from snomniman.pipeline import (
    RECIPE_FORMAT,
    Recipe,
    RecipeStep,
    apply_recipe,
    capture_recipe,
    delete_recipe,
    duplicated,
    load_recipe,
    renamed,
    save_recipe,
    with_step_params,
)
from snomniman.processing.image.fix_zero import FixZero
from snomniman.processing.image.plane_level import PlaneLevel


def _manual_chain(dataset: Dataset) -> Dataset:
    leveled = PlaneLevel(channel="Z", order=1).apply({"primary": dataset})
    return FixZero(channel="Z").apply({"primary": leveled})


# --------------------------------------------------------------------------- #
# Capture
# --------------------------------------------------------------------------- #


def test_capture_recipe_from_history(topography_dataset: Dataset) -> None:
    derived = _manual_chain(topography_dataset)
    recipe = capture_recipe(derived, name="topo clean")
    assert recipe.name == "topo clean"
    assert [s.step_id for s in recipe.steps] == ["image.plane_level", "image.fix_zero"]
    assert recipe.steps[0].params == {"channel": "Z", "order": 1}
    assert recipe.steps[1].params["channel"] == "Z"


def test_capture_recipe_rejects_raw_dataset(topography_dataset: Dataset) -> None:
    with pytest.raises(ProcessingError, match="raw"):
        capture_recipe(topography_dataset, name="nothing")


def test_capture_recipe_rejects_multi_input_chain(synthetic_dataset: Dataset) -> None:
    from snomniman.processing.image.arithmetic import Arithmetic

    combined = Arithmetic(channel="O2", mode="a_minus_b").apply(
        {"primary": synthetic_dataset, "secondary": synthetic_dataset}
    )
    with pytest.raises(ProcessingError, match="cannot capture a recipe"):
        capture_recipe(combined, name="bad")


# --------------------------------------------------------------------------- #
# Replay
# --------------------------------------------------------------------------- #


def test_replay_matches_manual_channel_values(topography_dataset: Dataset) -> None:
    manual = _manual_chain(topography_dataset)
    recipe = Recipe(
        name="topo clean",
        steps=(
            RecipeStep("image.plane_level", 1, {"channel": "Z", "order": 1}),
            RecipeStep("image.fix_zero", 1, {"channel": "Z"}),
        ),
    )
    replayed = apply_recipe(recipe, topography_dataset)
    np.testing.assert_allclose(
        replayed.channel("Z").values, manual.channel("Z").values
    )


def test_replay_produces_equivalent_provenance_chain(topography_dataset: Dataset) -> None:
    manual = _manual_chain(topography_dataset)
    recipe = capture_recipe(manual, name="topo clean")
    replayed = apply_recipe(recipe, topography_dataset)

    manual_ids = [n.record.step_id for n in manual.provenance.iter_nodes()]
    replayed_ids = [n.record.step_id for n in replayed.provenance.iter_nodes()]
    assert manual_ids == replayed_ids

    manual_params = [dict(n.record.params) for n in manual.provenance.iter_nodes()]
    replayed_params = [dict(n.record.params) for n in replayed.provenance.iter_nodes()]
    assert manual_params == replayed_params


def test_replay_reports_which_step_failed(topography_dataset: Dataset) -> None:
    # reference_normalize needs a complex optical + reference channel; topography_dataset
    # (Z only) lacks both, so this must fail honestly, naming the step.
    recipe = Recipe(name="bad", steps=(RecipeStep("image.reference_normalize", 1, {}),))
    with pytest.raises(ProcessingError, match=r"step 0 \('image\.reference_normalize'\)"):
        apply_recipe(recipe, topography_dataset)


def test_replay_unknown_step_id_raises(topography_dataset: Dataset) -> None:
    recipe = Recipe(name="bad", steps=(RecipeStep("image.does_not_exist", 1, {}),))
    with pytest.raises(ProcessingError):
        apply_recipe(recipe, topography_dataset)


# --------------------------------------------------------------------------- #
# Editing helpers
# --------------------------------------------------------------------------- #


def test_renamed_returns_new_recipe_with_new_name() -> None:
    recipe = Recipe(name="a", steps=(RecipeStep("image.fix_zero", 1, {"channel": "Z"}),))
    renamed_recipe = renamed(recipe, "b")
    assert renamed_recipe.name == "b"
    assert recipe.name == "a"  # original untouched
    assert renamed_recipe.steps == recipe.steps


def test_duplicated_returns_independent_copy() -> None:
    recipe = Recipe(name="a", steps=(RecipeStep("image.fix_zero", 1, {"channel": "Z"}),))
    dup = duplicated(recipe, "a copy")
    assert dup.name == "a copy"
    assert dup.steps == recipe.steps
    assert dup is not recipe


def test_with_step_params_revalidates_against_registry() -> None:
    recipe = Recipe(
        name="a", steps=(RecipeStep("image.plane_level", 1, {"channel": "Z", "order": 1}),)
    )
    edited = with_step_params(recipe, 0, {"channel": "Z", "order": 2})
    assert edited.steps[0].params == {"channel": "Z", "order": 2}
    assert recipe.steps[0].params == {"channel": "Z", "order": 1}  # original untouched


def test_with_step_params_rejects_invalid_params() -> None:
    recipe = Recipe(
        name="a", steps=(RecipeStep("image.plane_level", 1, {"channel": "Z", "order": 1}),)
    )
    with pytest.raises(ProcessingError):
        with_step_params(recipe, 0, {"channel": "Z", "order": "not a number"})


def test_with_step_params_rejects_out_of_range_index() -> None:
    recipe = Recipe(
        name="a", steps=(RecipeStep("image.plane_level", 1, {"channel": "Z", "order": 1}),)
    )
    with pytest.raises(ProcessingError, match="no step at index"):
        with_step_params(recipe, 5, {"channel": "Z", "order": 1})


# --------------------------------------------------------------------------- #
# JSON (de)serialization + file persistence
# --------------------------------------------------------------------------- #


def test_recipe_to_dict_from_dict_round_trip() -> None:
    recipe = Recipe(
        name="topo clean",
        steps=(
            RecipeStep("image.plane_level", 1, {"channel": "Z", "order": 1}),
            RecipeStep("image.fix_zero", 1, {"channel": "Z"}),
        ),
    )
    data = json.loads(json.dumps(recipe.to_dict()))
    restored = Recipe.from_dict(data)
    assert restored.name == recipe.name
    assert restored.steps == recipe.steps
    assert data["format"] == RECIPE_FORMAT


def test_from_dict_rejects_wrong_format() -> None:
    with pytest.raises(ReaderError):
        Recipe.from_dict({"format": "not.a.recipe", "steps": []})


def test_from_dict_rejects_newer_schema_version() -> None:
    with pytest.raises(ReaderError, match="newer"):
        Recipe.from_dict(
            {
                "format": RECIPE_FORMAT,
                "schema_version": 999,
                "steps": [{"step_id": "image.fix_zero", "step_version": 1, "params": {}}],
            }
        )


def test_save_and_load_recipe_round_trip(tmp_path: Path) -> None:
    recipe = Recipe(
        name="topo clean",
        steps=(RecipeStep("image.plane_level", 1, {"channel": "Z", "order": 1}),),
    )
    path = save_recipe(recipe, tmp_path / "topo.snomrecipe")
    assert path.is_file()
    loaded = load_recipe(path)
    assert loaded.name == recipe.name
    assert loaded.steps == recipe.steps


def test_save_recipe_refuses_overwrite_by_default(tmp_path: Path) -> None:
    recipe = Recipe(name="a", steps=(RecipeStep("image.fix_zero", 1, {"channel": "Z"}),))
    path = tmp_path / "a.snomrecipe"
    save_recipe(recipe, path)
    with pytest.raises(FileExistsError):
        save_recipe(recipe, path)
    save_recipe(recipe, path, overwrite=True)  # does not raise


def test_load_recipe_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ReaderError):
        load_recipe(tmp_path / "missing.snomrecipe")


def test_load_recipe_rejects_corrupt_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.snomrecipe"
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(ReaderError):
        load_recipe(path)


def test_delete_recipe_removes_file(tmp_path: Path) -> None:
    recipe = Recipe(name="a", steps=(RecipeStep("image.fix_zero", 1, {"channel": "Z"}),))
    path = save_recipe(recipe, tmp_path / "a.snomrecipe")
    delete_recipe(path)
    assert not path.exists()


def test_delete_recipe_is_a_no_op_if_missing(tmp_path: Path) -> None:
    delete_recipe(tmp_path / "missing.snomrecipe")  # does not raise


# --------------------------------------------------------------------------- #
# Construction guards
# --------------------------------------------------------------------------- #


def test_recipe_requires_at_least_one_step() -> None:
    with pytest.raises(ValueError, match="at least one step"):
        Recipe(name="empty", steps=())


def test_recipe_requires_non_empty_name() -> None:
    with pytest.raises(ValueError, match="non-empty name"):
        Recipe(name="  ", steps=(RecipeStep("image.fix_zero", 1, {"channel": "Z"}),))
