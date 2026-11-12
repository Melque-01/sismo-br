# -*- coding: utf-8 -*-
"""Injeta fontes, imagens e timeline no template do vídeo."""

import base64
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
TEMPLATE = RAIZ / "template.html"
SAIDA = RAIZ / "video.html"
ASSETS = RAIZ / "assets"


def b64(caminho: Path) -> str:
    return base64.b64encode(caminho.read_bytes()).decode("ascii")


def main() -> None:
    timeline = json.loads((RAIZ / "timeline.json").read_text(encoding="utf-8"))
    duracao = round(timeline["total"] + 1.8, 3)

    html = TEMPLATE.read_text(encoding="utf-8")
    substituicoes = {
        "{{FONT_REG}}": b64(Path(r"C:\Windows\Fonts\segoeui.ttf")),
        "{{FONT_BOLD}}": b64(Path(r"C:\Windows\Fonts\segoeuib.ttf")),
        "{{FONT_MONO}}": b64(Path(r"C:\Windows\Fonts\consola.ttf")),
        "{{IMG_MAPA}}": b64(ASSETS / "mapa.jpg"),
        "{{IMG_FILTROS}}": b64(ASSETS / "filtros.jpg"),
        "{{IMG_TABELA}}": b64(ASSETS / "tabela.jpg"),
        "{{IMG_SERIE}}": b64(ASSETS / "serie.jpg"),
        "{{IMG_HIST}}": b64(ASSETS / "histograma.jpg"),
        "{{IMG_LOGIN}}": b64(ASSETS / "login.jpg"),
        "{{IMG_REGISTRAR}}": b64(ASSETS / "registrar.jpg"),
        "__CENAS__": json.dumps(timeline["cenas"], ensure_ascii=False),
        "__DURACAO__": str(duracao),
    }
    for chave, valor in substituicoes.items():
        html = html.replace(chave, valor)
    SAIDA.write_text(html, encoding="utf-8")
    print("video.html:", round(SAIDA.stat().st_size / 1024 / 1024, 2), "MB")
    print("duração:", duracao, "s")


if __name__ == "__main__":
    main()
