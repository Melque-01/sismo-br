"""Sessões assinadas em cookie (sem banco e sem dependência externa).

O token é `base64url(payload).base64url(hmac_sha256)`. O payload só carrega o
e-mail e a expiração: nada sensível, e qualquer alteração invalida a assinatura.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional

import config

NOME_COOKIE = "sismos_sessao"
NOME_COOKIE_CSRF = "sismos_csrf"
_SEGREDO_ALEATORIO = None
_SEGREDO_DO_BANCO = None


def _segredo_do_banco():
    """Carrega (ou cria) o segredo na tabela `segredos` do banco.

    Sem SESSION_SECRET no .env, guardar o segredo no banco mantém os cookies
    válidos entre reinícios. Falha (banco fora) devolve None e o chamador
    cai para o segredo aleatório de boot.
    """
    global _SEGREDO_DO_BANCO
    if _SEGREDO_DO_BANCO is not None:
        return _SEGREDO_DO_BANCO
    try:
        from db import database

        linha = database.consultar_um(
            "SELECT valor FROM segredos WHERE chave = 'sessao'"
        )
        if not (linha and linha.get("valor")):
            valor = secrets.token_hex(32)
            database.executar(
                """
                INSERT INTO segredos (chave, valor) VALUES ('sessao', %s)
                ON CONFLICT (chave) DO NOTHING
                """,
                (valor,),
            )
            # Outra thread pode ter vencido o INSERT: reler o valor do banco
            # garante que o processo usa exatamente o que está gravado.
            linha = database.consultar_um(
                "SELECT valor FROM segredos WHERE chave = 'sessao'"
            )
            if not (linha and linha.get("valor")):
                return None
        _SEGREDO_DO_BANCO = str(linha["valor"]).encode("utf-8")
        return _SEGREDO_DO_BANCO
    except Exception:  # noqa: BLE001 - sem banco, segue o segredo de boot
        return None


def _segredo() -> bytes:
    """Segredo de assinatura: .env → banco → aleatório por boot."""
    if config.SEGREDO_SESSAO:
        return config.SEGREDO_SESSAO.encode("utf-8")
    do_banco = _segredo_do_banco()
    if do_banco:
        return do_banco
    global _SEGREDO_ALEATORIO
    if _SEGREDO_ALEATORIO is None:
        _SEGREDO_ALEATORIO = secrets.token_hex(32)
    return _SEGREDO_ALEATORIO.encode("utf-8")


def _b64(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode("ascii")


def _de_b64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _assinar(payload: bytes) -> str:
    return _b64(hmac.new(_segredo(), payload, hashlib.sha256).digest())


def criar_token(email: str, ttl: Optional[int] = None) -> str:
    """Cria um token assinado para o e-mail, com validade em segundos."""
    validade = config.SESSAO_TTL if ttl is None else ttl
    payload = json.dumps(
        {"sub": email.strip().lower(), "exp": int(time.time()) + int(validade)},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "{}.{}".format(_b64(payload), _assinar(payload))


def validar_token(token: Optional[str]) -> Optional[str]:
    """Devolve o e-mail se o token for válido e não tiver expirado."""
    if not token or "." not in token:
        return None
    parte_payload, parte_assinatura = token.rsplit(".", 1)
    try:
        payload = _de_b64(parte_payload)
    except (ValueError, TypeError):
        return None
    if not hmac.compare_digest(_assinar(payload), parte_assinatura):
        return None
    try:
        dados = json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(dados, dict):
        return None
    if int(dados.get("exp", 0)) < int(time.time()):
        return None
    email = dados.get("sub")
    return email if isinstance(email, str) and email else None


def criar_token_csrf() -> str:
    """Token aleatório para o duplo envio (cookie + campo do formulário)."""
    return secrets.token_urlsafe(32)


def token_csrf(cookies) -> Optional[str]:
    """Token CSRF já presente no cookie, se tiver tamanho plausível."""
    token = (cookies or {}).get(NOME_COOKIE_CSRF)
    if not isinstance(token, str) or len(token) < 20:
        return None
    return token


def csrf_valido(cookies, enviado) -> bool:
    """Compara o campo do formulário com o token do cookie."""
    esperado = token_csrf(cookies)
    if not esperado or not enviado:
        return False
    return hmac.compare_digest(esperado, str(enviado))
