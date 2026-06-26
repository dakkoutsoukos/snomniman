"""Provenance value objects: the multi-input DAG (data-model.md sec 8; OHD-2/5).

Provenance is a **directed acyclic graph**, not a linear chain: a step may take
multiple *named* inputs, each resolving to another node or a :class:`RawSource`.
This represents sample/reference normalization, background subtraction,
calibration inputs, and stitched scans. The Phase-1 reader uses a single
``io.read`` node, but the schema supports multi-input from the start.

These are pure data (no dependency on ``processing``) so ``core`` stays at the
base of the dependency graph. Serialization here produces the project-graph JSON
described in data-model.md sec 9.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib import metadata
from typing import Any

from .rawsource import RawSource

#: Schema version for the serialized provenance graph.
GRAPH_SCHEMA_VERSION = 1

#: Step id used for the raw-import node produced by a reader.
READ_STEP_ID = "io.read"

# Libraries whose versions are captured for traceability (OHD-5).
_TRACKED_PACKAGES = ("snomniman", "numpy", "scipy", "xarray", "zarr")


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def current_software() -> dict[str, str]:
    """Capture versions of SNOMNIMAN and key scientific libraries (OHD-5)."""
    out: dict[str, str] = {}
    for name in _TRACKED_PACKAGES:
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:  # pragma: no cover - env dependent
            out[name] = "unknown"
    return out


@dataclass(frozen=True)
class StepRecord:
    """An immutable record of one operation applied in the provenance graph."""

    step_id: str
    step_version: int
    deterministic: bool
    params: Mapping[str, Any] = field(default_factory=dict)
    applied_at: str = field(default_factory=_utcnow_iso)
    software: Mapping[str, str] = field(default_factory=current_software)
    input_fingerprint: str | None = None
    output_fingerprint: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class ProvenanceNode:
    """A node in the provenance DAG: one :class:`StepRecord` plus its inputs.

    ``inputs`` are named upstream nodes (enabling multi-input operations);
    ``sources`` are named :class:`RawSource` leaves (populated for ``io.read``).
    """

    node_id: str
    record: StepRecord
    inputs: Mapping[str, ProvenanceNode] = field(default_factory=dict)
    sources: Mapping[str, RawSource] = field(default_factory=dict)

    @property
    def is_raw(self) -> bool:
        """True iff this is a bare read node (no upstream processing steps)."""
        return self.record.step_id == READ_STEP_ID and not self.inputs

    def iter_nodes(self) -> Iterator[ProvenanceNode]:
        """Yield every node reachable from here (this node last), each once."""
        seen: set[str] = set()
        yield from _walk(self, seen)

    def iter_sources(self) -> Iterator[RawSource]:
        """Yield every distinct :class:`RawSource` in the reachable graph."""
        seen: set[tuple[str, str]] = set()
        for node in self.iter_nodes():
            for src in node.sources.values():
                key = (src.path, src.sha256)
                if key not in seen:
                    seen.add(key)
                    yield src


def _walk(node: ProvenanceNode, seen: set[str]) -> Iterator[ProvenanceNode]:
    if node.node_id in seen:
        return
    seen.add(node.node_id)
    for parent in node.inputs.values():
        yield from _walk(parent, seen)
    yield node


def serialize_dag(root: ProvenanceNode) -> dict[str, Any]:
    """Serialize the DAG reachable from ``root`` to project-graph JSON."""
    source_ids: dict[tuple[str, str], str] = {}
    sources_out: list[dict[str, Any]] = []
    nodes_out: list[dict[str, Any]] = []

    for node in root.iter_nodes():
        src_refs: dict[str, str] = {}
        for name, src in node.sources.items():
            key = (src.path, src.sha256)
            if key not in source_ids:
                sid = f"src_{len(sources_out)}"
                source_ids[key] = sid
                sources_out.append({"id": sid, **src.to_dict()})
            src_refs[name] = source_ids[key]
        rec = node.record
        nodes_out.append(
            {
                "id": node.node_id,
                "step_id": rec.step_id,
                "step_version": rec.step_version,
                "deterministic": rec.deterministic,
                "inputs": {name: p.node_id for name, p in node.inputs.items()},
                "sources": src_refs,
                "params": dict(rec.params),
                "applied_at": rec.applied_at,
                "input_fingerprint": rec.input_fingerprint,
                "output_fingerprint": rec.output_fingerprint,
                "software": dict(rec.software),
                "notes": rec.notes,
            }
        )

    return {
        "schema_version": GRAPH_SCHEMA_VERSION,
        "root": root.node_id,
        "sources": sources_out,
        "nodes": nodes_out,
        "environment": current_software(),
    }


def deserialize_dag(data: Mapping[str, Any]) -> ProvenanceNode:
    """Rebuild a DAG from :func:`serialize_dag` output; returns the root node."""
    sources_by_id = {s["id"]: RawSource.from_dict(s) for s in data["sources"]}
    raw_nodes = {n["id"]: n for n in data["nodes"]}
    built: dict[str, ProvenanceNode] = {}

    def build(node_id: str) -> ProvenanceNode:
        if node_id in built:
            return built[node_id]
        n = raw_nodes[node_id]
        inputs = {name: build(pid) for name, pid in n.get("inputs", {}).items()}
        srcs = {name: sources_by_id[sid] for name, sid in n.get("sources", {}).items()}
        record = StepRecord(
            step_id=n["step_id"],
            step_version=n["step_version"],
            deterministic=n["deterministic"],
            params=dict(n.get("params", {})),
            applied_at=n["applied_at"],
            software=dict(n.get("software", {})),
            input_fingerprint=n.get("input_fingerprint"),
            output_fingerprint=n.get("output_fingerprint"),
            notes=n.get("notes"),
        )
        node = ProvenanceNode(node_id=node_id, record=record, inputs=inputs, sources=srcs)
        built[node_id] = node
        return node

    return build(data["root"])


__all__ = [
    "GRAPH_SCHEMA_VERSION",
    "READ_STEP_ID",
    "ProvenanceNode",
    "StepRecord",
    "current_software",
    "deserialize_dag",
    "serialize_dag",
]
