"""Modelo dos sismos: carga, upsert e (mais adiante) consultas espaciais."""

import json
from typing import Dict, List

from db import database
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


__all__ = ["upsert_lote", "carregar_estados", "COLUNAS"]
