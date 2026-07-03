"""Smoke tests: the package imports, and the backend stays GUI-free.

The GUI-free check encodes Rule 4 (scientific functionality must not depend on
the Qt toolkit) as an executable invariant.
"""

import importlib
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import snomniman

BACKEND_PACKAGES = [
    "snomniman.core",
    "snomniman.io",
    "snomniman.processing",
    "snomniman.describe",
    "snomniman.diagnostics",
    "snomniman.ai",
    "snomniman.knowledge",
    "snomniman.manual",
    "snomniman.pipeline",
    "snomniman.viz",
    "snomniman.batch",
]

# Top-level modules that would indicate the GUI toolkit leaked into the backend.
GUI_TOPLEVEL = {"PySide6", "PyQt5", "PyQt6", "shiboken6", "pyqtgraph"}

_SRC = Path(__file__).resolve().parents[1] / "src"


def test_version_present() -> None:
    assert isinstance(snomniman.__version__, str)
    assert snomniman.__version__


def test_backend_imports() -> None:
    for name in BACKEND_PACKAGES:
        importlib.import_module(name)


def test_backend_is_qt_free() -> None:
    """A fresh process importing only the backend must not pull in the GUI toolkit.

    Run in a subprocess so the result is independent of any GUI test that may have
    imported Qt earlier in this pytest session: the invariant is about what the
    backend *itself* imports, not the ambient process state. This strengthens (it
    does not weaken) Rule 4's executable guarantee.
    """
    packages = ", ".join(repr(p) for p in BACKEND_PACKAGES)
    gui = ", ".join(repr(g) for g in sorted(GUI_TOPLEVEL))
    code = textwrap.dedent(
        f"""
        import importlib, sys
        for name in [{packages}]:
            importlib.import_module(name)
        gui = {{{gui}}}
        leaked = sorted(m for m in sys.modules if m.split('.')[0] in gui)
        print(",".join(leaked))
        sys.exit(1 if leaked else 0)
        """
    )
    env = {**os.environ, "PYTHONPATH": str(_SRC) + os.pathsep + os.environ.get("PYTHONPATH", "")}
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, check=False
    )
    assert result.returncode == 0, (
        f"Backend pulled in GUI libraries: {result.stdout.strip()} {result.stderr.strip()}"
    )
