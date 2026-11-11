import unittest

from controles.sismo_controle import ErroValidacao, montar_filtros


class TestFiltros(unittest.TestCase):
    def test_padroes(self):
        f = montar_filtros({})
        self.assertEqual(f["fonte"], "todas")
        self.assertEqual(f["celula"], 0.5)
        self.assertEqual(f["ano_ini"], 1500)
        self.assertIsNone(f["mag_min"])
        self.assertIsNone(f["mag_max"])
        self.assertIsNone(f["prof_max"])
        self.assertIsNone(f["uf"])
        self.assertIsNone(f["categoria"])

    def test_celula_invalida(self):
        with self.assertRaises(ErroValidacao):
            montar_filtros({"celula": "0.3"})

    def test_celula_valida_como_texto(self):
        self.assertEqual(montar_filtros({"celula": "1"})["celula"], 1.0)

    def test_mag_min_maior_que_max(self):
        with self.assertRaises(ErroValidacao):
            montar_filtros({"mag_min": "5", "mag_max": "2"})

    def test_uf_normalizada(self):
        self.assertEqual(montar_filtros({"uf": "mg"})["uf"], "MG")

    def test_uf_vazia_nao_e_filtro(self):
        self.assertIsNone(montar_filtros({"uf": "  "})["uf"])

    def test_uf_invalida(self):
        with self.assertRaises(ErroValidacao):
            montar_filtros({"uf": "XX"})

    def test_ano_texto_invalido(self):
        with self.assertRaises(ErroValidacao):
            montar_filtros({"ano_ini": "abc"})

    def test_ano_fora_da_faixa(self):
        with self.assertRaises(ErroValidacao):
            montar_filtros({"ano_ini": "1200"})
        with self.assertRaises(ErroValidacao):
            montar_filtros({"ano_fim": "2999"})

    def test_ano_invertido(self):
        with self.assertRaises(ErroValidacao):
            montar_filtros({"ano_ini": "2010", "ano_fim": "1990"})

    def test_fonte_invalida(self):
        with self.assertRaises(ErroValidacao):
            montar_filtros({"fonte": "USGS"})

    def test_fonte_vazia_vira_todas(self):
        self.assertEqual(montar_filtros({"fonte": ""})["fonte"], "todas")

    def test_categoria_invalida(self):
        with self.assertRaises(ErroValidacao):
            montar_filtros({"categoria": "Z"})

    def test_mensagem_em_portugues(self):
        with self.assertRaises(ErroValidacao) as contexto:
            montar_filtros({"celula": "0.3"})
        self.assertIn("Célula", str(contexto.exception))
        self.assertIn("0.25", str(contexto.exception))


if __name__ == "__main__":
    unittest.main()
