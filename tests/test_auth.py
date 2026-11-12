import unittest
from unittest.mock import patch

import config
from controles import auth_controle
from servicos import sessoes


def _dados(email="", senha="", proto="http"):
    return {
        "email": email,
        "senha": senha,
        "_ip": "127.0.0.1",
        "_proto": proto,
        "_cookies": {},
    }


class TestAuth(unittest.TestCase):
    def setUp(self):
        auth_controle._FALHAS.clear()
        self.credenciais = patch.multiple(
            config, LOGIN_EMAIL="melque@sismos.br", LOGIN_SENHA="senha-teste"
        )
        self.credenciais.start()
        self.addCleanup(self.credenciais.stop)

    def test_credenciais_certas(self):
        self.assertTrue(auth_controle.credenciais_validas("melque@sismos.br", "senha-teste"))
        self.assertTrue(auth_controle.credenciais_validas("MELQUE@sismos.br", "senha-teste"))

    def test_credenciais_erradas(self):
        self.assertFalse(auth_controle.credenciais_validas("melque@sismos.br", "x"))
        self.assertFalse(auth_controle.credenciais_validas("outro@sismos.br", "senha-teste"))
        self.assertFalse(auth_controle.credenciais_validas("", ""))

    def test_login_grava_cookie(self):
        status, cabecalhos, _ = auth_controle.login(
            _dados("melque@sismos.br", "senha-teste", proto="https")
        )
        self.assertEqual(status, 303)
        self.assertEqual(cabecalhos["location"], "/")
        cookie = cabecalhos["set-cookie"]
        self.assertIn("sismos_sessao=", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Secure", cookie)

    def test_login_invalido_nao_grava_cookie(self):
        status, cabecalhos, corpo = auth_controle.login(
            _dados("melque@sismos.br", "errada")
        )
        self.assertEqual(status, 401)
        self.assertNotIn("set-cookie", cabecalhos)
        self.assertIn(b"E-mail ou senha", corpo)

    def test_login_sem_credenciais_configuradas_falha(self):
        with patch.multiple(config, LOGIN_EMAIL="", LOGIN_SENHA=""):
            self.assertFalse(auth_controle.credenciais_validas("a@b.com", "x"))

    def test_bloqueio_apos_cinco_falhas(self):
        for _ in range(auth_controle.LIMITE_FALHAS):
            auth_controle.login(_dados("melque@sismos.br", "errada"))
        self.assertTrue(auth_controle.bloqueado("127.0.0.1"))
        status, _, _ = auth_controle.login(
            _dados("melque@sismos.br", "senha-teste")
        )
        self.assertEqual(status, 429)

    def test_logout_limpa_cookie(self):
        status, cabecalhos, _ = auth_controle.logout(_dados())
        self.assertEqual(status, 303)
        self.assertEqual(cabecalhos["location"], "/login")
        self.assertIn("Max-Age=0", cabecalhos["set-cookie"])

    def test_login_form_redireciona_autenticado(self):
        token = sessoes.criar_token("melque@sismos.br")
        dados = _dados()
        dados["_cookies"] = {sessoes.NOME_COOKIE: token}
        status, cabecalhos, _ = auth_controle.login_form(dados)
        self.assertEqual(status, 303)
        self.assertEqual(cabecalhos["location"], "/")


if __name__ == "__main__":
    unittest.main()
