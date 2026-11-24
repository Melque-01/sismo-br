"""Testes de cache de processo nas respostas agregadas da API."""

import unittest
from unittest import mock

from controles import sismo_controle


def _limpar_cache():
    with sismo_controle._TRAVA_CACHE:
        sismo_controle._CACHE.clear()


class TestCacheApi(unittest.TestCase):
    def setUp(self):
        _limpar_cache()

    def tearDown(self):
        _limpar_cache()

    def test_mesmo_filtro_calcula_uma_vez(self):
        chamadas = []

        def fake_densidade(filtros, celula, metrica):
            chamadas.append(filtros)
            return {"total": 7, "cortes": [1.0], "celulas": []}

        with mock.patch.object(sismo_controle.modelo_sismo, "versao_dados", return_value="v1"), \
             mock.patch.object(sismo_controle.modelo_sismo, "densidade", fake_densidade):
            primeira = sismo_controle.api_densidade({"uf": "MG"})
            segunda = sismo_controle.api_densidade({"uf": "MG"})

        self.assertEqual(len(chamadas), 1)
        self.assertEqual(primeira[0], segunda[0] == 200 and 200)
        self.assertIn("cache-control", segunda[1])
        self.assertIn("max-age", segunda[1]["cache-control"])

    def test_versao_de_dados_invalida_cache(self):
        chamadas = []
        versao = {"valor": "v1"}

        def fake_densidade(filtros, celula, metrica):
            chamadas.append(1)
            return {"total": 7, "cortes": [1.0], "celulas": []}

        def fake_versao():
            return versao["valor"]

        with mock.patch.object(sismo_controle.modelo_sismo, "versao_dados", fake_versao), \
             mock.patch.object(sismo_controle.modelo_sismo, "densidade", fake_densidade):
            sismo_controle.api_densidade({})
            versao["valor"] = "v2"  # importação rodou
            sismo_controle.api_densidade({})

        self.assertEqual(len(chamadas), 2)

    def test_filtro_diferente_nao_reusa(self):
        chamadas = []

        def fake_densidade(filtros, celula, metrica):
            chamadas.append(filtros)
            return {"total": 7, "cortes": [1.0], "celulas": []}

        with mock.patch.object(sismo_controle.modelo_sismo, "versao_dados", return_value="v1"), \
             mock.patch.object(sismo_controle.modelo_sismo, "densidade", fake_densidade):
            sismo_controle.api_densidade({"uf": "MG"})
            sismo_controle.api_densidade({"uf": "SP"})

        self.assertEqual(len(chamadas), 2)

    def test_erro_nao_fica_em_cache(self):
        def fake_densidade(filtros, celula, metrica):
            raise RuntimeError("banco fora")

        with mock.patch.object(sismo_controle.modelo_sismo, "versao_dados", return_value="v1"), \
             mock.patch.object(sismo_controle.modelo_sismo, "densidade", fake_densidade):
            status, _, _ = sismo_controle.api_densidade({})
        self.assertEqual(status, 503)


class TestHistograma(unittest.TestCase):
    def test_faixas_normalizadas(self):
        linhas = [{"inicio": 4.0, "n": 3}, {"inicio": 4.5, "n": 1}]
        faixas = sismo_controle.modelo_sismo._histograma_magnitude(linhas)
        self.assertEqual(
            faixas,
            [{"de": 4.0, "ate": 4.5, "n": 3}, {"de": 4.5, "ate": 5.0, "n": 1}],
        )

    def test_versao_dados_sem_banco(self):
        from modelo import sismo

        with mock.patch.object(
            sismo.database, "consultar_um", side_effect=RuntimeError("fora")
        ):
            self.assertEqual(sismo.versao_dados(), "desconhecida")


if __name__ == "__main__":
    unittest.main()
