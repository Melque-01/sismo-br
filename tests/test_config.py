import unittest

import config


class TestConfig(unittest.TestCase):
    def test_celulas_permitidas(self):
        self.assertEqual(config.CELULAS, (0.25, 0.5, 1.0, 2.0))
        self.assertIn(config.CELULA_PADRAO, config.CELULAS)

    def test_banco_padrao(self):
        self.assertEqual(config.BANCO["dbname"], "sismos_br")
        self.assertEqual(config.BANCO["user"], "sismos_br")

    def test_fontes(self):
        self.assertEqual(config.FDSN_DESDE, "2024-01-01")
        self.assertTrue(config.URL_SISBRA.endswith("catalogo_RAW.dat"))
        self.assertIn("/fdsnws/event/1/query", config.URL_FDSN)

    def test_ufs_27(self):
        self.assertEqual(len(config.UFS), 27)
