"""Launch the Measurement Explorer (the GUI entry point).

Usage: ``python -m snomniman.gui [measurement-directory]``. With no path, a folder
chooser opens. This is the only place a Qt event loop is started; everything it
shows is produced by the read-only backend + model.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pyqtgraph as pg
from PySide6 import QtWidgets

from snomniman.core.exceptions import ReaderError
from snomniman.pipeline import MANIFEST_NAME, load_project

from .model import ExplorerModel
from .window import MeasurementExplorerWindow


def _configure() -> None:
    pg.setConfigOptions(
        imageAxisOrder="row-major",  # data is (y, x); matches the lower-left convention
        antialias=True,
        background="#111317",
        foreground="#c8c8c8",
    )


def run(path: str | None = None, *, argv: list[str] | None = None) -> int:
    """Open ``path`` (or prompt) in the Explorer and run the Qt event loop."""
    _configure()
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(argv if argv is not None else sys.argv)

    if path is None:
        path = QtWidgets.QFileDialog.getExistingDirectory(
            None, "Open neaSNOM measurement directory"
        )
        if not path:
            return 0

    try:
        window = _open(path)
    except ReaderError as exc:
        QtWidgets.QMessageBox.critical(None, "Could not open", str(exc))
        return 1

    window.resize(1180, 760)
    window.show()
    return int(app.exec())


def _open(path: str) -> MeasurementExplorerWindow:
    """Open ``path`` as a saved project (if it is one) or a raw measurement directory."""
    if (Path(path) / MANIFEST_NAME).is_file():
        project = load_project(path)
        window = MeasurementExplorerWindow(ExplorerModel(project.current))
        window.load_project_object(project)
        window._project_path = Path(path)
        return window
    return MeasurementExplorerWindow(ExplorerModel.open_measurement(path))


__all__ = ["run"]
