# -*- coding: utf-8 -*-
"""Gera a narração do vídeo (pt-BR) e a linha do tempo das cenas."""

import asyncio
import json
import subprocess
from pathlib import Path

import edge_tts

RAIZ = Path(__file__).resolve().parent
AUDIO = RAIZ / "audio"
AUDIO.mkdir(exist_ok=True)

VOZ = "pt-BR-AntonioNeural"
RITMO = "-2%"
PAUSA = 0.45  # segundos entre cenas

CENAS = [
    (
        "intro",
        "O Sismos BR é um mapa interativo que mostra onde os terremotos "
        "registrados no Brasil se concentram. Ele cruza o catálogo histórico "
        "do SISBRA com os eventos recentes do serviço FDSN, da USP.",
    ),
    (
        "dados",
        "São cinco mil cento e quarenta e um eventos, de mil seiscentos e "
        "noventa até dois mil e vinte e seis. Cada registro passa por um "
        "parser que corrige horário local, valida coordenadas e descarta o "
        "que está fora do território brasileiro.",
    ),
    (
        "postgis",
        "Os eventos viram pontos no PostgreSQL com PostGIS. A malha do IBGE "
        "define o limite das vinte e sete unidades federativas, e o banco "
        "calcula a grade: cada célula tem meio grau e guarda a contagem de "
        "sismos.",
    ),
    (
        "mapa",
        "No mapa, a cor indica densidade: quanto mais claro, mais eventos "
        "naquela área. A legenda mostra as faixas, e a métrica normalizada "
        "divide a contagem pela área real da célula, permitindo comparar "
        "regiões de tamanhos diferentes.",
    ),
    (
        "filtros",
        "Os filtros ajustam período, magnitude, profundidade, fonte e estado. "
        "Ao clicar numa célula, o rodapé lista os eventos que a formaram, com "
        "data, magnitude, profundidade e a ficha completa de cada sismo.",
    ),
    (
        "painel",
        "O painel resume o recorte: total de eventos, período, maior "
        "magnitude, estados com mais registros, série anual e distribuição "
        "de magnitudes.",
    ),
    (
        "login",
        "O acesso é protegido por login. O usuário pode criar a própria conta "
        "em segundos; a senha é gravada com hash PBKDF2, e a sessão fica num "
        "cookie assinado.",
    ),
    (
        "arquitetura",
        "Por dentro, o sistema segue o padrão MVC em Python puro. O navegador "
        "chama a API, os controllers validam os filtros, os models executam "
        "SQL parametrizado e o PostGIS responde.",
    ),
    (
        "cloudflare",
        "A publicação usa o Cloudflare Tunnel: o servidor abre uma conexão de "
        "saída, sem precisar de IP público nem liberar portas. A Cloudflare "
        "entrega o HTTPS e o professor acessa por uma URL pública.",
    ),
    (
        "fechamento",
        "Sismos BR. Dados abertos, mapa de densidade e uma arquitetura "
        "simples, do catálogo ao navegador.",
    ),
]


def duracao(caminho: Path) -> float:
    saida = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(caminho),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(saida.stdout.strip())


async def gerar(texto: str, destino: Path) -> None:
    comunicador = edge_tts.Communicate(texto, VOZ, rate=RITMO)
    await comunicador.save(str(destino))


def main() -> None:
    cenas = []
    inicio = 0.0
    for nome, texto in CENAS:
        mp3 = AUDIO / f"{nome}.mp3"
        if not mp3.exists():
            asyncio.run(gerar(texto, mp3))
        d = duracao(mp3)
        cenas.append(
            {
                "nome": nome,
                "inicio": round(inicio, 3),
                "duracao": round(d, 3),
                "fim": round(inicio + d, 3),
            }
        )
        inicio += d + PAUSA

    timeline = {
        "voz": VOZ,
        "pausa": PAUSA,
        "total": round(inicio, 3),
        "cenas": cenas,
    }
    (RAIZ / "timeline.json").write_text(
        json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(timeline, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
