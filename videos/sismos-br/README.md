# Vídeo explicativo — Sismos BR

Vídeo de 2min15 explicando o sistema de ponta a ponta, com narração em pt-BR.

- **Arquivo final:** `sismos-br-explicativo.mp4` (1920×1080, 30 fps, ~13 MB)
- **Voz:** `pt-BR-FranciscaNeural` (edge-tts, ritmo −4%)
- **Trilha:** pad sintetizado no próprio HTML (volume baixo sob a narração)
- **Cenas:** 10, com tempos em `timeline.json`

## Cenas

| # | Cena | Conteúdo |
|---|---|---|
| 1 | intro | nome, subtítulo, proposta |
| 2 | dados | SISBRA 5.044 + FDSN 97 = 5.141 eventos |
| 3 | postgis | catálogos → parser → PostGIS, malha do IBGE |
| 4 | mapa | grade de densidade, legenda e métrica |
| 5 | filtros | filtros reais + tabela de eventos da célula |
| 6 | painel | série anual, histograma e números |
| 7 | login | telas de login e cadastro, PBKDF2/cookie |
| 8 | arquitetura | navegador → controllers → models → PostGIS |
| 9 | cloudflare | túnel de saída, sem abrir portas |
| 10 | fechamento | nome e URL |

## Regerar

Pré-requisitos: Node 18+, ffmpeg, Python 3.10+, `pip install edge-tts`, `npm install playwright`.

```bash
cd videos/sismos-br

# 1. narração (gera audio/*.mp3 e timeline.json)
python make_narration.py

# 2. junta a narração em WAV
python make_narracao_wav.py

# 3. injeta fontes/imagens/tempos no HTML
python build_video.py

# 4. rascunho rápido (30 fps, sem motion blur)
node render.mjs video.html draft.mp4 30 1 4

# 5. final (30 fps, 2 subframes de motion blur)
node render.mjs video.html final.mp4 30 2 4

# 6. mixa narração sobre a trilha e normaliza
ffmpeg -y -i final.mp4 -i narracao.wav \
  -filter_complex "[0:a]volume=0.22[bg];[1:a]volume=1.0[voice];[bg][voice]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95,loudnorm=I=-16:TP=-1.5:LRA=11[mix]" \
  -map 0:v -map "[mix]" -c:v copy -c:a aac -b:a 192k sismos-br-explicativo.mp4
```

Para mudar o texto: edite `CENAS` em `make_narration.py` e repita os passos. Para mudar a voz, troque `VOZ` (ex.: `pt-BR-AntonioNeural`).

## Estrutura

```
make_narration.py      texto + TTS + timeline
make_narracao_wav.py   concatena os MP3 em WAV
template.html          cenas, animação seek(t), trilha sintetizada
build_video.py         injeta fontes, imagens e timeline
render.mjs             Playwright + ffmpeg (do skill explainer-default)
assets/                capturas da interface em JPEG
audio/                 narração por cena (MP3)
```

`video.html` gerado pode ser aberto no navegador para revisar as cenas (o play toca só a trilha; a narração está no MP4).
