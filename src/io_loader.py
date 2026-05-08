"""Carga del Excel Bicimotos con doble cabecera y normalizacion de columnas."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from . import parsers

_KM_VALUE_RE = re.compile(r"^\s*\d+(?:[.,]\d+)?\s*km\s*$", re.IGNORECASE)
_KM_COLUMN_CANDIDATES = (
    "longitud_ruta",
    "posiciondeparada_velocidadmaxima",
    "posiciondeparada_velocidadmedia",
)

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
    n = n.replace(" ", "")
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


def _km_de_fila(row: pd.Series, columnas: tuple[str, ...]) -> float:
    """Devuelve los km de una fila probando las columnas candidatas en orden.

    El export del GPS desfasa los km por fila: la mayoria los trae en
    ``longitud_ruta`` pero hay filas (mismo archivo, distintas placas)
    donde quedan corridos a ``posiciondeparada_velocidadmaxima``. Para
    cada fila, devolvemos el primer valor que matchee ``"X.XX Km"``.
    """
    for col in columnas:
        v = row.get(col)
        if v is None:
            continue
        v_str = str(v)
        if _KM_VALUE_RE.match(v_str):
            return parsers.parse_km(v_str)
    return 0.0


def load_excel(path: str | Path, sheet_name: str = "Report") -> pd.DataFrame:
    """Carga el Excel y devuelve un DataFrame normalizado y tipado.

    Columnas resultantes:
    - ``estado``: ``"Detenido"`` o ``"Movimiento"``.
    - ``placa``: identificador de la moto (str).
    - ``comienzo_dt`` / ``fin_dt``: ``datetime64`` parseados.
    - ``duracion_seg`` / ``ralenti_seg``: segundos como float.
    - ``km_ruta``: distancia en km (float, 0 para detenidos).

    Nota: el export del GPS desfasa los km por fila — la mayoria los trae
    en ``longitud_ruta`` pero algunas filas los traen en
    ``posiciondeparada_velocidadmaxima``. ``_km_de_fila`` prueba las
    candidatas en orden y devuelve el primer valor que matchee el formato
    ``"X.XX Km"``, asi que filas de ``Detenido`` (que tienen ``"lat,lon"``)
    y movimientos con datos vacios quedan en 0 — correcto, no aportan al
    recorrido.
    """
    df = pd.read_excel(path, sheet_name=sheet_name, header=[0, 1])
    df.columns = _flatten_columns(df.columns)

    df["comienzo_dt"] = df["comienzo"].apply(parsers.parse_datetime_pegada)
    df["fin_dt"] = df["fin"].apply(parsers.parse_datetime_pegada)
    df["duracion_seg"] = df["duracion"].apply(parsers.parse_duracion_segundos)
    df["ralenti_seg"] = df["ralenti"].apply(parsers.parse_duracion_segundos)

    candidatas = tuple(c for c in _KM_COLUMN_CANDIDATES if c in df.columns)
    df["km_ruta"] = df.apply(lambda r: _km_de_fila(r, candidatas), axis=1)

    return df


def filter_movimientos(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve solo las filas de tipo ``Movimiento`` con timestamps validos."""
    mov = df[df["estado"] == "Movimiento"].copy()
    mov = mov.dropna(subset=["comienzo_dt", "fin_dt"])
    mov = mov[mov["fin_dt"] > mov["comienzo_dt"]]
    return mov.reset_index(drop=True)
