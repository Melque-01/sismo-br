import unittest

from servicos import sessoes


class TestSessoes(unittest.TestCase):
    def test_ida_e_volta(self):
        token = sessoes.criar_token("Melque@Exemplo.com")
        self.assertEqual(sessoes.validar_token(token), "melque@exemplo.com")

    def test_token_expirado(self):
        token = sessoes.criar_token("a@b.com", ttl=-1)
        self.assertIsNone(sessoes.validar_token(token))

    def test_token_adulterado(self):
        token = sessoes.criar_token("a@b.com")
        self.assertIsNone(sessoes.validar_token(token[:-2] + "xy"))

    def test_token_vazio_ou_lixo(self):
        self.assertIsNone(sessoes.validar_token(""))
        self.assertIsNone(sessoes.validar_token(None))
        self.assertIsNone(sessoes.validar_token("sem-ponto"))
        self.assertIsNone(sessoes.validar_token("a.b"))

    def test_cookie_nome(self):
        self.assertEqual(sessoes.NOME_COOKIE, "sismos_sessao")


if __name__ == "__main__":
    unittest.main()
