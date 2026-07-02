"""Shared neaSNOM vendor-header parsing (``#``-prefixed ``.txt`` parameter files).

Both the imaging reader (:mod:`snomniman.io.neasnom`) and the point-spectroscopy
reader (:mod:`snomniman.io.neasnom_spectrum`) read the same header grammar - a
block of ``# Label:\t[unit]\tvalue\t...`` lines - ahead of format-specific data
(a grid of ``.gsf`` files, or a tab-delimited spectra table). Centralizing the
grammar here keeps the two readers from silently drifting apart.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from snomniman.core import length_scale_to_nm

__all__ = [
    "is_wavenumber_unit",
    "num",
    "pair_to_nm",
    "parse_date",
    "parse_param_file",
    "str_value",
    "txt_index",
]


def parse_param_file(path: Path) -> dict[str, Any]:
    """Parse the neaSNOM ``.txt`` header into verbatim lines + ordered records."""
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    records: list[dict[str, Any]] = []
    for line in raw_lines:
        if not line.startswith("#"):
            continue
        content = line[1:].strip()
        if not content:
            continue
        parts = [p.strip() for p in content.split("\t")]
        label = parts[0].rstrip(":").strip()
        unit: str | None = None
        values: list[str] = []
        for tok in parts[1:]:
            if not tok:
                continue
            if unit is None and not values and tok.startswith("[") and tok.endswith("]"):
                unit = tok[1:-1]
            else:
                values.append(tok)
        records.append({"label": label, "unit": unit, "values": values})
    return {"lines": raw_lines, "records": records}


def txt_index(txt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {r["label"]: r for r in txt["records"]}


def num(rec: dict[str, Any] | None, i: int = 0) -> float | None:
    if rec is None:
        return None
    values = rec["values"]
    if i >= len(values):
        return None
    try:
        return float(values[i].replace(",", ""))
    except ValueError:
        return None


def str_value(rec: dict[str, Any] | None, i: int = 0) -> str | None:
    if rec is None or i >= len(rec["values"]):
        return None
    return str(rec["values"][i])


def is_wavenumber_unit(unit: str | None) -> bool:
    if not unit:
        return False
    u = unit.lower()
    return "cm" in u and ("-1" in u or "⁻¹" in u or "¹" in u)


def pair_to_nm(
    rec: dict[str, Any] | None, *, factor_from_unit: str | None
) -> tuple[float, float] | None:
    if rec is None:
        return None
    a, b = num(rec, 0), num(rec, 1)
    if a is None or b is None:
        return None
    factor = length_scale_to_nm(factor_from_unit) if factor_from_unit else 1.0
    return (a * factor, b * factor)


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%m/%d/%Y %H:%M:%S").isoformat()
    except ValueError:
        return None
