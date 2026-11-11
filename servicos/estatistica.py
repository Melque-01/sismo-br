"""Estatística descritiva usada nos endpoints da API.

Funções puras: recebem listas de números e devolvem cortes/histograma. Ficam
fora do model para poderem ser testadas sem banco.
"""

import math
from typing import Dict, List, Optional, Sequence

CLASSES_PADRAO = 5
LARGURA_PADRAO = 0.5


def _indice_quantil(percentual: float, total: int) -> int:
    """Índice (0-based) do quantil por posto (nearest-rank).

    Usar posto em vez de interpolação deixa o resultado determinístico e
    igual ao que o mapa desenha: os cortes são valores que existem nos dados.
    """
    posto = max(math.ceil(percentual / 100.0 * total), 1)
    return min(posto, total) - 1


def cortes(valores: Sequence[float], classes: int = CLASSES_PADRAO) -> List[float]:
    """Cortes (quantis) que dividem os valores em `classes` faixas.

    Lista vazia devolve lista vazia: períodos sem sismo não podem quebrar a
    legenda. Valores repetidos geram menos cortes, não cortes duplicados.
    """
    if classes < 2:
        return []
    ordenados = sorted(valores)
    if not ordenados:
        return []

    total = len(ordenados)
    resultado = []
    for indice in range(1, classes):
        percentual = 100.0 * indice / classes
        valor = ordenados[_indice_quantil(percentual, total)]
        if not resultado or valor != resultado[-1]:
            resultado.append(valor)
    return resultado


def histograma(
    valores: Sequence[Optional[float]], largura: float = LARGURA_PADRAO
) -> List[Dict[str, float]]:
    """Conta valores em faixas de largura fixa ancoradas em múltiplos da largura.

    Ignora `None` (eventos sem magnitude/profundidade). Devolve as faixas
    ordenadas, com `de`, `ate` e `n`.
    """
    if largura <= 0:
        raise ValueError("largura do histograma precisa ser positiva")

    contagem: Dict[float, int] = {}
    for valor in valores:
        if valor is None:
            continue
        inicio = round(math.floor(float(valor) / largura) * largura, 6)
        contagem[inicio] = contagem.get(inicio, 0) + 1

    return [
        {"de": inicio, "ate": round(inicio + largura, 6), "n": contagem[inicio]}
        for inicio in sorted(contagem)
    ]
