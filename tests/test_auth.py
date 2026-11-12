import unittest
from unittest.mock import patch

from controles import auth_controle, home_controle
from servicos import senhas, sessoes

HASH = senhas.hash_senha("senha-teste")
USUARIO = {"id": 1, "email": "melque@sismos.br", "senha_hash": HASH}
CSRF = "csrf-de-teste-1234567890"


def _dados(
    email="", senha="", confirmar="", proto="http", csrf=CSRF, cookies=None
):
    return {
        "email": email,
        "senha": senha,
        "confirmar": confirmar,
        "_ip": "127.0.0.1",
        "_proto": proto,
        "_csrf": csrf,
        "_cookies": (
            {sessoes.NOME_COOKIE_CSRF: CSRF} if cookies is None else cookies
        ),
    }


class TestAuth(unittest.TestCase):
    def setUp(self):
        auth_controle._FALHAS.clear()
        auth_controle._CADASTROS.clear()
        auth_controle._FALHAS_CONTA.clear()

    def test_autenticar_certo(self):
        with patch.object(
            auth_controle.usuario_modelo, "buscar_por_email", return_value=USUARIO
        ):
            self.assertTrue(auth_controle.autenticar("melque@sismos.br", "senha-teste"))

    def test_autenticar_senha_errada(self):
        with patch.object(
            auth_controle.usuario_modelo, "buscar_por_email", return_value=USUARIO
        ):
            self.assertFalse(auth_controle.autenticar("melque@sismos.br", "x"))

    def test_autenticar_email_inexistente(self):
        with patch.object(
            auth_controle.usuario_modelo, "buscar_por_email", return_value=None
        ):
            self.assertFalse(auth_controle.autenticar("nao@existe.com", "x"))

    def test_login_grava_cookie(self):
        with patch.object(
            auth_controle.usuario_modelo, "buscar_por_email", return_value=USUARIO
        ):
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
        with patch.object(
            auth_controle.usuario_modelo, "buscar_por_email", return_value=USUARIO
        ):
            status, cabecalhos, corpo = auth_controle.login(
                _dados("melque@sismos.br", "errada")
            )
        self.assertEqual(status, 401)
        self.assertNotIn("set-cookie", cabecalhos)
        self.assertIn(b"E-mail ou senha", corpo)

    def test_bloqueio_apos_cinco_falhas(self):
        with patch.object(
            auth_controle.usuario_modelo, "buscar_por_email", return_value=USUARIO
        ):
            for _ in range(auth_controle.LIMITE_FALHAS):
                auth_controle.login(_dados("melque@sismos.br", "errada"))
        self.assertTrue(auth_controle.bloqueado("127.0.0.1"))
        status, _, _ = auth_controle.login(_dados("melque@sismos.br", "senha-teste"))
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

    def test_login_form_grava_cookie_csrf(self):
        status, cabecalhos, corpo = auth_controle.login_form(_dados(cookies={}))
        self.assertEqual(status, 200)
        cookie = cabecalhos["set-cookie"]
        self.assertIn(sessoes.NOME_COOKIE_CSRF + "=", cookie)
        token = cookie.split(sessoes.NOME_COOKIE_CSRF + "=")[1].split(";")[0]
        self.assertIn(token.encode("ascii"), corpo)

    def test_login_sem_csrf_responde_403(self):
        with patch.object(
            auth_controle.usuario_modelo, "buscar_por_email", return_value=USUARIO
        ):
            status, _, _ = auth_controle.login(
                _dados("melque@sismos.br", "senha-teste", csrf="")
            )
        self.assertEqual(status, 403)

    def test_login_csrf_diferente_do_cookie_responde_403(self):
        dados = _dados("melque@sismos.br", "senha-teste")
        dados["_csrf"] = "token-forjado-por-outro-site"
        with patch.object(
            auth_controle.usuario_modelo, "buscar_por_email", return_value=USUARIO
        ):
            status, _, _ = auth_controle.login(dados)
        self.assertEqual(status, 403)

    def test_logout_sem_csrf_nao_apaga_sessao(self):
        status, cabecalhos, _ = auth_controle.logout(_dados(csrf=""))
        self.assertEqual(status, 303)
        self.assertNotIn("set-cookie", cabecalhos)

    def test_conta_bloqueia_apos_dez_falhas_de_ips_diferentes(self):
        with patch.object(
            auth_controle.usuario_modelo, "buscar_por_email", return_value=USUARIO
        ):
            for indice in range(auth_controle.LIMITE_CONTA):
                dados = _dados("melque@sismos.br", "errada")
                dados["_ip"] = "10.0.0.{}".format(indice)
                auth_controle.login(dados)
            outro = _dados("melque@sismos.br", "senha-teste")
            outro["_ip"] = "10.0.0.99"
            status, _, _ = auth_controle.login(outro)
        self.assertEqual(status, 429)

    def test_falhas_de_uma_conta_nao_bloqueiam_outra(self):
        with patch.object(
            auth_controle.usuario_modelo, "buscar_por_email", return_value=USUARIO
        ):
            for indice in range(auth_controle.LIMITE_CONTA):
                dados = _dados("melque@sismos.br", "errada")
                dados["_ip"] = "10.0.0.{}".format(indice)
                auth_controle.login(dados)
            outro = _dados("outra@exemplo.com", "senha-teste")
            outro["_ip"] = "10.0.0.99"
            status, _, _ = auth_controle.login(outro)
        self.assertEqual(status, 303)

    def test_login_certo_zera_contador_da_conta(self):
        with patch.object(
            auth_controle.usuario_modelo, "buscar_por_email", return_value=USUARIO
        ):
            for indice in range(auth_controle.LIMITE_CONTA - 1):
                dados = _dados("melque@sismos.br", "errada")
                dados["_ip"] = "10.0.1.{}".format(indice)
                auth_controle.login(dados)
            status, _, _ = auth_controle.login(
                _dados("melque@sismos.br", "senha-teste")
            )
            self.assertEqual(status, 303)
            for indice in range(auth_controle.LIMITE_CONTA - 1):
                dados = _dados("melque@sismos.br", "errada")
                dados["_ip"] = "10.0.2.{}".format(indice)
                auth_controle.login(dados)
            self.assertFalse(auth_controle.conta_bloqueada("melque@sismos.br"))

    def test_registro_de_falhas_nao_cresce_sem_limite(self):
        with patch.object(
            auth_controle.usuario_modelo, "buscar_por_email", return_value=None
        ), patch.object(auth_controle, "LIMITE_CHAVES", 2):
            for indice in range(6):
                dados = _dados("conta{}@exemplo.com".format(indice), "errada")
                dados["_ip"] = "10.0.3.{}".format(indice)
                auth_controle.login(dados)
        self.assertLessEqual(len(auth_controle._FALHAS_CONTA), 2)


