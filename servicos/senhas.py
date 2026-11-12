"""Hash e verificação de senhas com PBKDF2-HMAC-SHA256 (stdlib)."""

import hashlib
import hmac
import secrets

ITERACOES = 260_000
ALGORITMO = "pbkdf2_sha256"
TAMANHO_MAXIMO = 256


def hash_senha(senha: str) -> str:
    """Gera `algoritmo$iteracoes$salt_hex$hash_hex` com salt aleatório."""
    if not senha:
        raise ValueError("senha vazia")
    salt = secrets.token_bytes(16)
    derivado = hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), salt, ITERACOES
    )
    return "{}${}${}${}".format(ALGORITMO, ITERACOES, salt.hex(), derivado.hex())


def verificar_senha(senha: str, armazenado: str) -> bool:
    """Confere a senha em tempo constante; hash inválido nunca autentica."""
    if not senha or not armazenado or len(senha) > TAMANHO_MAXIMO:
        return False
    partes = armazenado.split("$")
    if len(partes) != 4 or partes[0] != ALGORITMO:
        return False
    try:
        iteracoes = int(partes[1])
        salt = bytes.fromhex(partes[2])
        esperado = partes[3]
        derivado = hashlib.pbkdf2_hmac(
            "sha256", senha.encode("utf-8"), salt, iteracoes
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derivado.hex(), esperado)
