"""Registro das execuções do importador (tabela `importacoes`)."""

from db import database

INICIAR = """
INSERT INTO importacoes (fonte, arquivo)
VALUES (%s, %s)
RETURNING id
"""

CONCLUIR = """
UPDATE importacoes
SET linhas_lidas = %s,
    linhas_importadas = %s,
    linhas_descartadas = %s,
    concluido_em = now(),
    erro = %s
WHERE id = %s
"""


def iniciar(fonte: str, arquivo: str) -> int:
    """Abre um registro de importação e devolve o id."""
    return database.inserir(INICIAR, (fonte, arquivo))


def concluir(
    importacao_id: int,
    lidas: int,
    importadas: int,
    descartadas: int,
    erro: str = None,
) -> None:
    """Fecha o registro com as contagens da execução."""
    database.executar(
        CONCLUIR, (lidas, importadas, descartadas, erro, importacao_id)
    )
