"""Controller da página inicial."""

from controles import auth_controle
from controles.respostas import render


def index(dados):
    """GET / - renderiza o mapa de densidade para o usuário autenticado."""
    return auth_controle.com_csrf(
        dados,
        render(
            "index.html",
            titulo="Sismos BR - densidade de epicentros",
            usuario=dados.get("_email") or "",
        ),
    )


def saiba_mais(dados):
    """GET /saiba-mais - apresentação pública do projeto e vídeo explicativo."""
    return render(
        "saiba-mais.html",
        titulo="Sismos BR - saiba mais sobre o projeto",
    )
