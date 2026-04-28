"""Tests para la construccion de la matriz dias x franjas horarias."""

from datetime import date, datetime

import pandas as pd
import pytest

from src.matriz import (
    MatrizConfig,
    _apportion_segment,
    build_matriz_km,
    fecha_label,
    resumen_placa,
    top_placas,
)


class TestApportionSegment:
    def test_segmento_dentro_de_una_sola_franja(self):
        cfg = MatrizConfig()
        out = _apportion_segment(
            datetime(2026, 4, 20, 7, 10), datetime(2026, 4, 20, 7, 50), 4.0, cfg
        )
        assert out == {(date(2026, 4, 20), 7): pytest.approx(4.0)}

    def test_segmento_cruza_dos_franjas_se_distribuye_proporcional(self):
        cfg = MatrizConfig()
        out = _apportion_segment(
            datetime(2026, 4, 20, 6, 30),
            datetime(2026, 4, 20, 7, 30),
            6.0,
            cfg,
        )
        assert out[(date(2026, 4, 20), 6)] == pytest.approx(3.0)
        assert out[(date(2026, 4, 20), 7)] == pytest.approx(3.0)

    def test_horas_fuera_ventana_se_descartan(self):
        cfg = MatrizConfig(hora_inicio=5, hora_fin=20)
        out = _apportion_segment(
            datetime(2026, 4, 20, 19, 30),
            datetime(2026, 4, 20, 20, 30),
            4.0,
            cfg,
        )
        assert out[(date(2026, 4, 20), 19)] == pytest.approx(2.0)
        assert (date(2026, 4, 20), 20) not in out

    def test_segmento_completamente_fuera_devuelve_vacio(self):
        cfg = MatrizConfig(hora_inicio=5, hora_fin=20)
        out = _apportion_segment(
            datetime(2026, 4, 20, 22, 0),
            datetime(2026, 4, 20, 23, 0),
            5.0,
            cfg,
        )
        assert out == {}

    def test_km_cero_devuelve_vacio(self):
        cfg = MatrizConfig()
        out = _apportion_segment(
            datetime(2026, 4, 20, 7, 0), datetime(2026, 4, 20, 8, 0), 0.0, cfg
        )
        assert out == {}


class TestBuildMatrizKm:
    def _mov_df(self, rows):
        return pd.DataFrame(
            rows, columns=["placa", "comienzo_dt", "fin_dt", "km_ruta"]
        )

    def test_matriz_simple_una_placa(self):
        mov = self._mov_df([
            ("BI001", datetime(2026, 4, 20, 7, 0), datetime(2026, 4, 20, 7, 30), 2.0),
            ("BI001", datetime(2026, 4, 21, 8, 0), datetime(2026, 4, 21, 8, 15), 1.5),
        ])
        m = build_matriz_km(mov, "BI001")
        assert m.at[date(2026, 4, 20), "07-08"] == pytest.approx(2.0)
        assert m.at[date(2026, 4, 21), "08-09"] == pytest.approx(1.5)

    def test_filtra_otras_placas(self):
        mov = self._mov_df([
            ("BI001", datetime(2026, 4, 20, 7, 0), datetime(2026, 4, 20, 7, 30), 2.0),
            ("BI002", datetime(2026, 4, 20, 7, 0), datetime(2026, 4, 20, 7, 30), 99.0),
        ])
        m = build_matriz_km(mov, "BI001")
        assert m.at[date(2026, 4, 20), "07-08"] == pytest.approx(2.0)

    def test_dias_intermedios_sin_actividad_aparecen(self):
        mov = self._mov_df([
            ("BI001", datetime(2026, 4, 20, 7, 0), datetime(2026, 4, 20, 7, 30), 2.0),
            ("BI001", datetime(2026, 4, 22, 7, 0), datetime(2026, 4, 22, 7, 30), 2.0),
        ])
        m = build_matriz_km(mov, "BI001")
        assert date(2026, 4, 21) in list(m.index)
        assert pd.isna(m.at[date(2026, 4, 21), "07-08"])

    def test_placa_sin_movimientos_devuelve_matriz_vacia(self):
        mov = self._mov_df([])
        m = build_matriz_km(mov, "BI001")
        assert m.empty


class TestResumenPlaca:
    def test_resumen_basico(self):
        idx = [date(2026, 4, 20), date(2026, 4, 21)]
        cols = ["07-08", "08-09"]
        m = pd.DataFrame(
            [[2.0, 3.0], [None, 1.0]], index=idx, columns=cols, dtype="float64"
        )
        r = resumen_placa(m)
        assert r["total_km"] == pytest.approx(6.0)
        assert r["dias_activos"] == 2
        assert r["dias_totales"] == 2
        assert r["promedio_dia"] == pytest.approx(3.0)


class TestTopPlacas:
    def _mov_df(self, rows):
        return pd.DataFrame(
            rows, columns=["placa", "comienzo_dt", "fin_dt", "km_ruta"]
        )

    def test_orden_descendente_por_km(self):
        mov = self._mov_df([
            ("BI001", datetime(2026, 4, 20, 7, 0), datetime(2026, 4, 20, 7, 30), 2.0),
            ("BI002", datetime(2026, 4, 20, 7, 0), datetime(2026, 4, 20, 7, 30), 5.0),
            ("BI003", datetime(2026, 4, 20, 7, 0), datetime(2026, 4, 20, 7, 30), 1.0),
        ])
        top = top_placas(mov, n=10)
        assert [t["placa"] for t in top] == ["BI002", "BI001", "BI003"]
        assert top[0]["total_km"] == pytest.approx(5.0)

    def test_n_limita_resultados(self):
        rows = [
            (f"BI{i:03d}", datetime(2026, 4, 20, 7, 0),
             datetime(2026, 4, 20, 7, 30), float(i))
            for i in range(1, 6)
        ]
        top = top_placas(self._mov_df(rows), n=3)
        assert len(top) == 3
        assert top[0]["placa"] == "BI005"

    def test_excluye_placas_sin_km(self):
        mov = self._mov_df([
            ("BI001", datetime(2026, 4, 20, 7, 0), datetime(2026, 4, 20, 7, 30), 3.0),
            ("BI002", datetime(2026, 4, 20, 22, 0), datetime(2026, 4, 20, 22, 30), 5.0),
        ])
        top = top_placas(mov, n=10)
        assert [t["placa"] for t in top] == ["BI001"]


class TestFechaLabel:
    def test_lunes_20_abril(self):
        assert fecha_label(date(2026, 4, 20)) == "Lunes 20-04-2026"

    def test_domingo_26_abril(self):
        assert fecha_label(date(2026, 4, 26)) == "Domingo 26-04-2026"
