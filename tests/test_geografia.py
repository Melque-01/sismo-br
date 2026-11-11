import unittest

from servicos.geografia import UF_POR_CODAREA, uf_do_codarea


class TestGeografia(unittest.TestCase):
    def test_27_ufs(self):
        self.assertEqual(len(UF_POR_CODAREA), 27)
        self.assertEqual(uf_do_codarea("11"), "RO")
        self.assertEqual(uf_do_codarea("35"), "SP")
        self.assertEqual(uf_do_codarea("99"), "")

    def test_codarea_como_inteiro(self):
        self.assertEqual(uf_do_codarea(53), "DF")

    def test_todas_as_siglas_sao_unicas(self):
        self.assertEqual(len(set(UF_POR_CODAREA.values())), 27)

    def test_todas_as_ufs_do_config(self):
        import config

        self.assertEqual(set(UF_POR_CODAREA.values()), set(config.UFS))


if __name__ == "__main__":
    unittest.main()
