"""Persistência das janelas de rate limit (tabela `limites`).

O dicionário em memória do `auth_controle` continua como primeiro nível
(latência zero), e o banco torna a proteção sobrevivente a reinícios.
Toda função falha aberta (devolve None / ignora erro): rate limit é barreira
extra — indisponibilidade de banco não pode derrubar o login, que já
responde 503 quando precisa do banco de verdade.
"""

from db import database


def registrar(tipo: str, chave: str) -> None:
    """Anota uma ocorrência (falha de login, cadastro) no banco."""
    try:
        database.executar(
            "INSERT INTO limites (tipo, chave) VALUES (%s, %s)", (tipo, chave)
        )
    except Exception:  # noqa: BLE001 - banco fora: memória cobre
        pass


def contar(tipo: str, chave: str, janela_segundos: int):
    """Ocorrências de `chave` em `janela_segundos`; None se banco indisponível."""
    try:
        linha = database.consultar_um(
            """
            SELECT count(*) AS n
            FROM limites
            WHERE tipo = %s AND chave = %s
              AND criado_em > now() - (%s * interval '1 second')
            """,
            (tipo, chave, janela_segundos),
        )
        return int(linha["n"]) if linha else 0
    except Exception:  # noqa: BLE001 - cai para a contagem em memória
        return None


def limpar(tipo: str, chave: str) -> None:
    """Zera a janela de uma chave (login bem-sucedido)."""
    try:
        database.executar(
            "DELETE FROM limites WHERE tipo = %s AND chave = %s", (tipo, chave)
        )
    except Exception:  # noqa: BLE001 - banco fora: memória cobre
        pass


def podar(dias: int = 2) -> None:
    """Remove registros vencidos (chamado pelo importador, não por request)."""
    try:
        database.executar(
            "DELETE FROM limites WHERE criado_em < now() - (%s * interval '1 day')",
            (dias,),
        )
    except Exception:  # noqa: BLE001 - podar é manutenção, não proteção
        pass
