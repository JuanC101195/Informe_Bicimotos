"""Parsers para el formato del Excel Bicimotos.

El reporte trae tres formatos no estandar que necesitan normalizacion:

- Fecha+hora pegadas: ``"20-04-202606:55:07"`` (sin separador).
- Duracion en string: ``"11h4min43s"``, ``"9min15s"``, ``"33s"``.
- Distancia con sufijo: ``"0.68Km"``.
"""

from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

_DT_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{4})(\d{2}):(\d{2}):(\d{2})$")
_DUR_RE = re.compile(
    r"(?:(?P<h>\d+)h)?(?:(?P<m>\d+)min)?(?:(?P<s>\d+)s)?$"
)
_KM_RE = re.compile(r"^([\d.,]+)\s*Km$", re.IGNORECASE)


def parse_datetime_pegada(value) -> datetime | pd.NaTType:
    """Parsea ``"DD-MM-YYYYHH:MM:SS"`` (sin espacio entre fecha y hora)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NaT
    s = str(value).strip()
    m = _DT_RE.match(s)
    if not m:
        return pd.to_datetime(s, errors="coerce", dayfirst=True)
    d, mo, y, hh, mm, ss = m.groups()
    try:
        return datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss))
    except ValueError:
        return pd.NaT


def parse_duracion_segundos(value) -> float:
    """Convierte ``"11h4min43s"`` o ``"33s"`` a segundos como float.

    Devuelve ``0.0`` cuando el valor es vacio o no parseable.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    s = str(value).strip().replace(" ", "")
    if not s:
        return 0.0
    m = _DUR_RE.match(s)
    if not m or not any(m.groupdict().values()):
        return 0.0
    h = int(m.group("h") or 0)
    mi = int(m.group("m") or 0)
    se = int(m.group("s") or 0)
    return float(h * 3600 + mi * 60 + se)


def parse_km(value) -> float:
    """Convierte ``"0.68Km"`` a ``0.68`` (float). Acepta coma como decimal."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    s = str(value).strip()
    if not s:
        return 0.0
    m = _KM_RE.match(s)
    if not m:
        try:
            return float(s.replace(",", "."))
        except ValueError:
            return 0.0
    raw = m.group(1).replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return 0.0
