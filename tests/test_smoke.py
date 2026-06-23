"""Smoke tests: the package imports, and the backend stays GUI-free.

The GUI-free check encodes Rule 4 (scientific functionality must not depend on
the Qt toolkit) as an executable invariant, even before backend code exists.
"""

import importlib
import sys

import snomniman

BACKEND_PACKAGES = [
    "snomniman.core",
    "snomniman.io",
    "snomniman.processing",
    "snomniman.pipeline",
    "snomniman.viz",
    "snomniman.batch",
]

# Top-level modules that would indicate the GUI toolkit leaked into the backend.
GUI_TOPLEVEL = {"PySide6", "PyQt5", "PyQt6", "shiboken6", "pyqtgraph"}


def test_version_present() -> None:
    assert isinstance(snomniman.__version__, str)
    assert snomniman.__version__


def test_backend_imports() -> None:
    for name in BACKEND_PACKAGES:
        importlib.import_module(name)


def test_backend_is_qt_free() -> None:
    """Importing the backend must not pull in the GUI toolkit (Rule 4)."""
    for name in BACKEND_PACKAGES:
        importlib.import_module(name)
    leaked = sorted(m for m in sys.modules if m.split(".")[0] in GUI_TOPLEVEL)
    assert not leaked, f"Backend pulled in GUI libraries: {leaked}"
