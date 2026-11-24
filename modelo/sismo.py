"""Modelo dos sismos: carga, upsert e (mais adiante) consultas espaciais."""

import json
import math
from datetime import date
from typing import Dict, List, Optional, Tuple

import config
from db import database
from servicos import estatistica
from servicos.geografia import uf_do_codarea

# Colunas gravadas no banco, na ordem em que os parâmetros são enviados.
COLUNAS = (
    "fonte",
    "evento_id",
    "data_hora",
    "ano",
    "geom",
    "profundidade_km",
    "magnitude",
    "tipo_magnitude",
    "categoria",
    "uf",
    "localidade",
    "autor",
)

UPSERT_SISMO = """
INSERT INTO sismos (
    fonte, evento_id, data_hora, ano, geom, profundidade_km, magnitude,
    tipo_magnitude, categoria, uf, localidade, autor
) VALUES (
    %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s, %s, %s, %s, %s
)
ON CONFLICT (fonte, evento_id) DO UPDATE SET
    data_hora = EXCLUDED.data_hora,
    ano = EXCLUDED.ano,
    geom = EXCLUDED.geom,
    profundidade_km = EXCLUDED.profundidade_km,
    magnitude = EXCLUDED.magnitude,
    tipo_magnitude = EXCLUDED.tipo_magnitude,
    categoria = EXCLUDED.categoria,
    uf = EXCLUDED.uf,
    localidade = EXCLUDED.localidade,
    autor = EXCLUDED.autor
"""

UPSERT_ESTADO = """
INSERT INTO estados (codarea, uf, geom)
VALUES (%s, %s, ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)))
ON CONFLICT (codarea) DO UPDATE SET
    uf = EXCLUDED.uf,
    geom = EXCLUDED.geom
"""


def _parametros(evento: Dict[str, object]) -> tuple:
    """Converte o evento normalizado nos parâmetros do UPSERT_SISMO."""
    return (
        evento["fonte"],
        evento["evento_id"],
        evento.get("data_hora"),
        evento["ano"],
        evento["lon"],
        evento["lat"],
        evento.get("profundidade_km"),
        evento.get("magnitude"),
        evento.get("tipo_magnitude"),
        evento.get("categoria"),
        evento.get("uf"),
        evento.get("localidade"),
        evento.get("autor"),
    )


def upsert_lote(eventos: List[Dict[str, object]]) -> int:
    """Grava/atualiza um lote de eventos e devolve quantos foram processados.

    A chave (fonte, evento_id) garante idempotência: reimportar o catálogo
    atualiza as linhas existentes em vez de duplicá-las.
    """
    if not eventos:
        return 0
    database.executar_lote(UPSERT_SISMO, [_parametros(evento) for evento in eventos])
    return len(eventos)


def carregar_estados(caminho: str) -> int:
    """Carrega a malha do IBGE (GeoJSON) na tabela `estados`.

    Devolve o número de UFs gravadas. `codarea` vem nas propriedades de cada
    feature; a sigla é resolvida por `servicos.geografia`.
    """
    with open(caminho, encoding="utf-8") as arquivo:
        malha = json.load(arquivo)

    parametros = []
    for feature in malha.get("features", []):
        propriedades = feature.get("properties") or {}
        codarea = str(propriedades.get("codarea") or "").strip()
        uf = uf_do_codarea(codarea)
        geometria = feature.get("geometry")
        if not codarea or not uf or not geometria:
            continue
        parametros.append((codarea, uf, json.dumps(geometria)))

    if not parametros:
        return 0
    database.executar_lote(UPSERT_ESTADO, parametros)
    return len(parametros)


