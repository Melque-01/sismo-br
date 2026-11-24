"""Login, cadastro e logout."""

import re
import time
from typing import Dict, Mapping

import config
from controles import respostas
from modelo import usuario as usuario_modelo
from servicos import limites, senhas, sessoes

# Proteção simples contra força bruta: 5 falhas por IP em 5 minutos.
LIMITE_FALHAS = 5
JANELA_SEGUNDOS = 300
_FALHAS: Dict[str, list] = {}

# Segunda barreira por conta: 10 falhas por e-mail em 15 minutos, somando
# IPs diferentes (evita trocar de IP para continuar tentando).
LIMITE_CONTA = 10
JANELA_CONTA_SEGUNDOS = 900
_FALHAS_CONTA: Dict[str, list] = {}

# Teto dos dicionários em memória (chaves vêm do cliente: IP e e-mail).
LIMITE_CHAVES = 5000

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


def _registrar_falha(ip: str, email: str) -> None:
    agora = time.time()
    _FALHAS.setdefault(ip, []).append(agora)
    _podar(_FALHAS)
    limites.registrar("falha_ip", ip)
    chave = usuario_modelo.normalizar_email(email)
    if chave:
        _FALHAS_CONTA.setdefault(chave, []).append(agora)
        _podar(_FALHAS_CONTA)
        limites.registrar("falha_conta", chave)


def _podar(registro: Dict[str, list]) -> None:
    """Descarta as chaves mais antigas quando o dicionário passa do teto."""
    excedente = len(registro) - LIMITE_CHAVES
    if excedente <= 0:
        return
    for chave in list(registro)[:excedente]:
        registro.pop(chave, None)


def conta_bloqueada(email: str) -> bool:
    chave = usuario_modelo.normalizar_email(email)
    if not chave:
        return False
    no_banco = limites.contar("falha_conta", chave, JANELA_CONTA_SEGUNDOS)
    if no_banco is not None:
        return no_banco >= LIMITE_CONTA
    return (
        len(_recentes(_FALHAS_CONTA, chave, JANELA_CONTA_SEGUNDOS))
        >= LIMITE_CONTA
    )


def _limpar_falhas_conta(email: str) -> None:
    chave = usuario_modelo.normalizar_email(email)
    _FALHAS_CONTA.pop(chave, None)
    limites.limpar("falha_conta", chave)


def bloqueado(ip: str) -> bool:
    no_banco = limites.contar("falha_ip", ip, JANELA_SEGUNDOS)
    if no_banco is not None:
        return no_banco >= LIMITE_FALHAS
    return len(_recentes(_FALHAS, ip, JANELA_SEGUNDOS)) >= LIMITE_FALHAS


def _cadastro_bloqueado(ip: str) -> bool:
    no_banco = limites.contar("cadastro", ip, JANELA_CADASTRO)
    if no_banco is not None:
        return no_banco >= LIMITE_CADASTROS
    return len(_recentes(_CADASTROS, ip, JANELA_CADASTRO)) >= LIMITE_CADASTROS


def _registrar_cadastro(ip: str) -> None:
    _CADASTROS.setdefault(ip, []).append(time.time())
    limites.registrar("cadastro", ip)


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


def _cookie_csrf(token: str, dados: Mapping[str, object]) -> str:
    seguro = "; Secure" if dados.get("_proto") == "https" else ""
    return (
        "{}={}; Path=/; HttpOnly; SameSite=Lax; Max-Age={}{}".format(
            sessoes.NOME_COOKIE_CSRF, token, int(config.SESSAO_TTL), seguro
        )
    )


def com_csrf(dados, resposta):
    """Garante o cookie CSRF e injeta o token nos formulários renderizados."""
    status, cabecalhos, corpo = resposta
    token = sessoes.token_csrf(dados.get("_cookies") or {})
    if token is None:
        token = sessoes.criar_token_csrf()
        cabecalhos["set-cookie"] = _cookie_csrf(token, dados)
    if b"{{csrf}}" in corpo:
        corpo = corpo.replace(b"{{csrf}}", token.encode("ascii"))
    return status, cabecalhos, corpo


