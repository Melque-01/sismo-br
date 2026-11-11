"""Regressão: latitude não pode perder o sinal nem a precisão.

Algumas linhas do catálogo têm latitude/longitude com 7 ou 8 caracteres, que
começam na coluna 18 e invadem a coluna do sinal. O slice fixo `[19:25]`
descartava o `-` e a linha era gravada com latitude positiva (evento migrava
para o hemisfério norte).
"""

import unittest
from pathlib import Path

from servicos.catalogo import ler_sisbra

TEXTO = (Path(__file__).resolve().parent / "fixtures" / "sisbra_sinal.dat").read_text(
    encoding="utf-8"
)

# Valores conferidos caractere a caractere contra o catálogo original.
ESPERADO = [
    {
        "lat": -25.972,
        "lon": -57.364,
        "uf": "PY",
        "magnitude": 3.3,
        "tipo_magnitude": "1",
    },
    {
        "lat": -20.2085,
        "lon": -43.4527,
        "uf": "MG",
        "magnitude": 2.4,
        "tipo_magnitude": "1",
    },
    {
        "lat": -5.767,
        "lon": -50.48,
        "uf": "PA",
        "magnitude": 3.4,
        "tipo_magnitude": "1",
    },
    {
        "lat": -29.3745,
        "lon": -50.8834,
        "uf": "RS",
        "magnitude": 0.8,
        "tipo_magnitude": "5",
    },
    {
        "lat": -20.775,
        "lon": -47.845,
        "uf": "SP",
        "magnitude": 1.5,
        "tipo_magnitude": "5",
    },
]


class TestSisbraSinal(unittest.TestCase):
    def setUp(self):
        self.eventos = ler_sisbra(TEXTO)

    def test_todas_as_linhas_importadas(self):
        self.assertEqual(len(self.eventos), 5)

    def test_latitude_negativa_preservada(self):
        for evento, esperado in zip(self.eventos, ESPERADO):
            self.assertLess(evento["lat"], 0)
            self.assertAlmostEqual(evento["lat"], esperado["lat"], places=4)

    def test_longitude_preservada(self):
        for evento, esperado in zip(self.eventos, ESPERADO):
            self.assertAlmostEqual(evento["lon"], esperado["lon"], places=4)

    def test_uf_completa(self):
        self.assertEqual([e["uf"] for e in self.eventos], [e["uf"] for e in ESPERADO])
        for evento in self.eventos:
            self.assertEqual(len(evento["uf"]), 2)

    def test_magnitude_e_tipo(self):
        for evento, esperado in zip(self.eventos, ESPERADO):
            self.assertAlmostEqual(evento["magnitude"], esperado["magnitude"])
            self.assertEqual(evento["tipo_magnitude"], esperado["tipo_magnitude"])

    def test_precisao_da_latitude(self):
        # -20.2085 não pode virar -20.208 (slice de 6 colunas).
        self.assertEqual(self.eventos[1]["lat"], -20.2085)
        self.assertEqual(self.eventos[3]["lat"], -29.3745)

    def test_hora_local_continua_convertida(self):
        instante = self.eventos[4]["data_hora"].isoformat()
        self.assertEqual(instante, "2019-08-13T09:30:00+00:00")

    def test_localidade(self):
        self.assertTrue(self.eventos[0]["localidade"].startswith("Yaceret"))
        self.assertEqual(self.eventos[1]["localidade"], "Mariana Mina-Germano")
        self.assertEqual(self.eventos[2]["localidade"], "Parauapebas")

    def test_nenhuma_latitude_fora_do_brasil(self):
        for evento in self.eventos:
            self.assertGreaterEqual(evento["lat"], -34.0)
            self.assertLessEqual(evento["lat"], 6.0)
            self.assertGreaterEqual(evento["lon"], -74.0)
            self.assertLessEqual(evento["lon"], -34.0)

    def test_linha_fora_da_bbox_e_descartada(self):
        # Saladillo (AR), lat -35.1: fora do recorte do Brasil.
        linha = (
            " 1845 1019 16L     -35.1  -59.8    0 AR    0. 3.5  4  C   5   "
            "    Saladillo Buenos_Aires (INPRES)"
        )
        self.assertEqual(ler_sisbra(linha), [])


if __name__ == "__main__":
    unittest.main()
