"""Controller das consultas de sismos: validação central dos filtros e API."""

import traceback
from datetime import date
from typing import Dict, Mapping, Optional

import config
from controles import respostas
from modelo import sismo as modelo_sismo
from servicos.catalogo import CATEGORIAS_SISBRA

FONTES = ("todas", "SISBRA", "FDSN")
METRICAS = ("contagem", "normalizada")


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


# --- Endpoints da API -----------------------------------------------------


def _resposta_api(calcular):
    """Executa o cálculo do endpoint traduzindo erros em respostas JSON."""
    try:
        return respostas.json_resposta(calcular())
    except ErroValidacao as erro:
        return respostas.json_resposta({"ok": False, "erro": str(erro)}, 400)
    except Exception:  # noqa: BLE001 - banco fora do ar, SQL inválido etc.
        traceback.print_exc()
        return respostas.json_resposta(
            {
                "ok": False,
                "erro": "Banco de dados indisponível. Tente novamente em instantes.",
            },
            503,
        )


def _coordenada(
    dados: Mapping[str, object], chave: str, rotulo: str, minimo: float, maximo: float
) -> float:
    """Lê uma coordenada obrigatória e confere se está dentro do recorte."""
    texto = _texto(dados, chave)
    if not texto:
        raise ErroValidacao("Informe {}.".format(rotulo))
    try:
        valor = float(texto)
    except ValueError:
        raise ErroValidacao(
            "{} inválida: use um número entre {} e {}.".format(rotulo, minimo, maximo)
        )
    if not minimo <= valor <= maximo:
        raise ErroValidacao(
            "{} fora do Brasil: use um valor entre {} e {}.".format(
                rotulo, minimo, maximo
            )
        )
    return valor


def _metrica(dados: Mapping[str, object]) -> str:
    metrica = (_texto(dados, "metrica") or "contagem").lower()
    if metrica not in METRICAS:
        raise ErroValidacao("Métrica inválida: use contagem ou normalizada.")
    return metrica


def _limite(dados: Mapping[str, object]) -> int:
    texto = _texto(dados, "limite")
    if not texto:
        return config.LIMITE_PONTOS
    try:
        limite = int(texto)
    except ValueError:
        raise ErroValidacao(
            "Limite inválido: use um número entre 1 e {}.".format(config.TETO_PONTOS)
        )
    if not 1 <= limite <= config.TETO_PONTOS:
        raise ErroValidacao(
            "Limite inválido: use um número entre 1 e {}.".format(config.TETO_PONTOS)
        )
    return limite


def _feature_celula(celula: Dict[str, object]) -> Dict[str, object]:
    propriedades = {
        chave: celula[chave]
        for chave in (
            "n",
            "mag_max",
            "mag_media",
            "densidade_km2",
            "ano_ini",
            "ano_fim",
            "area_km2",
        )
    }
    return {
        "type": "Feature",
        "geometry": celula["geometry"],
        "properties": propriedades,
    }


def _feature_ponto(ponto: Dict[str, object]) -> Dict[str, object]:
    propriedades = {
        chave: ponto.get(chave)
        for chave in (
            "id",
            "ano",
            "data_hora",
            "magnitude",
            "profundidade_km",
            "uf",
            "localidade",
            "fonte",
        )
    }
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [ponto["lon"], ponto["lat"]],
        },
        "properties": propriedades,
    }


def api_densidade(dados):
    """GET /api/densidade — grade de contagem por célula."""

    def calcular():
        metrica = _metrica(dados)
        filtros = montar_filtros(dados)
        resultado = modelo_sismo.densidade(filtros, filtros["celula"], metrica)
        return {
            "ok": True,
            "celula": filtros["celula"],
            "metrica": metrica,
            "total_eventos": resultado["total"],
            "cortes": resultado["cortes"],
            "celulas": {
                "type": "FeatureCollection",
                "features": [
                    _feature_celula(celula) for celula in resultado["celulas"]
                ],
            },
        }

    return _resposta_api(calcular)


def api_sismos(dados):
    """GET /api/sismos — pontos para a camada de calor."""

    def calcular():
        filtros = montar_filtros(dados)
        limite = _limite(dados)
        pontos = modelo_sismo.pontos(filtros, limite)
        return {
            "ok": True,
            "limite": limite,
            "total": len(pontos),
            "sismos": {
                "type": "FeatureCollection",
                "features": [_feature_ponto(ponto) for ponto in pontos],
            },
        }

    return _resposta_api(calcular)


def api_celula(dados):
    """GET /api/celula?lat=&lon= — eventos da célula clicada."""

    def calcular():
        lat = _coordenada(dados, "lat", "Latitude", -34.0, 6.0)
        lon = _coordenada(dados, "lon", "Longitude", -74.0, -34.0)
        filtros = montar_filtros(dados)
        eventos = modelo_sismo.eventos_celula(filtros, lat, lon, filtros["celula"])
        return {
            "ok": True,
            "lat": lat,
            "lon": lon,
            "celula": filtros["celula"],
            "total": len(eventos),
            "eventos": eventos,
        }

    return _resposta_api(calcular)


def api_evento(dados):
    """GET /api/evento?id= — ficha completa de um evento."""

    def calcular():
        texto = _texto(dados, "id")
        try:
            evento_id = int(texto)
        except ValueError:
            raise ErroValidacao("Id de evento inválido.")
        evento = modelo_sismo.buscar_evento(evento_id)
        if evento is None:
            raise ErroValidacao("Evento não encontrado.")
        return {"ok": True, "evento": evento}

    return _resposta_api(calcular)


def api_estatisticas(dados):
    """GET /api/estatisticas — resumo do recorte filtrado."""

    def calcular():
        filtros = montar_filtros(dados)
        return {"ok": True, **modelo_sismo.estatisticas(filtros)}

    return _resposta_api(calcular)


def api_filtros(dados):
    """GET /api/filtros — opções reais para os selects."""

    def calcular():
        return {"ok": True, **modelo_sismo.opcoes_filtros()}

    return _resposta_api(calcular)


def api_status(dados):
    """GET /api/status — saúde do banco e contagens."""

    def calcular():
        return {"ok": True, **modelo_sismo.status_dados()}

    return _resposta_api(calcular)


def api_importacoes(dados):
    """GET /api/importacoes — últimas execuções do importador."""

    def calcular():
        return {"ok": True, "importacoes": modelo_sismo.importacoes_recentes()}

    return _resposta_api(calcular)
