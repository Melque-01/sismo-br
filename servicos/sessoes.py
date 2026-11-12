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
_SEGREDO_ALEATORIO = None


def _segredo() -> bytes:
    """Segredo de assinatura; usa um aleatório por boot se não configurado."""
    global _SEGREDO_ALEATORIO
    if config.SEGREDO_SESSAO:
        return config.SEGREDO_SESSAO.encode("utf-8")
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
