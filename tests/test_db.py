import os
import unittest
from unittest import skipUnless

BANCO_OK = os.getenv("SISMOS_TESTAR_DB") == "1"


class TestSchemaEmComandos(unittest.TestCase):
    def test_ignora_ponto_e_virgula_em_comentario(self):
        from db.database import _comandos

        script = (
            "CREATE TABLE a (x INT);\n"
            "-- comentario; com ponto e virgula\n"
            "CREATE INDEX i ON a (x);\n"
        )
        comandos = _comandos(script)
        self.assertEqual(len(comandos), 2)
        self.assertTrue(comandos[1].startswith("CREATE INDEX"))

    def test_schema_real_gera_apenas_comandos_uteis(self):
        from db.database import CAMINHO_SCHEMA, _comandos

        with open(CAMINHO_SCHEMA, encoding="utf-8") as arquivo:
            comandos = _comandos(arquivo.read())
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS sismos" in c for c in comandos))
        self.assertGreaterEqual(len(comandos), 10)
        for comando in comandos:
            self.assertIn(
                comando.split()[0], {"CREATE", "COMMENT", "ALTER", "GRANT"}
            )

EVENTO = {
    "fonte": "FDSN",
    "evento_id": "teste-1",
    "data_hora": None,
    "ano": 2026,
    "lat": -20.03,
    "lon": -48.82,
    "profundidade_km": None,
    "magnitude": 3.0,
    "tipo_magnitude": "mR",
    "categoria": None,
    "uf": "MG",
    "localidade": "Frutal/MG",
    "autor": "teste",
}


@skipUnless(BANCO_OK, "defina SISMOS_TESTAR_DB=1 com PostGIS disponivel")
class TestBanco(unittest.TestCase):
    def tearDown(self):
        """Remove o que o teste gravou: o banco é o mesmo da aplicação."""
        from db import database

        database.executar(
            "DELETE FROM sismos WHERE evento_id LIKE %s", ("teste-%",)
        )
        database.executar("DELETE FROM importacoes WHERE arquivo = 'teste.dat'")

    def test_upsert_idempotente(self):
        from db import database
        from modelo.sismo import upsert_lote

        database.criar_tabelas()
        upsert_lote([EVENTO])
        upsert_lote([EVENTO])
        linha = database.consultar_um(
            "SELECT count(*) AS n FROM sismos WHERE evento_id = %s", ("teste-1",)
        )
        self.assertEqual(linha["n"], 1)

    def test_estados_carregados(self):
        from modelo.sismo import carregar_estados

        self.assertEqual(carregar_estados("dados/brasil_uf.geojson"), 27)

    def test_importacao_registrada(self):
        from modelo import importacao

        importacao_id = importacao.iniciar("SISBRA", "teste.dat")
        importacao.concluir(importacao_id, 10, 8, 2)
        from db.database import consultar_um

        linha = consultar_um(
            "SELECT * FROM importacoes WHERE id = %s", (importacao_id,)
        )
        self.assertEqual(linha["linhas_importadas"], 8)
        self.assertIsNotNone(linha["concluido_em"])


if __name__ == "__main__":
    unittest.main()