def sql_filtros(f: Dict[str, object]) -> Tuple[str, list]:
    """Monta o fragmento `WHERE` e os parâmetros correspondentes.

    Os padrões (ano mínimo..ano atual, sem UF etc.) não viram condição: assim
    a consulta sem filtro usa o índice e o resultado é o mesmo.
    """
    condicoes = []
    parametros = []

    ano_ini = int(f["ano_ini"])
    ano_fim = int(f["ano_fim"])
    if ano_ini != config.ANO_MIN or ano_fim != date.today().year:
        condicoes.append("ano BETWEEN %s AND %s")
        parametros.extend([ano_ini, ano_fim])
    if f["fonte"] != "todas":
        condicoes.append("fonte = %s")
        parametros.append(f["fonte"])
    if f["uf"]:
        condicoes.append("uf = %s")
        parametros.append(f["uf"])
    if f["categoria"]:
        condicoes.append("categoria = %s")
        parametros.append(f["categoria"])
    if f["mag_min"] is not None:
        condicoes.append("magnitude >= %s")
        parametros.append(f["mag_min"])
    if f["mag_max"] is not None:
        condicoes.append("magnitude <= %s")
        parametros.append(f["mag_max"])
    if f["prof_max"] is not None:
        condicoes.append("profundidade_km <= %s")
        parametros.append(f["prof_max"])

    if not condicoes:
        return "", []
    return " WHERE " + " AND ".join(condicoes), parametros


def _condicao_extra(where: str, condicao: str) -> str:
    """Acrescenta uma condição ao WHERE já montado (ou cria o WHERE)."""
    return where + " AND " + condicao if where else " WHERE " + condicao


LARGURA_HISTOGRAMA = 0.5  # mesmas faixas de servicos.estatistica.histograma


def _histograma_magnitude(linhas):
    """Monta as faixas do histograma a partir das agregações do SQL.

    O Postgres já conta por faixa (floor(magnitude/0.5)*0.5); aqui só
    normalizamos a saída para o mesmo formato de `estatistica.histograma`.
    """
    resultado = []
    for linha in linhas:
        inicio = round(float(linha["inicio"]), 6)
        resultado.append(
            {
                "de": inicio,
                "ate": round(inicio + LARGURA_HISTOGRAMA, 6),
                "n": int(linha["n"]),
            }
        )
    return resultado


def versao_dados():
    """Assinatura barata do catálogo (invalida caches de processo do servidor).

    Usa `max(id)` (O(1) pela PK) e a última importação (índice existente) —
    um `count(*)` por request custaria mais que o próprio cache economiza.
    Qualquer importação muda a assinatura. Em falha de banco devolve
    "desconhecida" — o cache simplesmente não é usado.
    """
    try:
        linha = database.consultar_um(
            """
            SELECT coalesce(max(id), 0)::text AS maior,
                   (SELECT coalesce(max(iniciado_em)::text, '')
                      FROM importacoes) AS ultima
            FROM sismos
            """
        )
    except Exception:  # noqa: BLE001 - sem banco não há versão confiável
        return "desconhecida"
    if not linha:
        return "desconhecida"
    return "{maior}:{ultima}".format(maior=linha["maior"], ultima=linha["ultima"])


def _celula(f: Dict[str, object], celula: Optional[float]) -> float:
    """Tamanho de célula pedido, caindo no filtro validado."""
    return float(celula if celula is not None else f["celula"])


def _data_iso(valor):
    """Datas viram texto ISO para o JSON da API."""
    return valor.isoformat() if valor is not None else None


def _evento_linha(linha: Dict[str, object]) -> Dict[str, object]:
    """Normaliza uma linha da tabela para resposta da API."""
    linha = dict(linha)
    for chave in ("data_hora", "criado_em"):
        if chave in linha:
            linha[chave] = _data_iso(linha[chave])
    if "lat" in linha:
        linha["lat"] = float(linha["lat"])
    if "lon" in linha:
        linha["lon"] = float(linha["lon"])
    return linha


