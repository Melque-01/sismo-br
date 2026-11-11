"""Importa os catálogos SISBRA e FDSN para o PostGIS.

Uso:
    python scripts/importar_catalogo.py                # as duas fontes
    python scripts/importar_catalogo.py --somente fdsn # só a atualização recente
    python scripts/importar_catalogo.py --sem-baixar   # usa dados/brutos

O script é idempotente: o upsert por (fonte, evento_id) atualiza o que já
existe, e eventos fora do território brasileiro são removidos depois da carga.
"""

import argparse
import os
import sys
import urllib.parse
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import config  # noqa: E402
from db import database  # noqa: E402
from modelo import importacao  # noqa: E402
from modelo import sismo as modelo_sismo  # noqa: E402
from servicos.catalogo import ler_fdsn, ler_sisbra  # noqa: E402

ARQUIVO_SISBRA = os.path.join(str(config.PASTA_BRUTOS), "catalogo_RAW.dat")
ARQUIVO_FDSN = os.path.join(str(config.PASTA_BRUTOS), "fdsn_br.txt")

TEMPO_LIMITE = 180

# Remove eventos que caíram no recorte, mas fora da malha do IBGE (Chile,
# Argentina, oceano etc.). Roda depois de cada carga, sempre pela fonte.
REMOVER_FORA_DO_BRASIL = """
DELETE FROM sismos s
WHERE s.fonte = %s
  AND NOT EXISTS (
      SELECT 1 FROM estados e WHERE ST_Contains(e.geom, s.geom)
  )
"""


def baixar(url, destino):
    """Baixa `url` para `destino` (criando a pasta) e devolve o caminho."""
    pasta = os.path.dirname(destino)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    requisicao = urllib.request.Request(
        url, headers={"User-Agent": "sismos-br/1.0 (trabalho academico)"}
    )
    with urllib.request.urlopen(requisicao, timeout=TEMPO_LIMITE) as resposta:
        conteudo = resposta.read()
    with open(destino, "wb") as arquivo:
        arquivo.write(conteudo)
    return destino


def url_fdsn():
    """URL do serviço FDSN com o recorte do Brasil e a data de corte."""
    parametros = {
        "format": "text",
        "starttime": config.FDSN_DESDE,
        "eventtype": "earthquake",
        "orderby": "time",
        "limit": 20000,
    }
    parametros.update(config.FDSN_BBOX)
    return config.URL_FDSN + "?" + urllib.parse.urlencode(parametros)


def filtrar_sisbra(eventos, ufs):
    """Mantém só eventos com UF brasileira; devolve (aceitos, descartados)."""
    aceitos = [evento for evento in eventos if evento.get("uf") in ufs]
    return aceitos, len(eventos) - len(aceitos)


def filtrar_fdsn(eventos):
    """Mantém todos os eventos do FDSN; o filtro geográfico é feito no banco."""
    return list(eventos), 0


def _garantir_estrutura():
    """Aplica o schema e carrega a malha das UFs quando ainda não existe."""
    database.criar_tabelas()
    estados = database.consultar_um("SELECT count(*) AS n FROM estados")
    if int(estados["n"] or 0) < 27:
        modelo_sismo.carregar_estados(str(config.ARQUIVO_ESTADOS))


def _registrar(fonte, arquivo, lidas, importadas, descartadas, erro=None):
    """Grava a execução na tabela `importacoes`."""
    importacao_id = importacao.iniciar(fonte, arquivo)
    importacao.concluir(
        importacao_id, lidas, importadas, descartadas, erro=erro
    )


def importar_sisbra(caminho=None, baixar_de_novo=True):
    """Lê, filtra e grava o catálogo SISBRA. Devolve o resumo."""
    caminho = caminho or ARQUIVO_SISBRA
    if baixar_de_novo or not os.path.isfile(caminho):
        baixar(config.URL_SISBRA, caminho)

    with open(caminho, encoding="utf-8", errors="replace") as arquivo:
        texto = arquivo.read()

    lidos = [
        linha
        for linha in texto.splitlines()
        if linha.strip() and not linha.lstrip().startswith("#")
    ]
    eventos = ler_sisbra(texto)
    aceitos, descartados_uf = filtrar_sisbra(eventos, config.UFS)

    modelo_sismo.upsert_lote(aceitos)
    removidos = database.executar(REMOVER_FORA_DO_BRASIL, ("SISBRA",))
    descartadas = (len(lidos) - len(eventos)) + descartados_uf + max(removidos, 0)
    importadas = max(len(aceitos) - max(removidos, 0), 0)

    _registrar("SISBRA", os.path.basename(caminho), len(lidos), importadas, descartadas)
    return {
        "fonte": "SISBRA",
        "arquivo": caminho,
        "lidas": len(lidos),
        "importadas": importadas,
        "descartadas": descartadas,
    }


def importar_fdsn(caminho=None, baixar_de_novo=True):
    """Baixa/lê, grava e filtra geograficamente o catálogo FDSN."""
    caminho = caminho or ARQUIVO_FDSN
    if baixar_de_novo or not os.path.isfile(caminho):
        baixar(url_fdsn(), caminho)

    with open(caminho, encoding="utf-8", errors="replace") as arquivo:
        texto = arquivo.read()

    eventos = ler_fdsn(texto)
    aceitos, descartados = filtrar_fdsn(eventos)

    modelo_sismo.upsert_lote(aceitos)
    removidos = database.executar(REMOVER_FORA_DO_BRASIL, ("FDSN",))
    descartadas = descartados + max(removidos, 0)
    importadas = max(len(aceitos) - max(removidos, 0), 0)

    _registrar("FDSN", os.path.basename(caminho), len(eventos), importadas, descartadas)
    return {
        "fonte": "FDSN",
        "arquivo": caminho,
        "lidas": len(eventos),
        "importadas": importadas,
        "descartadas": descartadas,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Importa os catálogos SISBRA e FDSN para o PostGIS."
    )
    parser.add_argument(
        "--somente",
        choices=("sisbra", "fdsn"),
        help="importa apenas uma das fontes (padrão: as duas)",
    )
    parser.add_argument(
        "--sem-baixar",
        action="store_true",
        help="usa os arquivos já existentes em dados/brutos",
    )
    argumentos = parser.parse_args(argv)

    baixar_de_novo = not argumentos.sem_baixar
    fontes = []
    if argumentos.somente in (None, "sisbra"):
        fontes.append(("SISBRA", importar_sisbra))
    if argumentos.somente in (None, "fdsn"):
        fontes.append(("FDSN", importar_fdsn))

    _garantir_estrutura()

    falhou = False
    for nome, funcao in fontes:
        print("Importando {}...".format(nome))
        try:
            resumo = funcao(baixar_de_novo=baixar_de_novo)
        except Exception as erro:  # noqa: BLE001 - registra e segue para a outra
            falhou = True
            print("ERRO em {}: {}".format(nome, erro))
            try:
                _registrar(nome, "", 0, 0, 0, erro=str(erro))
            except Exception:  # noqa: BLE001 - banco fora do ar: só reporta
                print("(não foi possível registrar a falha no banco)")
            continue
        print(
            "  {lidas} linhas lidas, {importadas} importadas, "
            "{descartadas} descartadas".format(**resumo)
        )

    if falhou:
        return 1

    total = database.consultar_um("SELECT count(*) AS n FROM sismos")
    print("Total no banco: {} eventos.".format(total["n"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
