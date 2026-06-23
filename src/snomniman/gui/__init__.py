"""snomniman.gui - the desktop application (PySide6 + PyQtGraph).

Depends on the backend packages; nothing in the backend depends on it. Contains
only presentation and interaction logic - views, widgets, dialogs, event
handlers - and **no scientific computation** (Rule 4). It builds processing
steps / provenance graphs and calls the backend to do the work. Requires the
optional ``gui`` dependency group. (Not part of the Phase 1 vertical slice.)
"""
