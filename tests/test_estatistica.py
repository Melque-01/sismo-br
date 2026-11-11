import unittest

from servicos.estatistica import cortes, histograma


class TestEstatistica(unittest.TestCase):
    def test_cortes_lista_vazia(self):
        self.assertEqual(cortes([]), [])

    def test_cortes_cinco_classes(self):
        self.assertEqual(cortes([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]), [2, 4, 6, 8])

    def test_cortes_sem_duplicata(self):
        self.assertEqual(cortes([1, 1, 1, 1, 1]), [1])

    def test_cortes_cinco_valores(self):
        self.assertEqual(cortes([1, 2, 3, 4, 5]), [1, 2, 3, 4])

    def test_cortes_devolve_ints_ou_floats_ordenados(self):
        resultado = cortes([10, 1, 5, 3, 8, 2, 9, 4, 7, 6])
        self.assertEqual(resultado, sorted(resultado))

    def test_histograma(self):
        h = histograma([1.1, 1.6, 2.0], largura=0.5)
        self.assertEqual([b["de"] for b in h], [1.0, 1.5, 2.0])
        self.assertEqual([b["n"] for b in h], [1, 1, 1])

    def test_histograma_lista_vazia(self):
        self.assertEqual(histograma([]), [])

    def test_histograma_ignora_none(self):
        h = histograma([None, 1.0, None])
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0]["n"], 1)

    def test_histograma_soma_total(self):
        valores = [0.1, 0.4, 0.5, 1.2, 1.7, 2.9]
        self.assertEqual(sum(b["n"] for b in histograma(valores)), len(valores))


if __name__ == "__main__":
    unittest.main()
