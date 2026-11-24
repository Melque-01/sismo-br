"""Testes de fail-fast de configuração em servidor exposto."""

import unittest
from unittest import mock

import config


class TestAvisosDeProd(unittest.TestCase):
    def test_localhost_nao_exige_nada(self):
        self.assertEqual(config.avisos_de_prod("127.0.0.1"), [])
        self.assertEqual(config.avisos_de_prod("localhost"), [])

    def test_exposto_sem_segredo_reprova(self):
        ambiente = {"SESSION_SECRET": "", "DB_PASSWORD": "forte-123", "LOGIN_SENHA": "x"}
        with mock.patch.dict("os.environ", ambiente):
            avisos = config.avisos_de_prod("0.0.0.0")
        self.assertTrue(any("SESSION_SECRET" in aviso for aviso in avisos))

    def test_exposto_sem_senha_reprova(self):
        ambiente = {"SESSION_SECRET": "segredo", "DB_PASSWORD": "", "LOGIN_SENHA": "x"}
        with mock.patch.dict("os.environ", ambiente):
            avisos = config.avisos_de_prod("0.0.0.0")
        self.assertTrue(any("DB_PASSWORD" in aviso for aviso in avisos))

    def test_exposto_com_senha_padrao_reprova(self):
        ambiente = {
            "SESSION_SECRET": "segredo",
            "DB_PASSWORD": config.SENHA_BANCO_PADRAO,
            "LOGIN_SENHA": "x",
        }
        with mock.patch.dict("os.environ", ambiente):
            avisos = config.avisos_de_prod("0.0.0.0")
        self.assertTrue(any("DB_PASSWORD" in aviso for aviso in avisos))

    def test_exposto_sem_login_reprova(self):
        ambiente = {"SESSION_SECRET": "segredo", "DB_PASSWORD": "forte", "LOGIN_SENHA": ""}
        with mock.patch.dict("os.environ", ambiente):
            avisos = config.avisos_de_prod("0.0.0.0")
        self.assertTrue(any("LOGIN_SENHA" in aviso for aviso in avisos))

    def test_exposto_configurado_passa(self):
        ambiente = {"SESSION_SECRET": "segredo", "DB_PASSWORD": "forte", "LOGIN_SENHA": "x"}
        with mock.patch.dict("os.environ", ambiente):
            self.assertEqual(config.avisos_de_prod("0.0.0.0"), [])


if __name__ == "__main__":
    unittest.main()
