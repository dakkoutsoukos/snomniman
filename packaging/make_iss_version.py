"""Generate ``packaging/version.iss`` (an Inno Setup include) from
``pyproject.toml``'s version, so the installer's version string, the frozen
exe's version resource (``make_version_info.py``), and the app's own
provenance-recorded version are one identity (deployment-strategy.md
Section 6). Rerun manually whenever ``pyproject.toml``'s version changes,
then rebuild the installer.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def main() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = pyproject["project"]["version"]
    out = REPO_ROOT / "packaging" / "version.iss"
    out.write_text(f'#define MyAppVersion "{version}"\n', encoding="utf-8")
    print(f"wrote {out} (version {version})")


if __name__ == "__main__":
    main()
