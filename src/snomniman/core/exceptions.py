"""Typed exceptions for the scientific backend.

Backend code raises these (never bare ``Exception``); the GUI layer translates
them into user-facing messages (architecture.md sec 8). ``core`` depends on
nothing internal, so these live at the base of the dependency graph.
"""

from __future__ import annotations


class SnomnimanError(Exception):
    """Base class for all SNOMNIMAN backend errors."""


class ReaderError(SnomnimanError):
    """A vendor file or measurement directory could not be read or parsed."""


class DatasetError(SnomnimanError):
    """A ``Dataset`` was constructed or queried in an invalid way."""


class MetadataError(SnomnimanError):
    """Metadata was malformed or violated a stored scientific convention."""


class ProcessingError(SnomnimanError):
    """A processing step was invalid, mis-parameterized, or failed to execute."""


__all__ = [
    "DatasetError",
    "MetadataError",
    "ProcessingError",
    "ReaderError",
    "SnomnimanError",
]
