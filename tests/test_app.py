import email
import io
import unittest

import app


def _handler(cabecalhos=None, caminho="/api/status"):
    """Manipulador HTTP com socket/headers falsos, sem abrir porta."""
    mensagem = email.message.Message()
    for nome, valor in (cabecalhos or {}).items():
        mensagem[nome] = valor
    manipulador = app.Manipulador.__new__(app.Manipulador)
    manipulador.path = caminho
    manipulador.requestline = "GET {} HTTP/1.1".format(caminho)
    manipulador.headers = mensagem
    manipulador.wfile = io.BytesIO()
    manipulador.client_address = ("200.1.2.3", 12345)
    manipulador.protocol_version = "HTTP/1.1"
    manipulador.request_version = "HTTP/1.1"
    manipulador.close_connection = False
    manipulador._headers_buffer = []
    return manipulador


class TestIpCliente(unittest.TestCase):
    def setUp(self):
        self.proxies_originais = app.PROXIES_CONFIAVEIS
        app.PROXIES_CONFIAVEIS = {"127.0.0.1"}

    def tearDown(self):
        app.PROXIES_CONFIAVEIS = self.proxies_originais

    def test_proxy_confiavel_usa_x_real_ip(self):
        self.assertEqual(
            app.ip_cliente("127.0.0.1", {"x-real-ip": "200.1.2.3"}), "200.1.2.3"
        )

    def test_proxy_usa_primeiro_x_forwarded_for(self):
        self.assertEqual(
            app.ip_cliente(
                "127.0.0.1", {"x-forwarded-for": "200.1.2.3, 10.0.0.1"}
            ),
            "200.1.2.3",
        )

    def test_cliente_direto_ignora_cabecalho(self):
        self.assertEqual(
            app.ip_cliente("200.1.2.3", {"x-real-ip": "1.1.1.1"}), "200.1.2.3"
        )

    def test_ip_invalido_cai_no_peer(self):
        self.assertEqual(
            app.ip_cliente("127.0.0.1", {"x-real-ip": "nao-e-ip"}), "127.0.0.1"
        )


class TestSegurancaHttp(unittest.TestCase):
    def _resposta(self, cabecalhos, caminho="/api/status"):
        manipulador = _handler(cabecalhos, caminho)
        manipulador._despachar("GET")
        return manipulador.wfile.getvalue().decode("utf-8", "replace").lower()

    def test_http_do_proxy_redireciona_para_https(self):
        resposta = self._resposta(
            {"x-forwarded-proto": "http", "host": "sismosbr.duckdns.org"}
        )
        self.assertTrue(resposta.startswith("http/1.1 301"), resposta[:80])
        self.assertIn(
            "location: https://sismosbr.duckdns.org/api/status", resposta
        )

    def test_sem_cabecalho_proxy_nao_redireciona(self):
        resposta = self._resposta({})
        self.assertNotIn("location:", resposta)
        self.assertNotIn("strict-transport-security", resposta)

    def test_https_envia_hsts(self):
        resposta = self._resposta({"x-forwarded-proto": "https"})
        self.assertIn("strict-transport-security: max-age=31536000", resposta)

    def test_toda_resposta_envia_headers_basicos(self):
        resposta = self._resposta({})
        self.assertIn("x-content-type-options: nosniff", resposta)
        self.assertIn("x-frame-options: deny", resposta)
        self.assertIn("referrer-policy: no-referrer", resposta)

    def test_api_envia_no_store(self):
        resposta = self._resposta({})
        self.assertIn("cache-control: no-store", resposta)

    def test_erro_500_generico_sem_detalhe(self):
        def explosao(dados):
            raise RuntimeError("segredo interno /home/melque/.env")

        rotas_originais = app.ROTAS
        publicas_originais = app.ROTAS_PUBLICAS
        try:
            app.ROTAS = {("GET", "/api/teste-erro"): explosao}
            app.ROTAS_PUBLICAS = {("GET", "/api/teste-erro")}
            resposta = self._resposta({}, caminho="/api/teste-erro")
        finally:
            app.ROTAS = rotas_originais
            app.ROTAS_PUBLICAS = publicas_originais
        self.assertIn('"erro interno"', resposta)
        self.assertNotIn("segredo interno", resposta)
        self.assertNotIn(".env", resposta)


