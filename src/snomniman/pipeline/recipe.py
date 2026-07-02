"""Processing Recipes (Phase 4A): a named, replayable projection of a provenance chain.

A :class:`Recipe` captures the linear sequence of :class:`~snomniman.processing.ProcessingStep`
applications that produced a dataset - identity + parameters only, never dataset
content - and replays it on another compatible dataset through the exact same
registry + ``ProcessingStep.apply`` path a manual, one-step-at-a-time Preview ->
Accept already uses. This is **not** a second processing engine: capture is a
projection of the existing provenance DAG (the same ``StepRecord`` shape ADR-0030
already produces, with execution-time facts - ``applied_at``, ``software``,
fingerprints - dropped because they describe one past run, not a portable step
identity), and replay is a loop over ``ProcessingStep.apply()``. The result is an
ordinary derived :class:`~snomniman.core.Dataset` with a fresh, correct provenance
DAG - indistinguishable from hand-applying the same steps in order.

Recipes are deliberately restricted to single-``primary``-input chains: today's only
multi-input operation (``image.arithmetic``) binds a measurement-specific
``secondary`` dataset that cannot be captured context-free. Capturing a history that
passes through such a step raises :class:`~snomniman.core.exceptions.ProcessingError`
rather than silently dropping the extra input - see
``docs/phase4-workflow-automation.md`` sec 3.1 for the full analysis, and the Phase 4A
ADR for why this line is drawn here.

Persistence is a standalone ``.snomrecipe`` JSON file (mirroring the ``.snomproj``
manifest's safety pattern - a format tag, a schema version, plain JSON) rather than a
change to the project schema; a recipe is a small, portable artifact independent of
any one project.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from snomniman.core import Dataset, current_software
from snomniman.core.exceptions import ProcessingError, ReaderError
from snomniman.core.provenance import ProvenanceNode
from snomniman.processing import get_step

#: Marks a file as a SNOMNIMAN recipe (guards against loading unrelated JSON).
RECIPE_FORMAT = "snomniman.recipe"

#: Bumped when the recipe JSON layout changes.
RECIPE_SCHEMA_VERSION = 1

#: The conventional file suffix for a saved recipe.
RECIPE_SUFFIX = ".snomrecipe"


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class RecipeStep:
    """One step in a recipe: identity + bound parameters (no execution facts)."""

    step_id: str
    step_version: int
    params: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_version": self.step_version,
            "params": dict(self.params),
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> RecipeStep:
        return RecipeStep(
            step_id=str(data["step_id"]),
            step_version=int(data["step_version"]),
            params=dict(data.get("params", {})),
        )


@dataclass(frozen=True)
class Recipe:
    """A named, ordered, portable sequence of ``ProcessingStep`` applications.

    ``steps`` is oldest-first (the order they are replayed in). A ``Recipe`` is
    immutable; :func:`renamed`, :func:`duplicated`, and :func:`with_step_params`
    return an edited copy rather than mutating in place.
    """

    name: str
    steps: tuple[RecipeStep, ...]
    created_at: str = field(default_factory=_utcnow_iso)
    software: Mapping[str, str] = field(default_factory=current_software)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("a Recipe must have a non-empty name")
        if not self.steps:
            raise ValueError("a Recipe must contain at least one step")

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": RECIPE_FORMAT,
            "schema_version": RECIPE_SCHEMA_VERSION,
            "name": self.name,
            "created_at": self.created_at,
            "software": dict(self.software),
            "steps": [s.to_dict() for s in self.steps],
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> Recipe:
        fmt = data.get("format")
        if fmt != RECIPE_FORMAT:
            raise ReaderError(f"unexpected recipe format {fmt!r}; expected {RECIPE_FORMAT!r}")
        version = data.get("schema_version", 0)
        if not isinstance(version, int) or version > RECIPE_SCHEMA_VERSION:
            raise ReaderError(
                f"recipe schema version {version} is newer than this build supports "
                f"(<= {RECIPE_SCHEMA_VERSION}); upgrade SNOMNIMAN"
            )
        raw_steps = data.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ReaderError("recipe lists no steps")
        return Recipe(
            name=str(data.get("name", "recipe")),
            steps=tuple(RecipeStep.from_dict(s) for s in raw_steps),
            created_at=str(data.get("created_at", _utcnow_iso())),
            software=dict(data.get("software", {})),
        )


def capture_recipe(dataset: Dataset, *, name: str) -> Recipe:
    """Capture *dataset*'s linear processing history as a portable :class:`Recipe`.

    Walks the provenance chain via the ``primary`` input only - the single-input
    lane every registered operation lives in except ``image.arithmetic``. A chain
    that passes through a step bound to anything other than exactly ``primary`` (a
    multi-input step) cannot be captured context-free, so this raises
    :class:`~snomniman.core.exceptions.ProcessingError` rather than silently
    dropping the extra input. Raises the same if *dataset* is raw (no history to
    capture).
    """
    chain: list[ProvenanceNode] = []
    node = dataset.provenance
    while not node.is_raw:
        input_names = tuple(node.inputs)
        if input_names != ("primary",):
            raise ProcessingError(
                f"cannot capture a recipe through step {node.record.step_id!r}: it "
                f"binds input(s) {input_names!r}, not just 'primary' - a portable "
                "recipe covers only single-primary-input chains (see "
                "docs/phase4-workflow-automation.md sec 3.1)"
            )
        chain.append(node)
        node = node.inputs["primary"]
    if not chain:
        raise ProcessingError("dataset has no processing history to capture (it is raw)")
    chain.reverse()
    steps = tuple(
        RecipeStep(n.record.step_id, n.record.step_version, dict(n.record.params))
        for n in chain
    )
    return Recipe(name=name, steps=steps)


def apply_recipe(recipe: Recipe, dataset: Dataset) -> Dataset:
    """Replay *recipe* onto *dataset* through the ordinary ``ProcessingStep`` path.

    Each step is rebuilt from the processing registry and applied via the exact
    ``ProcessingStep.apply()`` call a manual Preview -> Accept uses: parameter
    validation, ``check_compatibility``, and provenance recording are the existing
    per-step contract, unchanged. The result is an ordinary derived
    :class:`~snomniman.core.Dataset` with a fresh, correct provenance DAG -
    indistinguishable from hand-applying the same steps in order. A step that does
    not apply to *dataset* (a missing capability, a failed compatibility check)
    raises :class:`~snomniman.core.exceptions.ProcessingError` naming its position -
    an honest failure, never a silent skip.
    """
    result = dataset
    for index, step in enumerate(recipe.steps):
        try:
            cls = get_step(step.step_id)
            result = cls(**step.params).apply({"primary": result})
        except ProcessingError as exc:
            raise ProcessingError(
                f"recipe {recipe.name!r} step {index} ({step.step_id!r}) did not "
                f"apply: {exc}"
            ) from exc
    return result


def renamed(recipe: Recipe, name: str) -> Recipe:
    """Return a copy of *recipe* under a new name (recipes are immutable)."""
    return replace(recipe, name=name)


def duplicated(recipe: Recipe, name: str) -> Recipe:
    """Return a copy of *recipe* under a new name, captured as of now."""
    return replace(recipe, name=name, created_at=_utcnow_iso())


def with_step_params(recipe: Recipe, index: int, params: Mapping[str, Any]) -> Recipe:
    """Return a copy of *recipe* with step *index*'s parameters replaced.

    The new parameters are revalidated against that step's registered
    ``ProcessingStep`` (the same ``validate`` a manual parameter form uses), so an
    edited recipe cannot silently drift from what the engine will actually accept.
    """
    if not 0 <= index < len(recipe.steps):
        raise ProcessingError(f"recipe {recipe.name!r} has no step at index {index}")
    step = recipe.steps[index]
    validated = get_step(step.step_id).validate(dict(params))
    new_steps = list(recipe.steps)
    new_steps[index] = RecipeStep(step.step_id, step.step_version, validated)
    return replace(recipe, steps=tuple(new_steps))


def save_recipe(recipe: Recipe, path: str | Path, *, overwrite: bool = False) -> Path:
    """Write *recipe* to a ``.snomrecipe`` JSON file at *path*; return the path.

    Raises :class:`FileExistsError` if *path* already exists and ``overwrite`` is
    ``False``.
    """
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"recipe file already exists (overwrite=False): {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(recipe.to_dict(), indent=2), encoding="utf-8")
    return target


def load_recipe(path: str | Path) -> Recipe:
    """Load a ``.snomrecipe`` JSON file written by :func:`save_recipe`.

    Raises :class:`~snomniman.core.exceptions.ReaderError` if *path* is not a
    readable SNOMNIMAN recipe file.
    """
    target = Path(path)
    if not target.is_file():
        raise ReaderError(f"{target} is not a SNOMNIMAN recipe file")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReaderError(f"corrupt recipe file {target}: {exc}") from exc
    if not isinstance(data, dict):
        raise ReaderError(f"corrupt recipe file {target}: not a JSON object")
    return Recipe.from_dict(data)


def delete_recipe(path: str | Path) -> None:
    """Delete a ``.snomrecipe`` file at *path* (a plain, explicit file removal)."""
    target = Path(path)
    if target.is_file():
        target.unlink()


__all__ = [
    "RECIPE_FORMAT",
    "RECIPE_SCHEMA_VERSION",
    "RECIPE_SUFFIX",
    "Recipe",
    "RecipeStep",
    "apply_recipe",
    "capture_recipe",
    "delete_recipe",
    "duplicated",
    "load_recipe",
    "renamed",
    "save_recipe",
    "with_step_params",
]
