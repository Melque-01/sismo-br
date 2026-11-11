"""Controller das consultas de sismos: validação central dos filtros.

Os endpoints em si ficam no fim deste módulo (Task 7 do plano); aqui está a
regra única de validação usada por todos eles.
"""

from datetime import date
from typing import Dict, Mapping, Optional

import config
from servicos.catalogo import CATEGORIAS_SISBRA

FONTES = ("todas", "SISBRA", "FDSN")


class ErroValidacao(Exception):
    """Filtro inválido: o controller responde 400 com esta mensagem."""


def _texto(dados: Mapping[str, object], chave: str) -> str:
    valor = dados.get(chave)
    if valor is None:
        return ""
    return str(valor).strip()


def _inteiro(
    dados: Mapping[str, object],
    chave: str,
    padrao: int,
    rotulo: str,
    minimo: int,
    maximo: int,
) -> int:
    texto = _texto(dados, chave)
    if not texto:
        return padrao
    try:
        valor = int(texto)
    except ValueError:
        raise ErroValidacao(
            "{} inválido: use um número entre {} e {}.".format(rotulo, minimo, maximo)
        )
    if not minimo <= valor <= maximo:
        raise ErroValidacao(
            "{} inválido: use um número entre {} e {}.".format(rotulo, minimo, maximo)
        )
    return valor


def _decimal(
    dados: Mapping[str, object],
    chave: str,
    rotulo: str,
    minimo: float,
    maximo: float,
) -> Optional[float]:
    texto = _texto(dados, chave)
    if not texto:
        return None
    try:
        valor = float(texto)
    except ValueError:
        raise ErroValidacao(
            "{} inválida: use um número entre {} e {}.".format(rotulo, minimo, maximo)
        )
    if not minimo <= valor <= maximo:
        raise ErroValidacao(
            "{} inválida: use um número entre {} e {}.".format(rotulo, minimo, maximo)
        )
    return valor


def montar_filtros(dados: Mapping[str, object]) -> Dict[str, object]:
    """Valida e normaliza os filtros vindos da query string.

    Devolve sempre o dicionário completo, com os padrões preenchidos, para o
    model não precisar repetir regra de negócio.
    """
    ano_atual = date.today().year
    ano_ini = _inteiro(
        dados, "ano_ini", config.ANO_MIN, "Ano inicial", config.ANO_MIN, ano_atual
    )
    ano_fim = _inteiro(
        dados, "ano_fim", ano_atual, "Ano final", config.ANO_MIN, ano_atual
    )
    if ano_ini > ano_fim:
        raise ErroValidacao(
            "Ano inicial ({}) não pode ser maior que o ano final ({}).".format(
                ano_ini, ano_fim
            )
        )

    celula_texto = _texto(dados, "celula")
    celula = config.CELULA_PADRAO
    if celula_texto:
        try:
            celula = float(celula_texto)
        except ValueError:
            celula = -1.0
        if celula not in config.CELULAS:
            raise ErroValidacao(
                "Célula inválida: use {} graus.".format(
                    ", ".join(str(valor) for valor in config.CELULAS)
                )
            )

    fonte = (_texto(dados, "fonte") or "todas").upper()
    if fonte.lower() == "todas":
        fonte = "todas"
    if fonte not in FONTES:
        raise ErroValidacao("Fonte inválida: use SISBRA, FDSN ou todas.")

    uf_texto = _texto(dados, "uf").upper()
    uf = uf_texto or None
    if uf is not None and uf not in config.UFS:
        raise ErroValidacao("UF inválida: use a sigla de duas letras (ex.: MG).")

    categoria_texto = _texto(dados, "categoria").upper()
    categoria = categoria_texto or None
    if categoria is not None and categoria not in CATEGORIAS_SISBRA:
        raise ErroValidacao("Categoria inválida: use A, B, C, D, E, I ou R.")

    mag_min = _decimal(dados, "mag_min", "Magnitude mínima", -1.0, 10.0)
    mag_max = _decimal(dados, "mag_max", "Magnitude máxima", -1.0, 10.0)
    if mag_min is not None and mag_max is not None and mag_min > mag_max:
        raise ErroValidacao(
            "Magnitude mínima ({}) não pode ser maior que a máxima ({}).".format(
                mag_min, mag_max
            )
        )

    prof_max = _decimal(dados, "prof_max", "Profundidade máxima", 0.0, 800.0)

    return {
        "ano_ini": ano_ini,
        "ano_fim": ano_fim,
        "mag_min": mag_min,
        "mag_max": mag_max,
        "prof_max": prof_max,
        "fonte": fonte,
        "uf": uf,
        "categoria": categoria,
        "celula": celula,
    }
