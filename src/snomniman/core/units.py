"""Canonical units and explicit conversion helpers (ADR-0008, OHD-6B).

The canonical spatial/length unit is **nanometers (nm)**: every spatial
coordinate (x, y, s, z, opd) and every length-valued quantity (e.g. topography
height) is stored in nm. Original vendor units are preserved in metadata and any
conversion applied to data is recorded in provenance.

Units are tracked as lightweight metadata plus the conversion helpers here;
``pint`` is deliberately deferred behind this chokepoint (ADR-0008). The
nonlinear wavenumber<->wavelength relation is intentionally *not* hidden in a
generic converter.
"""

from __future__ import annotations

from .exceptions import MetadataError

#: Canonical spatial/length unit for all coordinates and length quantities.
SPATIAL_UNIT = "nm"

#: Canonical spectral unit (wavenumber). Not a length; never auto-converted to nm.
WAVENUMBER_UNIT = "cm-1"

# Multiplicative factors converting a named length unit to nanometers. Both the
# micro sign (U+00B5) and the Greek small mu (U+03BC) are accepted for microns.
_LENGTH_TO_NM: dict[str, float] = {
    "m": 1.0e9,
    "meter": 1.0e9,
    "metre": 1.0e9,
    "cm": 1.0e7,
    "mm": 1.0e6,
    "um": 1.0e3,
    "µm": 1.0e3,  # micro sign
    "μm": 1.0e3,  # greek mu
    "micron": 1.0e3,
    "microns": 1.0e3,
    "nm": 1.0,
}


def length_scale_to_nm(unit: str) -> float:
    """Return the factor that converts ``unit`` to nanometers.

    Raises ``MetadataError`` for an unknown unit rather than guessing, so a
    silent mis-scaling can never occur.
    """
    key = unit.strip()
    try:
        return _LENGTH_TO_NM[key]
    except KeyError as exc:
        raise MetadataError(
            f"unknown length unit {unit!r}; cannot convert to canonical nm"
        ) from exc


def length_to_nm(value: float, unit: str) -> float:
    """Convert a single length ``value`` given in ``unit`` to nanometers."""
    return value * length_scale_to_nm(unit)


__all__ = [
    "SPATIAL_UNIT",
    "WAVENUMBER_UNIT",
    "length_scale_to_nm",
    "length_to_nm",
]