def _csrf_invalido(dados) -> bool:
    return not sessoes.csrf_valido(
        dados.get("_cookies") or {}, dados.get("_csrf") or ""
    )


def _formulario(dados, template, **variaveis):
    """Renderiza formulário já protegido pelo token CSRF."""
    return com_csrf(dados, respostas.render(template, **variaveis))


def _erro_csrf(dados, template="login.html"):
    return _formulario(
        dados,
        template,
        erro="Sessão expirada. Recarregue a página e tente de novo.",
        email="",
        status=403,
    )


def esta_autenticado(dados: Mapping[str, object]) -> bool:
    cookies = dados.get("_cookies") or {}
    return bool(sessoes.validar_token(cookies.get(sessoes.NOME_COOKIE)))


def _entrar(dados, email: str):
    token = sessoes.criar_token(email)
    status, cabecalhos, corpo = respostas.redirecionar("/")
    cabecalhos["set-cookie"] = _cookie(token, dados, config.SESSAO_TTL)
    return status, cabecalhos, corpo


def _erro_banco(dados):
    return _formulario(
        dados,
        "login.html",
        erro="Sistema indisponível no momento. Tente novamente em instantes.",
        email="",
        status=503,
    )


def login_form(dados):
    """GET /login - mostra o formulário (ou volta para o mapa se já entrou)."""
    if esta_autenticado(dados):
        return respostas.redirecionar("/")
    return _formulario(dados, "login.html", erro="", email="")


def login(dados):
    """POST /login - valida e grava o cookie de sessão."""
    if _csrf_invalido(dados):
        return _erro_csrf(dados)

    ip = _ip(dados)
    if bloqueado(ip):
        return _formulario(
            dados,
            "login.html",
            erro="Muitas tentativas. Aguarde alguns minutos e tente de novo.",
            email="",
            status=429,
        )

    email = str(dados.get("email") or "").strip()
    senha = str(dados.get("senha") or "")

    if conta_bloqueada(email):
        return _formulario(
            dados,
            "login.html",
            erro="Muitas tentativas para esta conta. Aguarde e tente de novo.",
            email="",
            status=429,
        )

    try:
        valido = autenticar(email, senha)
    except Exception:  # noqa: BLE001 - banco fora do ar
        return _erro_banco(dados)

    if not valido:
        _registrar_falha(ip, email)
        return _formulario(
            dados,
            "login.html",
            erro="E-mail ou senha inválidos.",
            email=email,
            status=401,
        )

    _limpar_falhas_conta(email)
    return _entrar(dados, email)


def registrar_form(dados):
    """GET /registrar - formulário de criação de conta."""
    if esta_autenticado(dados):
        return respostas.redirecionar("/")
    return _formulario(dados, "registrar.html", erro="", email="")


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
    if _csrf_invalido(dados):
        return _erro_csrf(dados, "registrar.html")

    ip = _ip(dados)
    if _cadastro_bloqueado(ip):
        return _formulario(
            dados,
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
        return _formulario(
            dados, "registrar.html", erro=erro, email=email, status=400
        )

    try:
        if usuario_modelo.buscar_por_email(email):
            _registrar_cadastro(ip)
            return _formulario(
                dados,
                "registrar.html",
                erro="Este e-mail já está cadastrado.",
                email=email,
                status=409,
            )
        usuario_id = usuario_modelo.criar(email, senhas.hash_senha(senha))
    except Exception:  # noqa: BLE001 - banco fora do ar
        return _erro_banco(dados)

    if usuario_id is None:
        return _formulario(
            dados,
            "registrar.html",
            erro="Este e-mail já está cadastrado.",
            email=email,
            status=409,
        )

    _registrar_cadastro(ip)
    return _entrar(dados, email)


def logout(dados):
    """POST /logout - apaga o cookie e volta para o login."""
    if _csrf_invalido(dados):
        return respostas.redirecionar("/")
    status, cabecalhos, corpo = respostas.redirecionar("/login")
    cabecalhos["set-cookie"] = _cookie("", dados, 0)
    return status, cabecalhos, corpo
