"""Acesso ao PostgreSQL/PostGIS.

Um pool de conexões (`psycopg_pool`) é criado na primeira chamada e reusado
pelo `ThreadingHTTPServer` — evita abrir/fechar uma conexão por request.
O pool se recompõe sozinho se o banco reiniciar.

Quando o banco está fora do ar, uma janela de 30 s faz as chamadas falharem
na hora (sem esperar `connect_timeout` em cada request, o que trava filas).

SQL sempre parametrizado (`%s`).
"""

import contextlib
import os
import threading
import time

import psycopg
from psycopg.rows import dict_row

from config import BANCO

CAMINHO_SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

_trava = threading.Lock()
_pool = None

# Banco com falha recente: as próximas chamadas falham na hora durante esta
# janela, sem esperar o connect_timeout em cada request (fila não trava).
JANELA_FORA_AR = 30.0
_fora_do_ar_ate = 0.0


def _obter_pool():
    """Cria o pool uma única vez (thread-safe)."""
    global _pool
    with _trava:
        if _pool is None:
            try:
                from psycopg_pool import ConnectionPool

                _pool = ConnectionPool(
                    conninfo="",
                    kwargs={**BANCO, "row_factory": dict_row},
                    min_size=0,  # sem conexões de fundo tentando quando o banco está fora
                    max_size=4,
                    timeout=BANCO.get("connect_timeout", 5),
                    open=True,
                )
            except ImportError:
                _pool = False  # psycopg-pool ausente: cai para conexão avulsa
    return _pool


def conectar():
    """Abre uma conexão avulsa (uso de scripts fora do ciclo de request)."""
    return psycopg.connect(**BANCO, row_factory=dict_row)


@contextlib.contextmanager
def _conexao():
    """Conexão do pool, com fail-fast após falha recente do banco."""
    global _fora_do_ar_ate
    agora = time.monotonic()
    if agora < _fora_do_ar_ate:
        raise psycopg.OperationalError(
            "banco recentemente indisponível (tentando de novo em instantes)"
        )
    pool = _obter_pool()
    if pool is False:
        try:
            conexao = psycopg.connect(**BANCO, row_factory=dict_row)
        except Exception:
            _fora_do_ar_ate = agora + JANELA_FORA_AR
            raise
        try:
            yield conexao
        finally:
            conexao.close()
        return
    try:
        conexao = pool.getconn(timeout=BANCO.get("connect_timeout", 5))
    except Exception:
        _fora_do_ar_ate = agora + JANELA_FORA_AR
        raise
    quebrou = False
    try:
        yield conexao
    except psycopg.OperationalError:
        # Banco caiu com a conexão em uso: arma a janela e descarta a conexão.
        _fora_do_ar_ate = time.monotonic() + JANELA_FORA_AR
        quebrou = True
        raise
    finally:
        pool.putconn(conexao, close=quebrou)


def consultar(sql, parametros=()):
    """Executa um SELECT e devolve uma lista de dicionários."""
    with _conexao() as conexao, conexao.cursor() as cursor:
        cursor.execute(sql, parametros)
        return cursor.fetchall()


def consultar_um(sql, parametros=()):
    """Executa um SELECT e devolve o primeiro registro (ou None)."""
    with _conexao() as conexao, conexao.cursor() as cursor:
        cursor.execute(sql, parametros)
        return cursor.fetchone()


def executar(sql, parametros=()):
    """Executa INSERT/UPDATE/DELETE e devolve o número de linhas afetadas."""
    with _conexao() as conexao, conexao.cursor() as cursor:
        cursor.execute(sql, parametros)
        conexao.commit()
        return cursor.rowcount


def executar_lote(sql, lista_parametros):
    """Executa a mesma instrução para várias linhas e devolve o total."""
    with _conexao() as conexao, conexao.cursor() as cursor:
        cursor.executemany(sql, lista_parametros)
        total = cursor.rowcount
        conexao.commit()
        return total


def inserir(sql, parametros=()):
    """Executa um INSERT ... RETURNING id e devolve o id gerado."""
    with _conexao() as conexao, conexao.cursor() as cursor:
        cursor.execute(sql, parametros)
        linha = cursor.fetchone()
        conexao.commit()
        return linha["id"] if linha else None


def disponivel():
    """Verifica se o banco responde (healthcheck / mensagens de erro)."""
    try:
        consultar_um("SELECT 1 AS ok")
        return True
    except Exception:  # noqa: BLE001 - qualquer falha = indisponível
        return False


def _comandos(script):
    """Divide o schema em comandos, ignorando comentários de linha.

    O `--` pode conter ponto e vírgula; sem remover o comentário antes de
    dividir, o comando sairia cortado no meio.
    """
    linhas = []
    for linha in script.splitlines():
        corte = linha.find("--")
        if corte >= 0:
            linha = linha[:corte]
        linhas.append(linha)
    return [comando.strip() for comando in "\n".join(linhas).split(";") if comando.strip()]


def criar_tabelas():
    """Aplica `db/schema.sql` (idempotente)."""
    with open(CAMINHO_SCHEMA, encoding="utf-8") as arquivo:
        script = arquivo.read()

    comandos = _comandos(script)
    with _conexao() as conexao, conexao.cursor() as cursor:
        for comando in comandos:
            cursor.execute(comando)
        conexao.commit()
