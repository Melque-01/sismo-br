import unittest

from controles.sismo_controle import montar_filtros
from modelo.sismo import sql_filtros


class TestSqlFiltros(unittest.TestCase):
    def test_sem_filtro(self):
        where, params = sql_filtros(montar_filtros({}))
        self.assertEqual(where, "")
        self.assertEqual(params, [])

    def test_uf_e_magnitude(self):
        where, params = sql_filtros(montar_filtros({"uf": "MG", "mag_min": "3"}))
        self.assertIn("uf = %s", where)
        self.assertIn("magnitude >= %s", where)
        self.assertEqual(params, ["MG", 3.0])

    def test_fonte(self):
        where, params = sql_filtros(montar_filtros({"fonte": "SISBRA"}))
        self.assertIn("fonte = %s", where)
        self.assertEqual(params, ["SISBRA"])

    def test_periodo(self):
        where, params = sql_filtros(
            montar_filtros({"ano_ini": "1980", "ano_fim": "2000"})
        )
        self.assertIn("ano BETWEEN %s AND %s", where)
        self.assertEqual(params, [1980, 2000])

    def test_categoria_e_profundidade(self):
        where, params = sql_filtros(
            montar_filtros({"categoria": "I", "prof_max": "30"})
        )
        self.assertIn("categoria = %s", where)
        self.assertIn("profundidade_km <= %s", where)
        self.assertEqual(params, ["I", 30.0])

    def test_where_comeca_com_espaco(self):
        where, _ = sql_filtros(montar_filtros({"uf": "SP"}))
        self.assertTrue(where.startswith(" WHERE "))


if __name__ == "__main__":
    unittest.main()
