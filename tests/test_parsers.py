"""Tests para los parsers especificos del Excel Bicimotos."""

from datetime import datetime

import pandas as pd
import pytest

from src.parsers import parse_datetime_pegada, parse_duracion_segundos, parse_km


class TestParseDatetimePegada:
    def test_formato_estandar(self):
        assert parse_datetime_pegada("20-04-202606:55:07") == datetime(2026, 4, 20, 6, 55, 7)

    def test_medianoche(self):
        assert parse_datetime_pegada("01-01-202600:00:00") == datetime(2026, 1, 1, 0, 0, 0)

    def test_nan_devuelve_nat(self):
        assert pd.isna(parse_datetime_pegada(None))
        assert pd.isna(parse_datetime_pegada(float("nan")))

    def test_string_basura(self):
        assert pd.isna(parse_datetime_pegada("no es fecha"))


class TestParseDuracionSegundos:
    def test_horas_minutos_segundos(self):
        assert parse_duracion_segundos("11h4min43s") == 11 * 3600 + 4 * 60 + 43

    def test_solo_minutos_segundos(self):
        assert parse_duracion_segundos("9min15s") == 9 * 60 + 15

    def test_solo_segundos(self):
        assert parse_duracion_segundos("33s") == 33

    def test_solo_minutos(self):
        assert parse_duracion_segundos("5min") == 300

    def test_solo_horas(self):
        assert parse_duracion_segundos("2h") == 7200

    def test_vacio_o_nan(self):
        assert parse_duracion_segundos("") == 0.0
        assert parse_duracion_segundos(None) == 0.0
        assert parse_duracion_segundos(float("nan")) == 0.0

    def test_string_basura_devuelve_cero(self):
        assert parse_duracion_segundos("xyz") == 0.0


class TestParseKm:
    def test_decimal_punto(self):
        assert parse_km("0.68Km") == pytest.approx(0.68)

    def test_decimal_coma(self):
        assert parse_km("0,68Km") == pytest.approx(0.68)

    def test_entero(self):
        assert parse_km("12Km") == pytest.approx(12.0)

    def test_caso_insensitivo(self):
        assert parse_km("0.5km") == pytest.approx(0.5)
        assert parse_km("0.5KM") == pytest.approx(0.5)

    def test_sin_sufijo_intenta_float(self):
        assert parse_km("3.14") == pytest.approx(3.14)

    def test_nan_es_cero(self):
        assert parse_km(None) == 0.0
        assert parse_km(float("nan")) == 0.0

    def test_basura_es_cero(self):
        assert parse_km("foo") == 0.0
