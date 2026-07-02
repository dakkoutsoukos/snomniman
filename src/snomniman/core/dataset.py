"""The central ``Dataset`` abstraction (data-model.md sec 3).

``Dataset`` wraps an ``xarray.Dataset`` and adds SNOM domain semantics: a
human-facing :class:`DataKind`, derived :class:`Capability` set (hybrid dispatch),
typed :class:`Metadata`, the :class:`RawSource` anchor, and the dataset's node in
the provenance DAG. Each *channel* is an xarray data variable; *coordinates* are
the shared axes.

Raw data is immutable (Rule 5 / ADR-0004): on construction the backing arrays are
made read-only, and operations (later phases) return new datasets rather than
mutating. Amplitude and phase are derived *views* of a complex channel; the
unwrapped phase, when it exists, is a separate first-class channel (OHD-4).
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import xarray as xr

from .capabilities import Capability
from .datakind import DataKind
from .exceptions import DatasetError
from .metadata import Metadata
from .provenance import ProvenanceNode
from .rawsource import RawSource

# Canonical optical/mechanical channel name, optionally reference-prefixed:
# "O2", "M1", "R_O3", "R_M0".
_OM_RE = re.compile(r"^(R_)?(?P<kind>[OM])(?P<order>\d+)$")
_Z_RE = re.compile(r"^(R_)?Z(_[A-Za-z0-9]+)?$")


class Dataset:
    """A SNOM-aware, immutable labeled-array dataset."""

    def __init__(
        self,
        data: xr.Dataset,
        *,
        kind: DataKind,
        metadata: Metadata,
        provenance: ProvenanceNode,
        source: RawSource | None = None,
    ) -> None:
        if not isinstance(data, xr.Dataset):  # defensive; keeps the boundary honest
            raise DatasetError("Dataset must wrap an xarray.Dataset")
        self._data = data
        self._kind = kind
        self._metadata = metadata
        self._provenance = provenance
        self._source = source
        self._capabilities = _derive_capabilities(data)
        _freeze(data)

    # -- core accessors -------------------------------------------------------

    @property
    def kind(self) -> DataKind:
        return self._kind

    @property
    def capabilities(self) -> frozenset[Capability]:
        return self._capabilities

    @property
    def metadata(self) -> Metadata:
        return self._metadata

    @property
    def provenance(self) -> ProvenanceNode:
        return self._provenance

    @property
    def source(self) -> RawSource | None:
        return self._source

    @property
    def data(self) -> xr.Dataset:
        """The backing ``xarray.Dataset`` (read-only arrays). Prefer typed accessors."""
        return self._data

    @property
    def is_raw(self) -> bool:
        """True iff this dataset is a raw import (its provenance is a read node)."""
        return self._provenance.is_raw

    def has_capability(self, capability: Capability) -> bool:
        return capability in self._capabilities

    # -- channels -------------------------------------------------------------

    @property
    def channel_names(self) -> list[str]:
        return [str(name) for name in self._data.data_vars]

    def channels(self, *, role: str | None = None, kind: str | None = None) -> list[str]:
        """Channel names filtered by metadata ``role`` and/or ``kind``."""
        names = []
        for ch in self._metadata.channels:
            if role is not None and ch.role != role:
                continue
            if kind is not None and ch.kind != kind:
                continue
            names.append(ch.canonical)
        return names

    def channel(self, name: str) -> xr.DataArray:
        """Return the channel ``name`` as an ``xarray.DataArray``."""
        try:
            return self._data[name]
        except KeyError as exc:
            raise DatasetError(f"no such channel: {name!r}") from exc

    def is_complex(self, name: str) -> bool:
        return np.iscomplexobj(self.channel(name).data)

    def amplitude(self, name: str) -> xr.DataArray:
        """Amplitude view ``abs(O)`` of a complex channel."""
        da = self.channel(name)
        if not np.iscomplexobj(da.data):
            raise DatasetError(f"channel {name!r} is not complex; has no amplitude view")
        out = abs(da)
        out.attrs = {"unit": "a.u.", "derived_from": name, "quantity": "amplitude"}
        out.name = f"{name}_amplitude"
        return out

    def phase(self, name: str) -> xr.DataArray:
        """Phase view ``angle(O)`` of a complex channel, in radians.

        Equals the imported phase where amplitude > 0 (OHD-6D: no invert / re-ref /
        unwrap / normalize is applied). At exactly-zero amplitude, or at the
        +/-pi wrap boundary, the complex representation cannot distinguish the
        original sample; the raw file remains the source of truth.
        """
        da = self.channel(name)
        if not np.iscomplexobj(da.data):
            raise DatasetError(f"channel {name!r} is not complex; has no phase view")
        values = np.asarray(da.values)
        return xr.DataArray(
            np.arctan2(values.imag, values.real),
            coords=da.coords,
            dims=da.dims,
            name=f"{name}_phase",
            attrs={"unit": "rad", "derived_from": name, "quantity": "phase"},
        )

    # -- coordinates ----------------------------------------------------------

    @property
    def coord_names(self) -> list[str]:
        return [str(name) for name in self._data.coords]

    def coordinate(self, name: str) -> xr.DataArray:
        try:
            return self._data.coords[name]
        except KeyError as exc:
            raise DatasetError(f"no such coordinate: {name!r}") from exc

    def __repr__(self) -> str:
        return (
            f"Dataset(kind={self._kind.value!r}, "
            f"channels={len(self.channel_names)}, "
            f"dims={dict(self._data.sizes)}, "
            f"capabilities={sorted(c.value for c in self._capabilities)})"
        )


def _derive_capabilities(data: xr.Dataset) -> frozenset[Capability]:
    """Derive the capability set from a dataset's coords and channels (ADR-0017)."""
    caps: set[Capability] = set()
    coords = {str(c) for c in data.coords}
    if {"x", "y"} <= coords:
        caps.add(Capability.SPATIAL_2D)
    elif "s" in coords:
        caps.add(Capability.SPATIAL_1D)
    if "wavenumber" in coords:
        caps.add(Capability.SPECTRAL)
    if "opd" in coords:
        caps.add(Capability.INTERFEROMETRIC)

    optical_orders: set[int] = set()
    mechanical_orders: set[int] = set()
    for raw_name, var in data.data_vars.items():
        name = str(raw_name)
        is_reference = name.startswith("R_")
        if is_reference:
            caps.add(Capability.REFERENCE)
        if _Z_RE.match(name):
            caps.add(Capability.TOPOGRAPHY)
            continue
        m = _OM_RE.match(name)
        if m is None:
            continue
        complex_channel = np.iscomplexobj(var.data)
        order = int(m.group("order"))
        if m.group("kind") == "O" and complex_channel:
            caps.add(Capability.COMPLEX_OPTICAL)
            if not is_reference:
                optical_orders.add(order)
        elif m.group("kind") == "M" and complex_channel:
            caps.add(Capability.COMPLEX_MECHANICAL)
            if not is_reference:
                mechanical_orders.add(order)

    if len(optical_orders) > 1 or len(mechanical_orders) > 1:
        caps.add(Capability.MULTI_HARMONIC)
    return frozenset(caps)


def _freeze(data: xr.Dataset) -> None:
    """Make the backing numpy arrays read-only to enforce raw immutability."""
    for name in list(data.data_vars) + list(data.coords):
        arr: Any = data[name].data
        if isinstance(arr, np.ndarray):
            arr.flags.writeable = False


__all__ = ["Dataset"]