def densidade(
    f: Dict[str, object], celula: Optional[float] = None, metrica: str = "contagem"
) -> Dict[str, object]:
    """Agrega os eventos filtrados em células de `celula` graus.

    A célula é alinhada à origem (floor), a mesma conta usada em
    `eventos_celula` — clicar numa célula devolve exatamente os eventos que a
    formaram. Devolve as células, os cortes de cor e o total.
    """
    tamanho = _celula(f, celula)
    where, parametros = sql_filtros(f)

    sql = """
WITH base AS (
    SELECT geom, magnitude, ano
    FROM sismos{where}
), celulas AS (
    SELECT ST_SetSRID(ST_MakePoint(
               floor(ST_X(geom) / %s) * %s,
               floor(ST_Y(geom) / %s) * %s
           ), 4326) AS c,
           magnitude,
           ano
    FROM base
)
SELECT ST_X(c) AS x,
       ST_Y(c) AS y,
       count(*) AS n,
       max(magnitude) AS mag_max,
       avg(magnitude) AS mag_media,
       min(ano) AS ano_ini,
       max(ano) AS ano_fim,
       ST_AsGeoJSON(ST_MakeEnvelope(
           ST_X(c), ST_Y(c), ST_X(c) + %s, ST_Y(c) + %s, 4326
       )) AS geometry,
       ST_Area(ST_MakeEnvelope(
           ST_X(c), ST_Y(c), ST_X(c) + %s, ST_Y(c) + %s, 4326
       )::geography) / 1000000.0 AS area_km2
FROM celulas
GROUP BY c
ORDER BY n DESC
""".format(where=where)

    consulta_parametros = list(parametros) + [tamanho, tamanho, tamanho, tamanho]
    consulta_parametros += [tamanho, tamanho, tamanho, tamanho]

    linhas = database.consultar(sql, tuple(consulta_parametros))
    celulas = []
    for linha in linhas:
        quantidade = int(linha["n"])
        area = float(linha["area_km2"] or 0.0)
        celulas.append(
            {
                "x": float(linha["x"]),
                "y": float(linha["y"]),
                "n": quantidade,
                "mag_max": linha["mag_max"],
                "mag_media": (
                    round(float(linha["mag_media"]), 4)
                    if linha["mag_media"] is not None
                    else None
                ),
                "ano_ini": int(linha["ano_ini"]),
                "ano_fim": int(linha["ano_fim"]),
                "area_km2": round(area, 3),
                "densidade_km2": (
                    round(quantidade * 1000.0 / area, 4) if area else None
                ),
                "geometry": json.loads(linha["geometry"]),
            }
        )

    return {
        "total": sum(celula_["n"] for celula_ in celulas),
        "celulas": celulas,
        "cortes": estatistica.cortes([celula_["n"] for celula_ in celulas]),
        "metrica": metrica,
    }


def pontos(f: Dict[str, object], limite: int = config.LIMITE_PONTOS) -> List[dict]:
    """Lista de eventos com coordenada, para a camada de calor."""
    limite = max(1, min(int(limite), config.TETO_PONTOS))
    where, parametros = sql_filtros(f)
    sql = """
SELECT id, ST_Y(geom) AS lat, ST_X(geom) AS lon, ano, data_hora,
       magnitude, profundidade_km, uf, localidade, fonte
FROM sismos{where}
ORDER BY ano, id
LIMIT %s
""".format(where=where)
    linhas = database.consultar(sql, tuple(list(parametros) + [limite]))
    return [_evento_linha(linha) for linha in linhas]


def eventos_celula(
    f: Dict[str, object],
    lat: float,
    lon: float,
    celula: Optional[float] = None,
    limite: int = 500,
) -> List[dict]:
    """Eventos que caem na célula que contém (lat, lon)."""
    tamanho = _celula(f, celula)
    x0 = math.floor(float(lon) / tamanho) * tamanho
    y0 = math.floor(float(lat) / tamanho) * tamanho
    where, parametros = sql_filtros(f)
    condicao = (
        "geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326) "
        "AND ST_Intersects(geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))"
    )
    sql = """
SELECT id, ST_Y(geom) AS lat, ST_X(geom) AS lon, data_hora, ano, magnitude,
       profundidade_km, tipo_magnitude, categoria, uf, localidade, fonte
FROM sismos{where}
ORDER BY data_hora NULLS LAST, id
LIMIT %s
""".format(
        where=_condicao_extra(where, condicao)
    )
    parametros = list(parametros) + [
        x0,
        y0,
        x0 + tamanho,
        y0 + tamanho,
        x0,
        y0,
        x0 + tamanho,
        y0 + tamanho,
        max(1, int(limite)),
    ]
    linhas = database.consultar(sql, tuple(parametros))
    return [_evento_linha(linha) for linha in linhas]


