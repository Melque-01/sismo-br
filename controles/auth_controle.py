"""Login, cadastro e logout."""

import re
import time
from typing import Dict, Mapping

import config
from controles import respostas
from modelo import usuario as usuario_modelo
from servicos import senhas, sessoes

# Proteção simples contra força bruta: 5 falhas por IP em 5 minutos.
LIMITE_FALHAS = 5
JANELA_SEGUNDOS = 300
_FALHAS: Dict[str, list] = {}

# Cadastro: no máximo 10 tentativas por IP por hora.
LIMITE_CADASTROS = 10
JANELA_CADASTRO = 3600
_CADASTROS: Dict[str, list] = {}

EMAIL_VALIDO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SENHA_MINIMA = 8


def _ip(dados: Mapping[str, object]) -> str:
    return str(dados.get("_ip") or "desconhecido")


def _recentes(registro: Dict[str, list], ip: str, janela: int) -> list:
    agora = time.time()
    itens = [t for t in registro.get(ip, []) if agora - t < janela]
    if itens:
        registro[ip] = itens
    else:
        registro.pop(ip, None)
    return itens


def _registrar_falha(ip: str) -> None:
    _FALHAS.setdefault(ip, []).append(time.time())


def bloqueado(ip: str) -> bool:
    return len(_recentes(_FALHAS, ip, JANELA_SEGUNDOS)) >= LIMITE_FALHAS


def _cadastro_bloqueado(ip: str) -> bool:
    return len(_recentes(_CADASTROS, ip, JANELA_CADASTRO)) >= LIMITE_CADASTROS


def _registrar_cadastro(ip: str) -> None:
    _CADASTROS.setdefault(ip, []).append(time.time())


def autenticar(email: str, senha: str) -> bool:
    """Confere e-mail/senha contra a tabela de usuários."""
    registro = usuario_modelo.buscar_por_email(email)
    if not registro:
        return False
    return senhas.verificar_senha(senha, str(registro["senha_hash"]))


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


def _entrar(dados, email: str):
    token = sessoes.criar_token(email)
    status, cabecalhos, corpo = respostas.redirecionar("/")
    cabecalhos["set-cookie"] = _cookie(token, dados, config.SESSAO_TTL)
    return status, cabecalhos, corpo


def _erro_banco():
    return respostas.render(
        "login.html",
        erro="Sistema indisponível no momento. Tente novamente em instantes.",
        email="",
        status=503,
    )


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

    try:
        valido = autenticar(email, senha)
    except Exception:  # noqa: BLE001 - banco fora do ar
        return _erro_banco()

    if not valido:
        _registrar_falha(ip)
        return respostas.render(
            "login.html",
            erro="E-mail ou senha inválidos.",
            email=email,
            status=401,
        )

    return _entrar(dados, email)


def registrar_form(dados):
    """GET /registrar - formulário de criação de conta."""
    if esta_autenticado(dados):
        return respostas.redirecionar("/")
    return respostas.render("registrar.html", erro="", email="")


def _validar_cadastro(email: str, senha: str, confirmacao: str) -> str:
    if not EMAIL_VALIDO.match(email):
        return "Informe um e-mail válido."
    if len(senha) < SENHA_MINIMA:
        return "A senha precisa ter pelo menos {} caracteres.".format(SENHA_MINIMA)
    if senha != confirmacao:
        return "As senhas não conferem."
    return ""


def registrar(dados):
    """POST /registrar - cria a conta e já entra no sistema."""
    ip = _ip(dados)
    if _cadastro_bloqueado(ip):
        return respostas.render(
            "registrar.html",
            erro="Muitos cadastros deste endereço. Tente mais tarde.",
            email="",
            status=429,
        )

    email = usuario_modelo.normalizar_email(str(dados.get("email") or ""))
    senha = str(dados.get("senha") or "")
    confirmacao = str(dados.get("confirmar") or "")

    erro = _validar_cadastro(email, senha, confirmacao)
    if erro:
        _registrar_cadastro(ip)
        return respostas.render(
            "registrar.html", erro=erro, email=email, status=400
        )

    try:
        if usuario_modelo.buscar_por_email(email):
            _registrar_cadastro(ip)
            return respostas.render(
                "registrar.html",
                erro="Este e-mail já está cadastrado.",
                email=email,
                status=409,
            )
        usuario_id = usuario_modelo.criar(email, senhas.hash_senha(senha))
    except Exception:  # noqa: BLE001 - banco fora do ar
        return _erro_banco()

    if usuario_id is None:
        return respostas.render(
            "registrar.html",
            erro="Este e-mail já está cadastrado.",
            email=email,
            status=409,
        )

    _registrar_cadastro(ip)
    return _entrar(dados, email)


def logout(dados):
    """POST /logout - apaga o cookie e volta para o login."""
    status, cabecalhos, corpo = respostas.redirecionar("/login")
    cabecalhos["set-cookie"] = _cookie("", dados, 0)
    return status, cabecalhos, corpo
