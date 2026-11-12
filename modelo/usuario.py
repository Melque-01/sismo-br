"""Contas de acesso ao site (tabela `usuarios`)."""

from typing import Dict, Optional

from db import database
from servicos.senhas import hash_senha

BUSCAR = "SELECT id, email, senha_hash, criado_em FROM usuarios WHERE email = %s"

CRIAR = """
INSERT INTO usuarios (email, senha_hash)
VALUES (%s, %s)
ON CONFLICT (email) DO NOTHING
RETURNING id
"""


def normalizar_email(email: str) -> str:
    return (email or "").strip().lower()


def buscar_por_email(email: str) -> Optional[Dict[str, object]]:
    """Registro do usuário (inclui o hash) ou None."""
    return database.consultar_um(BUSCAR, (normalizar_email(email),))


def criar(email: str, senha_hash: str) -> Optional[int]:
    """Cria a conta; devolve None se o e-mail já existir."""
    return database.inserir(CRIAR, (normalizar_email(email), senha_hash))


def garantir_admin_inicial(email: str, senha: str) -> bool:
    """Cria o primeiro usuário a partir do .env quando a tabela está vazia."""
    if not email or not senha:
        return False
    total = database.consultar_um("SELECT count(*) AS n FROM usuarios")
    if int(total["n"] or 0) > 0:
        return False
    return criar(email, hash_senha(senha)) is not None


def total() -> int:
    linha = database.consultar_um("SELECT count(*) AS n FROM usuarios")
    return int(linha["n"] or 0)
