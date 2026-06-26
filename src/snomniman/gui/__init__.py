"""snomniman.gui - the desktop application (PySide6 + PyQtGraph).

Depends on the backend packages; nothing in the backend depends on it. Contains
only presentation and interaction logic - views, widgets, dialogs, event
handlers - and **no scientific computation** (Rule 4). It builds processing
steps / provenance graphs and calls the backend to do the work. Requires the
optional ``gui`` dependency group (``uv sync --extra gui``).

Implemented so far - the **read-only Measurement Explorer** (the first user-facing
experience): :mod:`~snomniman.gui.model` (the Qt-free ``ExplorerModel`` presenter),
the widgets (:mod:`~snomniman.gui.imageview`, :mod:`~snomniman.gui.panels`,
:mod:`~snomniman.gui.window`), :mod:`~snomniman.gui.colormap`, and the entry point
(:mod:`~snomniman.gui.app`; ``python -m snomniman.gui [dir]``). It opens, browses,
and inspects a measurement without modifying it. **Importing this package does not
import Qt** (only the submodules that need it do), so the Qt-free presenter and the
backend stay importable without the ``gui`` extra. Every GUI feature must satisfy
Rule 9 (it must improve a researcher's understanding of a measurement).
"""
