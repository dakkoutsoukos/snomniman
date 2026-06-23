"""snomniman - reproducible analysis of s-SNOM and nano-FTIR data.

See ``docs/architecture.md`` for the layered design and ``docs/data-model.md``
for the data model. This top-level package exposes only the version and
intentionally avoids importing heavy or GUI dependencies at import time: the
scientific backend stays free of the Qt toolkit (Rule 4).
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