class TestCadastro(unittest.TestCase):
    def setUp(self):
        auth_controle._FALHAS.clear()
        auth_controle._CADASTROS.clear()
        auth_controle._FALHAS_CONTA.clear()

    def test_cadastro_cria_e_entra(self):
        with patch.object(
            auth_controle.usuario_modelo, "buscar_por_email", return_value=None
        ), patch.object(
            auth_controle.usuario_modelo, "criar", return_value=10
        ) as criar:
            status, cabecalhos, _ = auth_controle.registrar(
                _dados("Novo@Exemplo.com", "senha-forte", "senha-forte", "https")
            )
        self.assertEqual(status, 303)
        self.assertEqual(cabecalhos["location"], "/")
        self.assertIn("sismos_sessao=", cabecalhos["set-cookie"])
        self.assertEqual(criar.call_args[0][0], "novo@exemplo.com")
        self.assertTrue(criar.call_args[0][1].startswith("pbkdf2_sha256$"))

    def test_cadastro_email_duplicado(self):
        with patch.object(
            auth_controle.usuario_modelo, "buscar_por_email", return_value=USUARIO
        ):
            status, _, corpo = auth_controle.registrar(
                _dados("melque@sismos.br", "senha-forte", "senha-forte")
            )
        self.assertEqual(status, 409)
        self.assertIn(b"j\xc3\xa1 est\xc3\xa1 cadastrado", corpo)

    def test_cadastro_email_invalido(self):
        status, _, _ = auth_controle.registrar(
            _dados("sem-arroba", "senha-forte", "senha-forte")
        )
        self.assertEqual(status, 400)

    def test_cadastro_senha_curta(self):
        status, _, _ = auth_controle.registrar(
            _dados("a@b.com", "123", "123")
        )
        self.assertEqual(status, 400)

    def test_cadastro_senhas_diferentes(self):
        status, _, _ = auth_controle.registrar(
            _dados("a@b.com", "senha-forte", "outra-senha")
        )
        self.assertEqual(status, 400)

    def test_cadastro_limitado_por_ip(self):
        for _ in range(auth_controle.LIMITE_CADASTROS):
            auth_controle.registrar(_dados("invalido", "123", "123"))
        status, _, _ = auth_controle.registrar(
            _dados("a@b.com", "senha-forte", "senha-forte")
        )
        self.assertEqual(status, 429)

    def test_cadastro_sem_csrf_responde_403(self):
        status, _, _ = auth_controle.registrar(
            _dados("a@b.com", "senha-forte", "senha-forte", csrf="")
        )
        self.assertEqual(status, 403)

    def test_banco_fora_do_ar(self):
        with patch.object(
            auth_controle.usuario_modelo,
            "buscar_por_email",
            side_effect=RuntimeError("sem banco"),
        ):
            status, _, corpo = auth_controle.registrar(
                _dados("a@b.com", "senha-forte", "senha-forte")
            )
        self.assertEqual(status, 503)


class TestHome(unittest.TestCase):
    def test_index_inclui_campo_csrf_no_logout(self):
        dados = {"_email": "melque@sismos.br", "_cookies": {}, "_proto": "https"}
        status, cabecalhos, corpo = home_controle.index(dados)
        self.assertEqual(status, 200)
        self.assertIn(b'name="_csrf"', corpo)
        self.assertIn(sessoes.NOME_COOKIE_CSRF, cabecalhos["set-cookie"])


if __name__ == "__main__":
    unittest.main()
