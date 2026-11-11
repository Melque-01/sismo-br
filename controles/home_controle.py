"""Controller da página inicial."""

from controles.respostas import render


def index(dados):
    """GET / - renderiza o mapa de densidade."""
    return render(
        "index.html",
        titulo="Sismos BR - densidade de epicentros",
    )
