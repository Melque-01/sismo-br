# -*- coding: utf-8 -*-
"""Junta a narração das cenas em um WAV contínuo, respeitando a timeline."""

import json
import subprocess
import wave
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
AUDIO = RAIZ / "audio"
TMP = RAIZ / "audio" / "tmp"
TMP.mkdir(exist_ok=True)

TAXA = 48000
CANAIS = 2


def decodificar(mp3: Path, wav: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y", "-i", str(mp3),
            "-ar", str(TAXA), "-ac", str(CANAIS), str(wav),
        ],
        check=True,
    )


def ler_pcm(caminho: Path) -> bytes:
    with wave.open(str(caminho), "rb") as w:
        if w.getframerate() != TAXA or w.getnchannels() != CANAIS:
            raise ValueError("formato inesperado em " + str(caminho))
        return w.readframes(w.getnframes())


def main() -> None:
    timeline = json.loads((RAIZ / "timeline.json").read_text(encoding="utf-8"))
    pausa = timeline["pausa"]
    silencio = b"\x00" * int(TAXA * pausa) * 2 * CANAIS

    partes = []
    for cena in timeline["cenas"]:
        mp3 = AUDIO / (cena["nome"] + ".mp3")
        wav = TMP / (cena["nome"] + ".wav")
        decodificar(mp3, wav)
        partes.append(ler_pcm(wav))
        partes.append(silencio)

    saida = RAIZ / "narracao.wav"
    with wave.open(str(saida), "wb") as w:
        w.setnchannels(CANAIS)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes(b"".join(partes))

    duracao = saida.stat().st_size / (TAXA * 2 * CANAIS)
    print("narracao.wav:", round(duracao, 2), "s", round(saida.stat().st_size / 1e6, 1), "MB")


if __name__ == "__main__":
    main()
