# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for SNOMNIMAN (deployment-strategy.md Phase 1).

Build with (from the repo root, packaging env synced via
``uv sync --extra gui --group packaging``):

    .venv/Scripts/pyinstaller.exe packaging/snomniman.spec --noconfirm

Produces a one-directory build at ``packaging/dist/SNOMNIMAN/`` whose entry
point is ``SNOMNIMAN.exe``. See docs/packaging-notes.md for the reasoning
behind every non-default option below.
"""

import os

block_cipher = None

# SPECPATH is injected by PyInstaller: the absolute directory containing this
# spec file (packaging/), regardless of the caller's current directory.
REPO_ROOT = os.path.dirname(SPECPATH)
SRC = os.path.join(REPO_ROOT, "src")
ENTRY = os.path.join(SPECPATH, "snomniman_entry.py")
ICON = os.path.join(SPECPATH, "snomniman.ico")
VERSION_FILE = os.path.join(SPECPATH, "version_info.txt")

a = Analysis(
    [ENTRY],
    pathex=[SRC],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SNOMNIMAN",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=ICON,
    version=VERSION_FILE,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="SNOMNIMAN",
)
