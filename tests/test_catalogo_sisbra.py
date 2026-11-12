"""Testes do parser do catálogo SISBRA (formato de colunas fixas)."""

import unittest
from datetime import timezone
from pathlib import Path

from servicos.catalogo import evento_id_sisbra, ler_sisbra

TEXTO = (Path(__file__).resolve().parent / "fixtures" / "sisbra_amostra.dat").read_text(
    encoding="utf-8"
)


class TestSisbra(unittest.TestCase):
    def setUp(self):
        self.eventos = ler_sisbra(TEXTO)

    def test_descarta_sem_coordenada(self):
        self.assertEqual(len(self.eventos), 6)

    def test_campos_normalizados(self):
        e = self.eventos[0]
        self.assertEqual(e["fonte"], "SISBRA")
        self.assertEqual(e["ano"], 2023)
        self.assertEqual(e["uf"], "PE")
        self.assertAlmostEqual(e["lat"], -8.35)
        self.assertAlmostEqual(e["lon"], -35.99)
        self.assertAlmostEqual(e["magnitude"], 2.2)
        self.assertEqual(e["categoria"], "I")
        self.assertEqual(e["localidade"], "Caruaru")
        self.assertEqual(e["autor"], "UFRN")

    def test_chaves_do_evento_normalizado(self):
        esperado = {
            "fonte",
            "evento_id",
            "data_hora",
            "ano",
            "lat",
            "lon",
            "profundidade_km",
            "magnitude",
            "tipo_magnitude",
            "categoria",
            "uf",
            "localidade",
            "autor",
        }
        for e in self.eventos:
            self.assertEqual(set(e), esperado)

    def test_hora_local_vira_utc_menos_3(self):
        e = self.eventos[1]
        self.assertEqual(e["data_hora"].isoformat(), "1724-01-04T10:30:00+00:00")

    def test_hora_utc_sem_sufixo(self):
        e = self.eventos[0]
        self.assertEqual(e["data_hora"].isoformat(), "2023-12-29T16:01:00+00:00")
        self.assertIs(e["data_hora"].tzinfo, timezone.utc)

    def test_hora_ausente_fica_none(self):
        self.assertIsNone(self.eventos[4]["data_hora"])  # 1720 1123 --

    def test_magnitude_desconhecida_fica_none(self):
        self.assertIsNone(self.eventos[3]["magnitude"])  # tm -1
        self.assertIsNone(ler_sisbra(TEXTO)[5]["magnitude"])  # mag 0.0

    def test_profundidade_zero_fica_none(self):
        self.assertIsNone(self.eventos[0]["profundidade_km"])

    def test_profundidade_presente(self):
        linha = (
            " 1960 1021 041844  -07.20 -73.80  50 AC 100.  4.9  5  I   -  "
            "     NW DO ACRE             (CERESIS: USGS) not in ISS"
        )
        e = ler_sisbra(linha)[0]
        self.assertAlmostEqual(e["profundidade_km"], 100.0)

    def test_tipo_magnitude_mantem_menos_um(self):
        self.assertEqual(self.eventos[3]["tipo_magnitude"], "-1")
        self.assertEqual(self.eventos[0]["tipo_magnitude"], "1")

    def test_autor_com_hifen(self):
        self.assertEqual(self.eventos[2]["autor"], "RSBR-USP")

    def test_autor_ausente_fica_none(self):
        self.assertIsNone(self.eventos[1]["autor"])

    def test_evento_id_estavel(self):
        a = evento_id_sisbra("2023", "1229", "160100", -8.35, -35.99, 2.2)
        b = evento_id_sisbra("2023", "1229", "160100", -8.35, -35.99, 2.2)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in a))

    def test_evento_id_e_sha256_nao_md5(self):
        import hashlib

        chave = "2023|1229|160100|-8.35|-35.99|2.2"
        identificador = evento_id_sisbra(
            "2023", "1229", "160100", -8.35, -35.99, 2.2
        )
        self.assertEqual(identificador, hashlib.sha256(chave.encode()).hexdigest())
        self.assertNotEqual(identificador, hashlib.md5(chave.encode()).hexdigest())

    def test_evento_id_difere_entre_eventos(self):
        ids = {e["evento_id"] for e in self.eventos}
        self.assertEqual(len(ids), 6)

    def test_ignora_cabecalho_e_linhas_vazias(self):
        self.assertEqual(ler_sisbra(""), [])
        self.assertEqual(ler_sisbra(TEXTO + "\n\n   \n"), self.eventos)


if __name__ == "__main__":
    unittest.main()
