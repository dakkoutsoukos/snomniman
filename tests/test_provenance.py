"""Unit tests for the provenance DAG value objects and (de)serialization."""

from __future__ import annotations

import json

from snomniman.core import (
    ProvenanceNode,
    RawSource,
    StepRecord,
    deserialize_dag,
    serialize_dag,
)
from snomniman.core.provenance import current_software


def _source(name: str, sha: str) -> RawSource:
    return RawSource(path=f"data/{name}", sha256=sha, reader="neasnom.image.gsf.v1")


def _read_node(node_id: str, src: RawSource) -> ProvenanceNode:
    rec = StepRecord(step_id="io.read", step_version=1, deterministic=True)
    return ProvenanceNode(node_id=node_id, record=rec, sources={"source": src})


def _normalize_dag() -> ProvenanceNode:
    """A multi-input DAG: normalize(sample, reference) -> one output node."""
    sample = _read_node("n1", _source("sample.gsf", "a" * 64))
    reference = _read_node("n2", _source("ref.gsf", "b" * 64))
    norm = StepRecord(
        step_id="image.normalize",
        step_version=1,
        deterministic=True,
        params={"channel": "O2"},
    )
    return ProvenanceNode(
        node_id="n3",
        record=norm,
        inputs={"sample": sample, "reference": reference},
    )


def test_read_node_is_raw_processing_node_is_not() -> None:
    dag = _normalize_dag()
    assert dag.is_raw is False
    sample = dag.inputs["sample"]
    assert sample.is_raw is True


def test_multi_input_dag_supported() -> None:
    dag = _normalize_dag()
    assert set(dag.inputs) == {"sample", "reference"}
    # Two distinct sources reachable from the output.
    assert len(list(dag.iter_sources())) == 2
    # Three nodes total (two reads + one normalize).
    assert len(list(dag.iter_nodes())) == 3


def test_serialize_structure() -> None:
    data = serialize_dag(_normalize_dag())
    assert data["root"] == "n3"
    assert len(data["sources"]) == 2
    assert len(data["nodes"]) == 3
    norm_node = next(n for n in data["nodes"] if n["id"] == "n3")
    assert norm_node["inputs"] == {"sample": "n1", "reference": "n2"}
    assert norm_node["step_id"] == "image.normalize"
    read_node = next(n for n in data["nodes"] if n["id"] == "n1")
    assert set(read_node["sources"].values()) <= {s["id"] for s in data["sources"]}


def test_serialize_roundtrip_through_json() -> None:
    dag = _normalize_dag()
    encoded = json.dumps(serialize_dag(dag))
    rebuilt = deserialize_dag(json.loads(encoded))
    # The rebuilt graph serializes identically (stable, lossless).
    assert serialize_dag(rebuilt) == serialize_dag(dag)
    assert rebuilt.node_id == "n3"
    assert rebuilt.inputs["reference"].sources["source"].sha256 == "b" * 64


def test_deterministic_flag_recorded() -> None:
    rec = StepRecord(step_id="x", step_version=2, deterministic=False)
    assert rec.deterministic is False
    assert rec.step_version == 2


def test_software_versions_captured() -> None:
    sw = current_software()
    assert "snomniman" in sw
    assert "numpy" in sw
    assert "xarray" in sw
    # A StepRecord captures versions by default (OHD-5 traceability).
    assert "numpy" in StepRecord(step_id="x", step_version=1, deterministic=True).software