def buscar_evento(evento_id: int) -> Optional[dict]:
    """Ficha completa de um evento pelo id interno."""
    linha = database.consultar_um(
        """
        SELECT id, fonte, evento_id, data_hora, ano,
               ST_Y(geom) AS lat, ST_X(geom) AS lon,
               profundidade_km, magnitude, tipo_magnitude, categoria, uf,
               localidade, autor, criado_em
        FROM sismos
        WHERE id = %s
        """,
        (int(evento_id),),
    )
    return _evento_linha(linha) if linha else None


def estatisticas(f: Dict[str, object]) -> Dict[str, object]:
    """Resumo estatístico do recorte filtrado (para o painel lateral)."""
    where, parametros = sql_filtros(f)

    resumo = database.consultar_um(
        """
        SELECT count(*) AS total,
               min(ano) AS ano_min,
               max(ano) AS ano_max,
               count(*) FILTER (WHERE magnitude IS NULL) AS sem_magnitude,
               count(*) FILTER (WHERE profundidade_km IS NULL) AS sem_profundidade,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY profundidade_km)
                   AS profundidade_mediana
        FROM sismos{where}
        """.format(where=where),
        tuple(parametros),
    )

    por_fonte = database.consultar(
        """
        SELECT fonte, count(*) AS n
        FROM sismos{where}
        GROUP BY fonte
        ORDER BY n DESC
        """.format(where=where),
        tuple(parametros),
    )

    maior = database.consultar_um(
        """
        SELECT id, fonte, data_hora, ano, ST_Y(geom) AS lat, ST_X(geom) AS lon,
               magnitude, profundidade_km, uf, localidade
        FROM sismos{where}
        ORDER BY magnitude DESC NULLS LAST
        LIMIT 1
        """.format(where=_condicao_extra(where, "magnitude IS NOT NULL")),
        tuple(parametros),
    )

    top_ufs = database.consultar(
        """
        SELECT uf, count(*) AS n
        FROM sismos{where}
        GROUP BY uf
        ORDER BY n DESC
        LIMIT 10
        """.format(where=_condicao_extra(where, "uf IS NOT NULL")),
        tuple(parametros),
    )

    serie_anual = database.consultar(
        """
        SELECT ano, count(*) AS n
        FROM sismos{where}
        GROUP BY ano
        ORDER BY ano
        """.format(where=where),
        tuple(parametros),
    )

    magnitudes = database.consultar(
        """
        SELECT floor(magnitude / 0.5) * 0.5 AS inicio, count(*) AS n
        FROM sismos{where}
        GROUP BY inicio
        ORDER BY inicio
        """.format(where=_condicao_extra(where, "magnitude IS NOT NULL")),
        tuple(parametros),
    )

    total = int(resumo["total"] or 0)
    return {
        "total": total,
        "ano_min": resumo["ano_min"],
        "ano_max": resumo["ano_max"],
        "por_fonte": [
            {"fonte": linha["fonte"], "n": int(linha["n"])} for linha in por_fonte
        ],
        "maior": _evento_linha(maior) if maior else None,
        "top_ufs": [
            {"uf": linha["uf"], "n": int(linha["n"])} for linha in top_ufs
        ],
        "serie_anual": [
            {"ano": int(linha["ano"]), "n": int(linha["n"])} for linha in serie_anual
        ],
        "histograma_magnitude": _histograma_magnitude(magnitudes),
        "profundidade_mediana": (
            round(float(resumo["profundidade_mediana"]), 2)
            if resumo["profundidade_mediana"] is not None
            else None
        ),
        "sem_magnitude": int(resumo["sem_magnitude"] or 0),
        "sem_profundidade": int(resumo["sem_profundidade"] or 0),
        "cobertura": {
            "magnitude_pct": (
                round(100.0 * (total - int(resumo["sem_magnitude"] or 0)) / total, 1)
                if total
                else 0.0
            ),
            "profundidade_pct": (
                round(
                    100.0 * (total - int(resumo["sem_profundidade"] or 0)) / total, 1
                )
                if total
                else 0.0
            ),
        },
    }


