import os
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestMapaJs(unittest.TestCase):
    def test_usa_tiles_esri_e_nao_osm(self):
        caminho = os.path.join(RAIZ, "static", "js", "mapa.js")
        with open(caminho, encoding="utf-8") as arquivo:
            js = arquivo.read()
        self.assertIn("server.arcgisonline.com", js)
        self.assertNotIn("tile.openstreetmap.org", js)
        self.assertNotIn("basemaps.cartocdn.com", js)


if __name__ == "__main__":
    unittest.main()
