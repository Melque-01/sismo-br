import os
import unittest
from unittest import skipUnless

BANCO_OK = os.getenv("SISMOS_TESTAR_DB") == "1"


@skipUnless(BANCO_OK, "defina SISMOS_TESTAR_DB=1")
class TestConsultas(unittest.TestCase):
    def test_densidade_soma_igual_total(self):
        from controles.sismo_controle import montar_filtros
        from modelo.sismo import densidade

        r = densidade(montar_filtros({}), 0.5)
        self.assertEqual(sum(c["n"] for c in r["celulas"]), r["total"])

    def test_celula_maior_agrega_mais(self):
        from controles.sismo_controle import montar_filtros
        from modelo.sismo import densidade

        f = montar_filtros({})
        self.assertLessEqual(
            len(densidade(f, 2.0)["celulas"]), len(densidade(f, 0.5)["celulas"])
        )

    def test_sem_evento_fora_do_brasil(self):
        from db.database import consultar_um

        r = consultar_um(
            """SELECT count(*) AS n FROM sismos s
               WHERE NOT EXISTS (SELECT 1 FROM estados e
                                 WHERE ST_Contains(e.geom, s.geom))"""
        )
        self.assertEqual(r["n"], 0)

    def test_filtro_magnitude_descarta_nulos(self):
        from controles.sismo_controle import montar_filtros
        from db.database import consultar_um
        from modelo.sismo import sql_filtros, estatisticas

        f = montar_filtros({"mag_min": "0"})
        where, params = sql_filtros(f)
        r = consultar_um(
            "SELECT count(*) AS n FROM sismos {}".format(where), tuple(params)
        )
        self.assertLess(r["n"], estatisticas(montar_filtros({}))["total"])

    def test_eventos_da_celula_estao_na_celula(self):
        from controles.sismo_controle import montar_filtros
        from modelo.sismo import densidade, eventos_celula

        f = montar_filtros({})
        celula = densidade(f, 1.0)["celulas"][0]
        eventos = eventos_celula(
            f, celula["y"], celula["x"], 1.0, limite=50
        )
        self.assertTrue(eventos)
        for evento in eventos:
            self.assertGreaterEqual(evento["lat"], celula["y"])
            self.assertLess(evento["lat"], celula["y"] + 1.0)
            self.assertGreaterEqual(evento["lon"], celula["x"])
            self.assertLess(evento["lon"], celula["x"] + 1.0)

    def test_estatisticas_consistentes(self):
        from controles.sismo_controle import montar_filtros
        from modelo.sismo import estatisticas

        e = estatisticas(montar_filtros({}))
        self.assertEqual(sum(item["n"] for item in e["por_fonte"]), e["total"])
        self.assertEqual(sum(item["n"] for item in e["serie_anual"]), e["total"])

    def test_filtro_vazio_nao_quebra(self):
        from controles.sismo_controle import montar_filtros
        from modelo.sismo import densidade, estatisticas

        f = montar_filtros({"ano_ini": "1900", "ano_fim": "1901", "uf": "AC"})
        d = densidade(f, 0.5)
        self.assertEqual(d["total"], 0)
        self.assertEqual(d["celulas"], [])
        self.assertEqual(d["cortes"], [])
        self.assertEqual(estatisticas(f)["total"], 0)


if __name__ == "__main__":
    unittest.main()
