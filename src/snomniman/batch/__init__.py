"""snomniman.batch - headless multi-measurement recipe runs (Phase 4B, depends on
pipeline, io, core).

Replays a single :class:`~snomniman.pipeline.Recipe` across many measurements,
independently. This is deliberately **not** a second automation system: each
measurement is processed through the unchanged
:func:`~snomniman.pipeline.apply_recipe` - the exact call a single, manual
"select this measurement, replay this recipe" already makes (Phase 4A, ADR-0031).
Batch adds only the loop, a per-measurement outcome, and a run summary; it computes
no new science and introduces no new provenance semantics.

A measurement the recipe does not apply to is recorded as **skipped** (with the
engine's own explanation) rather than aborting the run; an unexpected error while
replaying is recorded as **failed** (also without aborting the run) so one bad
measurement never costs the rest of the batch its results. Execution is local,
serial, and deterministic (Rule 1: no parallelism ahead of a measured need) - a
caller may request an early, clean stop between measurements (never mid-measurement)
via ``should_stop``, and may observe live progress via ``on_progress``.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime

from snomniman.core.exceptions import ProcessingError
from snomniman.pipeline import Measurement, Recipe, apply_recipe

#: This measurement's recipe replay completed and produced a new derived dataset.
STATUS_SUCCESS = "success"
#: The recipe does not apply to this measurement (an honest, expected incompatibility -
#: a missing capability/channel, a failed compatibility check) - the same
#: :exc:`~snomniman.core.exceptions.ProcessingError` a manual replay would raise.
STATUS_SKIPPED = "skipped"
#: An unexpected error occurred while replaying (not a recognized incompatibility) -
#: recorded, not silently swallowed, so it stays visible without aborting the batch.
STATUS_FAILED = "failed"


@dataclass(frozen=True)
class BatchOutcome:
    """The result of replaying a recipe on one measurement."""

    measurement_id: str
    title: str
    status: str  # STATUS_SUCCESS | STATUS_SKIPPED | STATUS_FAILED
    reason: str | None = None  # populated for STATUS_SKIPPED / STATUS_FAILED
    measurement: Measurement | None = None  # the updated measurement, on success only


@dataclass(frozen=True)
class BatchResult:
    """The outcome of running one recipe across many measurements."""

    recipe_name: str
    requested: int  # how many measurements were selected for this run
    outcomes: tuple[BatchOutcome, ...] = field(default_factory=tuple)  # processed so far
    started_at: str = ""
    elapsed_seconds: float = 0.0
    stopped_early: bool = False  # True iff `should_stop` ended the run before `requested`

    @property
    def succeeded(self) -> tuple[BatchOutcome, ...]:
        return tuple(o for o in self.outcomes if o.status == STATUS_SUCCESS)

    @property
    def skipped(self) -> tuple[BatchOutcome, ...]:
        return tuple(o for o in self.outcomes if o.status == STATUS_SKIPPED)

    @property
    def failed(self) -> tuple[BatchOutcome, ...]:
        return tuple(o for o in self.outcomes if o.status == STATUS_FAILED)


#: Called after each measurement with ``(completed_count, total, latest_outcome)``.
ProgressCallback = Callable[[int, int, BatchOutcome], None]


def run_batch(
    recipe: Recipe,
    measurements: Sequence[Measurement],
    *,
    on_progress: ProgressCallback | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> BatchResult:
    """Replay *recipe* on every measurement in *measurements*, independently.

    Each measurement is processed through the unchanged
    :func:`~snomniman.pipeline.apply_recipe`, applied to that measurement's own
    **current** (active) dataset - identical to selecting that one measurement and
    replaying the recipe by hand. On success, the derived dataset is appended to a
    *copy* of that measurement's history (the input ``measurements`` are never
    mutated); the caller is responsible for adopting the updated
    :class:`~snomniman.pipeline.Measurement` from the outcome. A measurement the
    recipe does not apply to is **skipped** (reason explained, not aborted); an
    unexpected error is recorded as **failed** (also not aborted) - one bad
    measurement never costs the rest of the batch its results.

    *on_progress*, if given, is called after each measurement with
    ``(completed_count, total, outcome)`` so a caller can report live progress on a
    long-running batch. *should_stop*, if given, is checked **between**
    measurements (never mid-measurement) - a clean, deterministic early stop, not a
    parallel cancellation.
    """
    started = datetime.now(UTC)
    t0 = time.monotonic()
    outcomes: list[BatchOutcome] = []
    total = len(measurements)
    stopped_early = False
    for i, measurement in enumerate(measurements, start=1):
        if should_stop is not None and should_stop():
            stopped_early = True
            break
        outcome = _run_one(recipe, measurement)
        outcomes.append(outcome)
        if on_progress is not None:
            on_progress(i, total, outcome)
    elapsed = time.monotonic() - t0
    return BatchResult(
        recipe_name=recipe.name,
        requested=total,
        outcomes=tuple(outcomes),
        started_at=started.isoformat(),
        elapsed_seconds=elapsed,
        stopped_early=stopped_early,
    )


def _run_one(recipe: Recipe, measurement: Measurement) -> BatchOutcome:
    try:
        derived = apply_recipe(recipe, measurement.current)
    except ProcessingError as exc:
        return BatchOutcome(
            measurement_id=measurement.measurement_id,
            title=measurement.title,
            status=STATUS_SKIPPED,
            reason=str(exc),
        )
    except Exception as exc:  # a genuinely unexpected error must not abort the batch
        return BatchOutcome(
            measurement_id=measurement.measurement_id,
            title=measurement.title,
            status=STATUS_FAILED,
            reason=f"{type(exc).__name__}: {exc}",
        )
    updated = replace(
        measurement,
        datasets=(*measurement.datasets, derived),
        current_index=len(measurement.datasets),
    )
    return BatchOutcome(
        measurement_id=measurement.measurement_id,
        title=measurement.title,
        status=STATUS_SUCCESS,
        measurement=updated,
    )


__all__ = [
    "STATUS_FAILED",
    "STATUS_SKIPPED",
    "STATUS_SUCCESS",
    "BatchOutcome",
    "BatchResult",
    "ProgressCallback",
    "run_batch",
]
