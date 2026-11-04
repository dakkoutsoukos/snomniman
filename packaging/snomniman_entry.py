"""PyInstaller freeze entry point for the SNOMNIMAN desktop application.

Not a package module (kept outside ``src/snomniman`` on purpose) - PyInstaller
analyzes a plain script, and a script that lives inside a package cannot use
relative imports when run directly (``snomniman.gui.__main__`` does, for the
``python -m snomniman.gui`` dev workflow). This file is the one place the
frozen build and the dev workflow diverge; both end up calling the same
``snomniman.gui.app.run`` (see docs/packaging-notes.md).
"""

from __future__ import annotations

import sys

from snomniman.gui.app import run

if __name__ == "__main__":
    sys.exit(run(sys.argv[1] if len(sys.argv) > 1 else None))