class TestPaginaSaibaMais(unittest.TestCase):
    def test_rota_publica_sem_login(self):
        self.assertIn(("GET", "/saiba-mais"), app.ROTAS_PUBLICAS)

    def test_despacha_sem_cookie(self):
        manipulador = _handler({}, "/saiba-mais")
        manipulador._despachar("GET")
        resposta = manipulador.wfile.getvalue()
        self.assertTrue(resposta.startswith(b"HTTP/1.1 200"), resposta[:80])

    def test_head_sem_cookie_nao_devolve_corpo(self):
        manipulador = _handler({}, "/saiba-mais")
        manipulador.command = "HEAD"
        manipulador._despachar("HEAD")
        cabecalho, _, corpo = manipulador.wfile.getvalue().partition(b"\r\n\r\n")
        self.assertIn(b"200", cabecalho.splitlines()[0])
        self.assertEqual(corpo, b"")


class TestStaticSeguranca(unittest.TestCase):
    def _status(self, caminho):
        manipulador = _handler({}, caminho)
        manipulador._despachar("GET")
        return manipulador.wfile.getvalue().splitlines()[0]

    def test_barra_invertida_codificada_nao_escapa(self):
        self.assertIn(b"403", self._status("/static/css/..%5c..%5cREADME.md"))

    def test_ponto_ponto_posix_nao_escapa(self):
        self.assertIn(b"403", self._status("/static/css/../../README.md"))

    def test_ponto_ponto_codificado_nao_escapa(self):
        self.assertIn(b"403", self._status("/static/%2e%2e/%2e%2e/README.md"))


class TestStaticRange(unittest.TestCase):
    CAMINHO = "/static/css/style.css"

    def _resposta(self, range_header=None):
        cabecalhos = {"range": range_header} if range_header else {}
        manipulador = _handler(cabecalhos, self.CAMINHO)
        manipulador._despachar("GET")
        bruto = manipulador.wfile.getvalue()
        cabecalho, _, corpo = bruto.partition(b"\r\n\r\n")
        return cabecalho.decode("latin-1").lower(), corpo

    def test_sem_range_devolve_arquivo_inteiro(self):
        cabecalho, corpo = self._resposta()
        self.assertIn("200", cabecalho.splitlines()[0])
        self.assertIn("accept-ranges: bytes", cabecalho)
        self.assertIn(b":root", corpo)

    def test_range_aberto_devolve_206(self):
        cabecalho, corpo = self._resposta("bytes=0-9")
        self.assertIn("206", cabecalho.splitlines()[0])
        self.assertIn("content-range: bytes 0-9/", cabecalho)
        self.assertIn(b":root", corpo)

    def test_range_sufixo_devolve_ultimos_bytes(self):
        cabecalho, corpo = self._resposta("bytes=-10")
        self.assertIn("206", cabecalho.splitlines()[0])
        self.assertEqual(len(corpo), 10)

    def test_range_aberto_ate_o_fim(self):
        cabecalho, corpo = self._resposta("bytes=0-")
        self.assertIn("206", cabecalho.splitlines()[0])
        self.assertIn("content-range: bytes 0-", cabecalho)
        self.assertGreater(len(corpo), 1000)

    def test_range_sufixo_maior_que_arquivo_devolve_tudo(self):
        cabecalho, corpo = self._resposta("bytes=-999999")
        self.assertIn("206", cabecalho.splitlines()[0])
        self.assertGreater(len(corpo), 1000)

    def test_head_com_range_nao_devolve_corpo(self):
        manipulador = _handler({"range": "bytes=0-1023"}, self.CAMINHO)
        manipulador.command = "HEAD"
        manipulador._despachar("HEAD")
        cabecalho, _, corpo = manipulador.wfile.getvalue().partition(b"\r\n\r\n")
        self.assertIn(b"206", cabecalho.splitlines()[0])
        self.assertIn(b"content-range: bytes 0-1023/", cabecalho)
        self.assertEqual(corpo, b"")

    def test_range_fora_do_arquivo_devolve_416(self):
        cabecalho, corpo = self._resposta("bytes=999999-")
        self.assertIn("416", cabecalho.splitlines()[0])
        self.assertIn("content-range: bytes */", cabecalho)
        self.assertEqual(corpo, b"")

    def test_range_multiplo_e_invalido(self):
        cabecalho, _ = self._resposta("bytes=0-1,4-5")
        self.assertIn("416", cabecalho.splitlines()[0])


if __name__ == "__main__":
    unittest.main()
