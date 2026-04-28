"""Carga del Excel Bicimotos con doble cabecera y normalizacion de columnas."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import parsers

CANONICAL_COLUMNS = [
    "estado",
    "placa",
    "comienzo",
    "fin",
    "duracion",
    "ralenti",
    "conductor",
    "longitud_ruta",
]


def _flatten_columns(cols) -> list[str]:
    """Aplana un MultiIndex de cabecera double-row a nombres canonicos."""
    flat = []
    for c in cols:
        if isinstance(c, tuple):
            parts = [str(x) for x in c if not str(x).startswith("Unnamed")]
            name = "_".join(parts).strip("_")
        else:
            name = str(c)
        flat.append(_canonicalize(name))
    return flat


def _canonicalize(name: str) -> str:
    """Normaliza nombres con caracteres especiales del Excel original."""
    n = name.lower()
    n = (
        n.replace("\xf3", "o")
        .replace("\xed", "i")
        .replace("\xe1", "a")
        .replace("\xe9", "e")
        .replace("\xfa", "u")
        .replace("\xf1", "n")
    )
    aliases = {
        "estado": "estado",
        "placa": "placa",
        "comienzo": "comienzo",
        "fin": "fin",
        "duracion": "duracion",
        "ralentidelmotor": "ralenti",
        "conductor": "conductor",
        "posiciondeparada_longitudderuta": "longitud_ruta",
    }
    return aliases.get(n, n)


def load_excel(path: str | Path, sheet_name: str = "Report") -> pd.DataFrame:
    """Carga el Excel y devuelve un DataFrame normalizado y tipado.

    Columnas resultantes:
    - ``estado``: ``"Detenido"`` o ``"Movimiento"``.
    - ``placa``: identificador de la moto (str).
    - ``comienzo_dt`` / ``fin_dt``: ``datetime64`` parseados.
    - ``duracion_seg`` / ``ralenti_seg``: segundos como float.
    - ``km_ruta``: distancia en km (float, 0 para detenidos).

    Nota: el Excel reusa la columna ``longitud_ruta`` con doble proposito —
    en filas ``Detenido`` trae ``"lat,lon"``, en filas ``Movimiento`` trae
    ``"X.XXKm"``. ``parse_km`` devuelve 0.0 para los strings de coord, asi
    que las filas de detenido quedan con ``km_ruta=0`` (correcto, no
    aportan al recorrido).
    """
    df = pd.read_excel(path, sheet_name=sheet_name, header=[0, 1])
    df.columns = _flatten_columns(df.columns)

    df["comienzo_dt"] = df["comienzo"].apply(parsers.parse_datetime_pegada)
    df["fin_dt"] = df["fin"].apply(parsers.parse_datetime_pegada)
    df["duracion_seg"] = df["duracion"].apply(parsers.parse_duracion_segundos)
    df["ralenti_seg"] = df["ralenti"].apply(parsers.parse_duracion_segundos)
    df["km_ruta"] = df["longitud_ruta"].apply(parsers.parse_km)

    return df


def filter_movimientos(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve solo las filas de tipo ``Movimiento`` con timestamps validos."""
    mov = df[df["estado"] == "Movimiento"].copy()
    mov = mov.dropna(subset=["comienzo_dt", "fin_dt"])
    mov = mov[mov["fin_dt"] > mov["comienzo_dt"]]
    return mov.reset_index(drop=True)
