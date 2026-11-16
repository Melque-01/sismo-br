import json
import unittest

from controles import home_controle, sismo_controle
from rotas.rotas import ROTAS


class TestRotas(unittest.TestCase):
    def test_rotas_declaradas(self):
        for caminho in [
            "/",
            "/saiba-mais",
            "/login",
            "/registrar",
            "/api/densidade",
            "/api/sismos",
            "/api/celula",
            "/api/evento",
            "/api/estatisticas",
            "/api/filtros",
            "/api/status",
            "/api/importacoes",
        ]:
            self.assertIn(("GET", caminho), ROTAS)
        self.assertIn(("POST", "/login"), ROTAS)
        self.assertIn(("GET", "/registrar"), ROTAS)
        self.assertIn(("POST", "/registrar"), ROTAS)
        self.assertIn(("POST", "/logout"), ROTAS)

    def test_pagina_saiba_mais_renderiza(self):
        status, cabecalhos, corpo = home_controle.saiba_mais({})
        self.assertEqual(status, 200)
        self.assertIn("text/html", cabecalhos["content-type"])
        html = corpo.decode("utf-8")
        self.assertIn("sismos-br-mobile.mp4", html)
        self.assertIn("sismos-br-desktop.mp4", html)
        self.assertIn("O que é o Sismos BR", html)

    def test_index_sem_botao_saiba_mais(self):
        status, _, corpo = home_controle.index({})
        self.assertEqual(status, 200)
        self.assertNotIn(b'class="botao-saiba-mais"', corpo)

    def test_filtro_invalido_vira_400(self):
        status, cabecalhos, corpo = sismo_controle.api_densidade({"celula": "0.3"})
        self.assertEqual(status, 400)
        self.assertIn("application/json", cabecalhos["content-type"])
        self.assertIn("erro", json.loads(corpo))

    def test_celula_coordenada_invalida(self):
        status, _, _ = sismo_controle.api_celula({"lat": "999", "lon": "-45"})
        self.assertEqual(status, 400)

    def test_celula_sem_coordenada(self):
        status, _, _ = sismo_controle.api_celula({})
        self.assertEqual(status, 400)

    def test_evento_id_invalido(self):
        status, _, _ = sismo_controle.api_evento({"id": "abc"})
        self.assertEqual(status, 400)

    def test_metrica_invalida(self):
        status, _, _ = sismo_controle.api_densidade({"metrica": "kde"})
        self.assertEqual(status, 400)

    def test_limite_de_pontos_acima_do_teto_vira_400(self):
        status, _, _ = sismo_controle.api_sismos({"limite": "999999"})
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
