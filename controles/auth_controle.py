"""Login e logout (usuário único configurado por variáveis de ambiente)."""

import hmac
import time
from typing import Dict, Mapping

import config
from controles import respostas
from servicos import sessoes

# Proteção simples contra força bruta: 5 falhas por IP em 5 minutos.
LIMITE_FALHAS = 5
JANELA_SEGUNDOS = 300
_FALHAS: Dict[str, list] = {}


def _ip(dados: Mapping[str, object]) -> str:
    return str(dados.get("_ip") or "desconhecido")


def _falhas_recentes(ip: str) -> list:
    agora = time.time()
    recentes = [t for t in _FALHAS.get(ip, []) if agora - t < JANELA_SEGUNDOS]
    if recentes:
        _FALHAS[ip] = recentes
    else:
        _FALHAS.pop(ip, None)
    return recentes


def _registrar_falha(ip: str) -> None:
    _FALHAS.setdefault(ip, []).append(time.time())


def bloqueado(ip: str) -> bool:
    return len(_falhas_recentes(ip)) >= LIMITE_FALHAS


def credenciais_validas(email: str, senha: str) -> bool:
    """Compara com as credenciais do .env em tempo constante."""
    if not config.LOGIN_EMAIL or not config.LOGIN_SENHA:
        return False
    email_ok = hmac.compare_digest(
        email.strip().lower().encode("utf-8"),
        config.LOGIN_EMAIL.strip().lower().encode("utf-8"),
    )
    senha_ok = hmac.compare_digest(
        senha.encode("utf-8"), config.LOGIN_SENHA.encode("utf-8")
    )
    return email_ok and senha_ok


def _cookie(token: str, dados: Mapping[str, object], max_age: int) -> str:
    seguro = "; Secure" if dados.get("_proto") == "https" else ""
    return (
        "{}={}; Path=/; HttpOnly; SameSite=Lax; Max-Age={}{}".format(
            sessoes.NOME_COOKIE, token, int(max_age), seguro
        )
    )


def esta_autenticado(dados: Mapping[str, object]) -> bool:
    cookies = dados.get("_cookies") or {}
    return bool(sessoes.validar_token(cookies.get(sessoes.NOME_COOKIE)))


def login_form(dados):
    """GET /login - mostra o formulário (ou volta para o mapa se já entrou)."""
    if esta_autenticado(dados):
        return respostas.redirecionar("/")
    return respostas.render("login.html", erro="", email="")


def login(dados):
    """POST /login - valida e grava o cookie de sessão."""
    ip = _ip(dados)
    if bloqueado(ip):
        return respostas.render(
            "login.html",
            erro="Muitas tentativas. Aguarde alguns minutos e tente de novo.",
            email="",
            status=429,
        )

    email = str(dados.get("email") or "").strip()
    senha = str(dados.get("senha") or "")

    if not credenciais_validas(email, senha):
        _registrar_falha(ip)
        return respostas.render(
            "login.html",
            erro="E-mail ou senha inválidos.",
            email=email,
            status=401,
        )

    token = sessoes.criar_token(email)
    status, cabecalhos, corpo = respostas.redirecionar("/")
    cabecalhos["set-cookie"] = _cookie(token, dados, config.SESSAO_TTL)
    return status, cabecalhos, corpo


def logout(dados):
    """POST /logout - apaga o cookie e volta para o login."""
    status, cabecalhos, corpo = respostas.redirecionar("/login")
    cabecalhos["set-cookie"] = _cookie("", dados, 0)
    return status, cabecalhos, corpo
