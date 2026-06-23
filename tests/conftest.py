"""Shared pytest configuration and fixtures.

``src`` is on the import path via ``[tool.pytest.ini_options] pythonpath`` in
``pyproject.toml``, so tests can ``import snomniman`` without an editable install.

Synthetic-data fixtures with analytically known answers (Rule 6) and golden-file
fixtures for the neaSNOM reader will live here as the Phase 1 vertical slice lands.
"""
