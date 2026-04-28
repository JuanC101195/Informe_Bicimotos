"""Construccion de la matriz dias x franjas horarias en km.

Cada movimiento se prorratea entre las franjas horarias que cruza, segun
la fraccion de su duracion que cae en cada hora. Solo se cuentan las horas
dentro de la ventana operativa configurada (por defecto 5..20).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pandas as pd

DIAS_ES = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]

HORA_INICIO_DEFAULT = 5
HORA_FIN_DEFAULT = 20


@dataclass(frozen=True)
class MatrizConfig:
    hora_inicio: int = HORA_INICIO_DEFAULT
    hora_fin: int = HORA_FIN_DEFAULT

    def franjas(self) -> list[int]:
        """Lista de horas que abren cada franja: [5, 6, ..., 19] para 5..20."""
        return list(range(self.hora_inicio, self.hora_fin))

    def franja_label(self, h: int) -> str:
        return f"{h:02d}-{h+1:02d}"


def _apportion_segment(
    inicio: datetime, fin: datetime, km: float, config: MatrizConfig
) -> dict[tuple[date, int], float]:
    """Distribuye los km de un segmento entre las franjas (fecha, hora) que cruza.

    Solo asigna km a franjas dentro de ``[hora_inicio, hora_fin)``. Si una franja
    queda fuera de la ventana operativa, esos km se descartan.
    """
    if pd.isna(inicio) or pd.isna(fin) or fin <= inicio or km <= 0:
        return {}

    total_seg = (fin - inicio).total_seconds()
    out: dict[tuple[date, int], float] = {}

    cursor = inicio
    while cursor < fin:
        proximo_borde = (cursor.replace(minute=0, second=0, microsecond=0)
                         + timedelta(hours=1))
        siguiente = min(proximo_borde, fin)
        hora = cursor.hour
        if config.hora_inicio <= hora < config.hora_fin:
            frac = (siguiente - cursor).total_seconds() / total_seg
            key = (cursor.date(), hora)
            out[key] = out.get(key, 0.0) + km * frac
        cursor = siguiente
    return out


def build_matriz_km(
    movimientos: pd.DataFrame,
    placa: str,
    config: MatrizConfig | None = None,
) -> pd.DataFrame:
    """Construye la matriz dias x franjas para una placa.

    Las filas son fechas (orden cronologico) y las columnas son las franjas
    horarias formateadas (``"05-06"``, ``"06-07"``...). Los valores son km.
    Las celdas sin movimiento aparecen como ``NaN`` (no como 0) para que el
    renderer pueda distinguir "no hubo recorrido" de "0.00 km redondeado".
    """
    cfg = config or MatrizConfig()
    placa_df = movimientos[movimientos["placa"] == placa]

    bucket: dict[tuple[date, int], float] = {}
    for row in placa_df.itertuples(index=False):
        delta = _apportion_segment(row.comienzo_dt, row.fin_dt, row.km_ruta, cfg)
        for k, v in delta.items():
            bucket[k] = bucket.get(k, 0.0) + v

    franjas = cfg.franjas()
    franja_labels = [cfg.franja_label(h) for h in franjas]

    fechas_con_actividad = sorted({k[0] for k in bucket})
    if fechas_con_actividad:
        fechas = pd.date_range(
            fechas_con_actividad[0], fechas_con_actividad[-1], freq="D"
        ).date
    else:
        fechas = []

    matriz = pd.DataFrame(index=list(fechas), columns=franja_labels, dtype="float64")
    for (fecha, hora), km in bucket.items():
        matriz.at[fecha, cfg.franja_label(hora)] = km

    return matriz


def resumen_placa(matriz: pd.DataFrame) -> dict:
    """KPIs para mostrar en el header del reporte."""
    total_km = float(matriz.sum().sum(skipna=True))
    dias_activos = int((matriz.sum(axis=1, skipna=True) > 0).sum())
    dias_totales = int(len(matriz.index))
    return {
        "total_km": round(total_km, 2),
        "dias_activos": dias_activos,
        "dias_totales": dias_totales,
        "promedio_dia": round(total_km / dias_activos, 2) if dias_activos else 0.0,
    }


def top_placas(
    movimientos: pd.DataFrame,
    config: MatrizConfig | None = None,
    n: int = 10,
) -> list[dict]:
    """Ranking de placas por km totales en la ventana operativa.

    Cada item: ``{"placa", "total_km", "dias_activos", "promedio_dia"}``.
    Solo se cuentan los km ya prorrateados a la ventana ``[hora_inicio, hora_fin)``,
    para que el ranking sea consistente con la matriz que el usuario ve arriba.
    """
    cfg = config or MatrizConfig()
    out = []
    for placa in movimientos["placa"].dropna().unique():
        m = build_matriz_km(movimientos, placa, cfg)
        if m.empty:
            continue
        r = resumen_placa(m)
        if r["total_km"] <= 0:
            continue
        out.append({
            "placa": str(placa),
            "total_km": r["total_km"],
            "dias_activos": r["dias_activos"],
            "promedio_dia": r["promedio_dia"],
        })
    out.sort(key=lambda x: x["total_km"], reverse=True)
    return out[:n]


def fecha_label(d: date) -> str:
    """``date(2026,4,20)`` -> ``"Lunes 20-04-2026"``."""
    return f"{DIAS_ES[d.weekday()]} {d.strftime('%d-%m-%Y')}"
