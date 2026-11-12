import unittest

from servicos import senhas


class TestSenhas(unittest.TestCase):
    def test_hash_e_verificacao(self):
        armazenado = senhas.hash_senha("minha-senha-123")
        self.assertTrue(armazenado.startswith("pbkdf2_sha256$"))
        self.assertTrue(senhas.verificar_senha("minha-senha-123", armazenado))
        self.assertFalse(senhas.verificar_senha("outra-senha", armazenado))

    def test_salt_diferente_por_hash(self):
        a = senhas.hash_senha("mesma-senha")
        b = senhas.hash_senha("mesma-senha")
        self.assertNotEqual(a, b)
        self.assertTrue(senhas.verificar_senha("mesma-senha", a))
        self.assertTrue(senhas.verificar_senha("mesma-senha", b))

    def test_hash_malformado(self):
        for invalido in ("", "abc", "pbkdf2_sha256$x$y$z", "md5$1$aa$bb"):
            self.assertFalse(senhas.verificar_senha("senha", invalido))

    def test_senha_vazia(self):
        with self.assertRaises(ValueError):
            senhas.hash_senha("")

    def test_senha_longa_nao_autentica(self):
        armazenado = senhas.hash_senha("ok")
        self.assertFalse(senhas.verificar_senha("x" * 300, armazenado))


if __name__ == "__main__":
    unittest.main()