def opcoes_filtros() -> Dict[str, object]:
    """Valores reais do banco para popular os selects do formulário."""
    faixa = database.consultar_um(
        """
        SELECT count(*) AS total,
               min(ano) AS ano_min,
               max(ano) AS ano_max,
               min(magnitude) AS mag_min,
               max(magnitude) AS mag_max
        FROM sismos
        """
    )
    ufs = database.consultar(
        "SELECT DISTINCT uf FROM sismos WHERE uf IS NOT NULL ORDER BY uf"
    )
    fontes = database.consultar(
        "SELECT DISTINCT fonte FROM sismos ORDER BY fonte"
    )
    categorias = database.consultar(
        "SELECT DISTINCT categoria FROM sismos WHERE categoria IS NOT NULL ORDER BY categoria"
    )
    return {
        "total": int(faixa["total"] or 0),
        "ano_min": faixa["ano_min"],
        "ano_max": faixa["ano_max"],
        "mag_min": faixa["mag_min"],
        "mag_max": faixa["mag_max"],
        "ufs": [linha["uf"] for linha in ufs],
        "fontes": [linha["fonte"] for linha in fontes],
        "categorias": [linha["categoria"] for linha in categorias],
    }


def status_dados() -> Dict[str, object]:
    """Estado do banco para o rodapé e o healthcheck."""
    por_fonte = database.consultar(
        "SELECT fonte, count(*) AS n FROM sismos GROUP BY fonte ORDER BY fonte"
    )
    total = database.consultar_um("SELECT count(*) AS n FROM sismos")
    ultima = database.consultar_um(
        """
        SELECT id, fonte, arquivo, linhas_lidas, linhas_importadas,
               linhas_descartadas, iniciado_em, concluido_em, erro
        FROM importacoes
        WHERE concluido_em IS NOT NULL
        ORDER BY concluido_em DESC
        LIMIT 1
        """
    )
    if ultima:
        ultima = dict(ultima)
        ultima["iniciado_em"] = _data_iso(ultima["iniciado_em"])
        ultima["concluido_em"] = _data_iso(ultima["concluido_em"])
    return {
        "banco": True,
        "total": int(total["n"] or 0),
        "por_fonte": [
            {"fonte": linha["fonte"], "n": int(linha["n"])} for linha in por_fonte
        ],
        "ultima_importacao": ultima,
    }


def importacoes_recentes(limite: int = 20) -> List[dict]:
    """Últimas execuções do importador, mais recentes primeiro."""
    linhas = database.consultar(
        """
        SELECT id, fonte, arquivo, linhas_lidas, linhas_importadas,
               linhas_descartadas, iniciado_em, concluido_em, erro
        FROM importacoes
        ORDER BY iniciado_em DESC
        LIMIT %s
        """,
        (max(1, int(limite)),),
    )
    resultado = []
    for linha in linhas:
        item = dict(linha)
        item["iniciado_em"] = _data_iso(item["iniciado_em"])
        item["concluido_em"] = _data_iso(item["concluido_em"])
        resultado.append(item)
    return resultado


__all__ = [
    "COLUNAS",
    "buscar_evento",
    "carregar_estados",
    "densidade",
    "estatisticas",
    "eventos_celula",
    "importacoes_recentes",
    "opcoes_filtros",
    "pontos",
    "sql_filtros",
    "status_dados",
    "upsert_lote",
]
