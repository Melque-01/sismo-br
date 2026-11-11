import unittest

from servicos.catalogo import ler_fdsn

TEXTO = """#EventID|Time|Latitude|Longitude|Depth/km|Author|Catalog|Contributor|ContributorID|MagType|Magnitude|MagAuthor|EventLocationName|EventType
usp1|2026-11-10T15:11:22.359999|-20.03|-48.82|0.0|jroberto||USP|usp1|mR|3.0517|jroberto|Frutal/MG|earthquake
usp2|2026-11-07T10:53:18.108305|-21.32|-67.99|115.0|cleusa||USP|usp2|mb|4.43|cleusa|Chile-Bolivia Border Region|earthquake
usp3|2026-11-06T01:00:00.000000|13.49|-90.93|10.0|cleusa||USP|usp3|mb|5.6|cleusa|Near Coast of Guatemala|earthquake
"""


class TestFdsn(unittest.TestCase):
    def test_tres_eventos(self):
        e = ler_fdsn(TEXTO)
        self.assertEqual(len(e), 3)
        self.assertEqual(e[0]["fonte"], "FDSN")
        self.assertEqual(e[0]["uf"], "MG")
        self.assertEqual(e[0]["localidade"], "Frutal/MG")
        self.assertAlmostEqual(e[0]["magnitude"], 3.0517)
        self.assertEqual(e[0]["tipo_magnitude"], "mR")
        self.assertEqual(e[0]["data_hora"].isoformat(), "2026-11-10T15:11:22.359999+00:00")

    def test_sem_uf_fica_none(self):
        self.assertIsNone(ler_fdsn(TEXTO)[1]["uf"])

    def test_sem_magnitude_fica_none(self):
        t = TEXTO.replace("|3.0517|", "||")
        self.assertIsNone(ler_fdsn(t)[0]["magnitude"])

    def test_profundidade_zero_fica_none(self):
        self.assertIsNone(ler_fdsn(TEXTO)[0]["profundidade_km"])

    def test_ignora_evento_que_nao_e_terremoto(self):
        t = TEXTO.replace("|earthquake\n", "|quarry blast\n", 1)
        self.assertEqual(len(ler_fdsn(t)), 2)

    def test_data_hora_sempre_utc(self):
        for evento in ler_fdsn(TEXTO):
            self.assertIsNotNone(evento["data_hora"].tzinfo)
            self.assertEqual(evento["data_hora"].utcoffset().total_seconds(), 0)

    def test_chaves_do_dicionario_normalizado(self):
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
        for evento in ler_fdsn(TEXTO):
            self.assertEqual(set(evento), esperado)

    def test_cabecalho_ausente_devolve_vazio(self):
        self.assertEqual(ler_fdsn(""), [])


if __name__ == "__main__":
    unittest.main()
