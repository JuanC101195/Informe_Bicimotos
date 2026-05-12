"""Carga y normalizacion del reporte de no pagos.

El Excel viene con cabecera simple, primera columna concatena placa y
nombre del conductor con ``" - "``, y las dos columnas relevantes son
``Deuda`` (monto total adeudado) y ``# Deuda`` (cantidad de cuotas
adeudadas, puede ser fraccionaria).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import parsers

DEFAULT_SHEET = "nopagos"


def _split_placa_conductor(value) -> tuple[str | None, str | None]:
    """``"BI0028 - KAROLAY GOMEZ NAVAS"`` -> ``("BI0028", "KAROLAY GOMEZ NAVAS")``."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None, None
    s = str(value).strip()
    if not s:
        return None, None
    if " - " in s:
        placa, _, nombre = s.partition(" - ")
        return parsers.normalize_placa(placa), nombre.strip() or None
    return parsers.normalize_placa(s), None


def load_nopagos(path: str | Path, sheet_name: str = DEFAULT_SHEET) -> pd.DataFrame:
    """Devuelve un DataFrame normalizado con columnas:

    - ``placa`` (str): identificador alineado con el reporte de recorridos.
    - ``conductor`` (str): nombre extraido de la columna 0.
    - ``deuda`` (float): monto total adeudado.
    - ``num_cuotas`` (float): cantidad de cuotas adeudadas.

    Filas sin placa parseable se descartan silenciosamente.
    """
    df = pd.read_excel(path, sheet_name=sheet_name)

    primera_col = df.columns[0]
    parsed = df[primera_col].apply(_split_placa_conductor)
    placas = parsed.apply(lambda x: x[0])
    conductores = parsed.apply(lambda x: x[1])

    out = pd.DataFrame({
        "placa": placas,
        "conductor": conductores,
        "deuda": pd.to_numeric(df.get("Deuda"), errors="coerce"),
        "num_cuotas": pd.to_numeric(df.get("# Deuda"), errors="coerce"),
    })
    out = out.dropna(subset=["placa"]).reset_index(drop=True)
    return out


def top_morosos(
    nopagos: pd.DataFrame,
    km_por_placa: dict[str, float] | None = None,
    n: int = 10,
) -> list[dict]:
    """Ranking de placas con mas cuotas adeudadas.

    Cada item: ``{placa, conductor, num_cuotas, deuda, km_recorridos}``.
    ``km_recorridos`` queda en ``None`` si la placa no aparece en el
    diccionario de km (no tuvo movimientos en el periodo de la matriz).
    """
    if nopagos.empty:
        return []
    km_map = km_por_placa or {}
    df = nopagos.copy()
    df = df.dropna(subset=["num_cuotas"])
    df = df.sort_values("num_cuotas", ascending=False).head(n)
    out = []
    for row in df.itertuples(index=False):
        out.append({
            "placa": row.placa,
            "conductor": row.conductor or "",
            "num_cuotas": float(row.num_cuotas),
            "deuda": float(row.deuda) if pd.notna(row.deuda) else 0.0,
            "km_recorridos": km_map.get(row.placa),
        })
    return out
