"""Testes do fallback do parser SISBRA para linhas com colunas deslocadas.

Algumas linhas reais do catálogo têm hora com fração de segundo (9 caracteres)
ou latitude/longitude com largura variável, o que empurra as colunas seguintes.
O parser deve recuperar essas linhas em vez de descartá-las.
"""

import unittest
from pathlib import Path

from servicos.catalogo import evento_id_sisbra, ler_sisbra

TEXTO = (
    Path(__file__).resolve().parent / "fixtures" / "sisbra_desalinhado.dat"
).read_text(encoding="utf-8")

# Valores conferidos caractere a caractere contra o catálogo original.
ESPERADO = [
    {
        "ano": 1989,
        "data_hora": "1989-03-26T13:25:39.310000+00:00",
        "lat": -4.81,
        "lon": -37.97,
        "uf": "CE",
        "profundidade_km": 4.0,
        "magnitude": 4.5,
        "tipo_magnitude": "2",
        "categoria": "I",
        "localidade": "Palhano",
        "autor": "UFRN;UnB;IAG",
    },
    {
        "ano": 2007,
        "data_hora": "2007-03-20T13:38:52.840000+00:00",
        "lat": -8.2635,
        "lon": -36.1607,
        "uf": "PE",
        "profundidade_km": 5.0,
        "magnitude": 3.9,
        "tipo_magnitude": "1",
        "categoria": "I",
        "localidade": "Sao Caetano",
        "autor": "UFRN=3.9;IAG=3.8; 5-sta local net",
    },
    {
        "ano": 2010,
        "data_hora": "2010-10-08T20:16:54.790000+00:00",
        "lat": -13.771,
        "lon": -49.16,
        "uf": "GO",
        "profundidade_km": 1.4,
        "magnitude": 5.0,
        "tipo_magnitude": "0",
        "categoria": "I",
        "localidade": "Mara Rosa",
        "autor": "UnB: rel.loc. with 2011-Feb-26; ISC mb5.0",
    },
    {
        "ano": 2012,
        "data_hora": "2012-05-19T13:41:22.560000+00:00",
        "lat": -16.6955,
        "lon": -43.8848,
        "uf": "MG",
        "profundidade_km": 1.1,
        "magnitude": 4.0,
        "tipo_magnitude": "1",
        "categoria": "I",
        "localidade": "Montes Claros",
        "autor": "IAG;UnB;USGS",
    },
]


class TestSisbraDesalinhado(unittest.TestCase):
    def setUp(self):
        self.eventos = ler_sisbra(TEXTO)

    def test_recupera_todas_as_linhas(self):
        self.assertEqual(len(self.eventos), 4)

    def test_coordenadas_recuperadas(self):
        for evento, esperado in zip(self.eventos, ESPERADO):
            self.assertAlmostEqual(evento["lat"], esperado["lat"], places=4)
            self.assertAlmostEqual(evento["lon"], esperado["lon"], places=4)

    def test_uf_recuperada(self):
        self.assertEqual([e["uf"] for e in self.eventos], [e["uf"] for e in ESPERADO])

    def test_magnitude_e_tipo_recuperados(self):
        for evento, esperado in zip(self.eventos, ESPERADO):
            self.assertAlmostEqual(evento["magnitude"], esperado["magnitude"])
            self.assertEqual(evento["tipo_magnitude"], esperado["tipo_magnitude"])

    def test_profundidade_recuperada(self):
        for evento, esperado in zip(self.eventos, ESPERADO):
            self.assertAlmostEqual(evento["profundidade_km"], esperado["profundidade_km"])

    def test_hora_com_fracao_de_segundo(self):
        for evento, esperado in zip(self.eventos, ESPERADO):
            self.assertEqual(evento["data_hora"].isoformat(), esperado["data_hora"])

    def test_categoria_localidade_e_autor(self):
        for evento, esperado in zip(self.eventos, ESPERADO):
            self.assertEqual(evento["categoria"], esperado["categoria"])
            self.assertEqual(evento["localidade"], esperado["localidade"])
            self.assertEqual(evento["autor"], esperado["autor"])

    def test_evento_id_continua_valido(self):
        ids = [e["evento_id"] for e in self.eventos]
        self.assertEqual(len(set(ids)), 4)
        for i in ids:
            self.assertEqual(len(i), 64)

    def test_linha_sem_coordenada_nao_e_recuperada(self):
        linha = (
            " 1709 ---- --        --   --       0 BA    0. 0.0 -1  D   -  "
            "     Salvador"
        )
        self.assertEqual(ler_sisbra(linha), [])

    def test_linha_ilegivel_e_descartada(self):
        linha = " 2023 1229 160100  xx.yy zz.ww   5 PE   0.0 2.2  1  I  -  Caruaru"
        self.assertEqual(ler_sisbra(linha), [])

    def test_evento_id_estavel(self):
        self.assertEqual(
            evento_id_sisbra("1989", "0326", "132539.31", -4.81, -37.97, 4.5),
            self.eventos[0]["evento_id"],
        )


if __name__ == "__main__":
    unittest.main()
