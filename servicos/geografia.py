"""Mapa entre códigos IBGE de UF e siglas.

A malha do IBGE identifica cada unidade federativa por um `codarea` numérico
(dois dígitos). O resto da aplicação trabalha com a sigla, então a conversão
fica isolada aqui.
"""

from typing import Dict, Union

# Códigos IBGE das 27 unidades federativas.
UF_POR_CODAREA: Dict[str, str] = {
    "11": "RO",
    "12": "AC",
    "13": "AM",
    "14": "RR",
    "15": "PA",
    "16": "AP",
    "17": "TO",
    "21": "MA",
    "22": "PI",
    "23": "CE",
    "24": "RN",
    "25": "PB",
    "26": "PE",
    "27": "AL",
    "28": "SE",
    "29": "BA",
    "31": "MG",
    "32": "ES",
    "33": "RJ",
    "35": "SP",
    "41": "PR",
    "42": "SC",
    "43": "RS",
    "50": "MS",
    "51": "MT",
    "52": "GO",
    "53": "DF",
}


def uf_do_codarea(codarea: Union[str, int]) -> str:
    """Sigla da UF para o código IBGE; string vazia quando desconhecido."""
    return UF_POR_CODAREA.get(str(codarea).strip(), "")
