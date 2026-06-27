"""Step registry: maps step_id -> ProcessingStep class.

Adding a new operation means subclassing :class:`~snomniman.processing.ProcessingStep`
and calling :func:`register` (or using it as a decorator).  The registry
intentionally does *not* use entry-point plugin discovery (Rule 7); steps are
registered explicitly in the package that owns them.
"""

from __future__ import annotations

from snomniman.core.exceptions import ProcessingError

from .step import ProcessingStep

_REGISTRY: dict[str, type[ProcessingStep]] = {}


def register(cls: type[ProcessingStep]) -> type[ProcessingStep]:
    """Register *cls* in the step registry. May be used as a class decorator.

    Raises :exc:`~snomniman.core.ProcessingError` if:

    - ``step_id`` or ``description`` are missing from the class.
    - the ``step_id`` is already registered (catches duplicate registrations
      at import time rather than silently overwriting them).
    """
    if not hasattr(cls, "step_id") or not cls.step_id:
        raise ProcessingError(
            f"Cannot register {cls.__name__!r}: step_id is missing or empty"
        )
    if not hasattr(cls, "description") or not cls.description:
        raise ProcessingError(
            f"Cannot register {cls.__name__!r}: description is missing or empty"
        )
    if cls.step_id in _REGISTRY:
        existing = _REGISTRY[cls.step_id].__name__
        raise ProcessingError(
            f"step_id {cls.step_id!r} is already registered "
            f"(existing class: {existing!r})"
        )
    _REGISTRY[cls.step_id] = cls
    return cls


def get_step(step_id: str) -> type[ProcessingStep]:
    """Return the registered :class:`~snomniman.processing.ProcessingStep` class.

    Raises :exc:`~snomniman.core.ProcessingError` for an unknown *step_id*.
    """
    try:
        return _REGISTRY[step_id]
    except KeyError:
        available = sorted(_REGISTRY)
        raise ProcessingError(
            f"Unknown step {step_id!r}. "
            f"Available: {available}"
        ) from None


def list_steps() -> list[str]:
    """Return a sorted list of all registered ``step_id`` strings."""
    return sorted(_REGISTRY.keys())


__all__ = ["get_step", "list_steps", "register"]
