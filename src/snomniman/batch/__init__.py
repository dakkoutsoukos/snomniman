"""snomniman.batch - headless multi-dataset runs (depends on pipeline, io, core).

Applies a provenance DAG (or template) across many sources, emitting results, a
per-result provenance record, and a run manifest. Pure backend with no UI, so
batch analysis is fully scriptable and reproducible.
"""
