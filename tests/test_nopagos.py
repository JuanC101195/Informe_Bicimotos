"""Tests para la carga del reporte de no pagos y el ranking de morosos."""

import pandas as pd
import pytest

from src.nopagos import _split_placa_conductor, top_morosos


class TestSplitPlacaConductor:
    def test_caso_normal(self):
        assert _split_placa_conductor("BI0028 - KAROLAY GOMEZ NAVAS") == (
            "BI0028", "KAROLAY GOMEZ NAVAS"
        )

    def test_doble_espacio_antes_del_nombre(self):
        # El Excel real tiene casos con doble espacio: "BI0172 -  EILEN..."
        placa, nombre = _split_placa_conductor("BI0172 -  EILEN MARGARITA")
        assert placa == "BI0172"
        assert nombre == "EILEN MARGARITA"

    def test_solo_placa_sin_separador(self):
        assert _split_placa_conductor("BI0028") == ("BI0028", None)

    def test_nan_devuelve_dos_none(self):
        assert _split_placa_conductor(None) == (None, None)
        assert _split_placa_conductor(float("nan")) == (None, None)

    def test_string_vacio(self):
        assert _split_placa_conductor("") == (None, None)
        assert _split_placa_conductor("   ") == (None, None)


class TestTopMorosos:
    def _df(self, rows):
        return pd.DataFrame(
            rows, columns=["placa", "conductor", "deuda", "num_cuotas"]
        )

    def test_ordena_descendente_por_cuotas(self):
        df = self._df([
            ("BI001", "Juan", 100, 1.0),
            ("BI002", "Ana", 500, 3.5),
            ("BI003", "Luis", 200, 2.0),
        ])
        top = top_morosos(df, n=10)
        assert [t["placa"] for t in top] == ["BI002", "BI003", "BI001"]
        assert top[0]["num_cuotas"] == pytest.approx(3.5)
        assert top[0]["conductor"] == "Ana"

    def test_n_limita_resultados(self):
        df = self._df([
            (f"BI{i:03d}", f"C{i}", 100 * i, float(i)) for i in range(1, 6)
        ])
        top = top_morosos(df, n=2)
        assert len(top) == 2
        assert top[0]["placa"] == "BI005"

    def test_cruza_km_por_placa(self):
        df = self._df([
            ("BI001", "Juan", 100, 2.0),
            ("BI002", "Ana", 200, 1.0),
        ])
        km_map = {"BI001": 42.5}
        top = top_morosos(df, km_por_placa=km_map, n=10)
        assert top[0]["km_recorridos"] == pytest.approx(42.5)
        assert top[1]["km_recorridos"] is None

    def test_descarta_filas_sin_cuotas(self):
        df = self._df([
            ("BI001", "Juan", 100, 1.0),
            ("BI002", "Ana", 500, None),
        ])
        top = top_morosos(df, n=10)
        assert [t["placa"] for t in top] == ["BI001"]

    def test_dataframe_vacio_devuelve_lista_vacia(self):
        assert top_morosos(self._df([])) == []
