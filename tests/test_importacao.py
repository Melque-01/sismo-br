import unittest

from scripts.importar_catalogo import filtrar_fdsn, filtrar_sisbra, url_fdsn

SIS = [
    {"uf": "MG", "lat": -19.9, "lon": -43.9},
    {"uf": "CH", "lat": -22.0, "lon": -43.0},
    {"uf": None, "lat": -10.0, "lon": -50.0},
]
FDSN = [
    {"uf": "MG", "lat": -20.0, "lon": -48.8},
    {"uf": None, "lat": -21.3, "lon": -68.0},
]


class TestImportacao(unittest.TestCase):
    def test_sisbra_descarta_uf_estrangeira_e_sem_uf(self):
        aceitos, descartados = filtrar_sisbra(SIS, {"MG", "SP"})
        self.assertEqual(len(aceitos), 1)
        self.assertEqual(descartados, 2)

    def test_fdsn_mantem_sem_uf_para_filtro_geografico(self):
        aceitos, descartados = filtrar_fdsn(FDSN)
        self.assertEqual(len(aceitos), 2)
        self.assertEqual(descartados, 0)

    def test_url_fdsn_tem_recorte_e_data_inicial(self):
        url = url_fdsn()
        self.assertIn("format=text", url)
        self.assertIn("starttime=2024-01-01", url)
        self.assertIn("minlatitude=-34.0", url)
        self.assertIn("eventtype=earthquake", url)

    def test_sisbra_sem_uf_brasileira_nao_entra(self):
        aceitos, _ = filtrar_sisbra(SIS, {"SP"})
        self.assertEqual(aceitos, [])


if __name__ == "__main__":
    unittest.main()
