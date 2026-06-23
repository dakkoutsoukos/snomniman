"""snomniman.pipeline - the reproducibility engine (depends on processing, core).

Defines the **provenance DAG** (multi-input: sample/reference normalization,
background subtraction, calibration inputs, stitched scans), replay/reconstruction,
JSON (de)serialization, environment/version + operation-version capture, and the
``Project`` bundle. This is the backbone of OHD-5: any result is reconstructable
and auditable from its data sources, provenance graph, steps, parameters, and
software/operation versions.
"""
