"""Leitores dos catálogos de sismos.

Aqui ficam apenas funções puras: recebem texto e devolvem a lista de eventos
normalizados. Nada de rede, nada de banco — quem chama decide de onde vem o
texto (arquivo local ou download).

Evento normalizado (mesmas chaves para todas as fontes):

    fonte, evento_id, data_hora, ano, lat, lon, profundidade_km,
    magnitude, tipo_magnitude, categoria, uf, localidade, autor
"""

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

FONTE_SISBRA = "SISBRA"

# Horário oficial do Brasil (UTC-3), usado quando a hora do SISBRA traz "L".
FUSO_LOCAL = timezone(timedelta(hours=-3))

# Categorias usadas pelo catálogo (A..E = histórico, I = instrumental, R = ?).
CATEGORIAS_SISBRA = frozenset("ABCDEIR")

# Hora no começo da linha: HH, HHMM, HHMMSS, com fração opcional e sufixo L.
_HORA = re.compile(r"(\d{2}(?:\d{2}(?:\d{2}(?:\.\d+)?)?)?)(L?)(?=[\s]|$)")
_HORA_PARTES = re.compile(r"^(\d{2})(\d{2})?(\d{2})?(?:\.(\d+))?(L?)$")

# Número com ponto decimal: usado para achar latitude/longitude fora da coluna.
_COORDENADA = re.compile(r"-?\d{1,3}\.\d+")


def evento_id_sisbra(
    ano: str,
    mmdd: str,
    hora: str,
    lat: float,
    lon: float,
    mag: Optional[float],
) -> str:
    """Identificador estável (md5) de um evento do catálogo SISBRA.

    O catálogo não traz id próprio, então derivamos o id dos campos que
    identificam o evento. Os mesmos valores geram sempre o mesmo id, o que
    permite o upsert idempotente no banco.
    """
    chave = "{}|{}|{}|{}|{}|{}".format(ano, mmdd, hora, lat, lon, mag)
    return hashlib.md5(chave.encode("utf-8")).hexdigest()


def _campo(linha: str, inicio: int, fim: int) -> str:
    """Fatia fixa do arquivo já sem espaços nas pontas."""
    return linha[inicio:fim].strip()


def _float_ou_none(texto: str) -> Optional[float]:
    """Converte para float; campo vazio ou inválido vira None."""
    if not texto:
        return None
    try:
        return float(texto)
    except ValueError:
        return None


def _hora_da_linha(linha: str) -> str:
    """Texto da hora do evento, ou "" quando ausente/inválida.

    A coluna começa em 11, mas a hora pode ocupar 9 caracteres quando tem
    fração de segundo (`132539.31`), empurrando as colunas seguintes. Por isso
    lemos por regex em vez de fatiar 8 caracteres fixos.
    """
    achado = _HORA.match(linha[11:20])
    if not achado:
        return ""
    return achado.group(1) + achado.group(2)


def _data_hora_sisbra(ano: str, mmdd: str, hora: str) -> Optional[datetime]:
    """Monta o instante do evento em UTC.

    `mmdd` e `hora` podem vir incompletos (`----`, `06--`, `--`, `18L`). Nesse
    caso devolvemos None: a data não é inventada. Sufixo `L` significa hora
    local (UTC-3); sem sufixo, a hora já é UTC.
    """
    if len(ano) != 4 or not ano.isdigit():
        return None
    if len(mmdd) != 4 or not mmdd.isdigit():
        return None

    partes = _HORA_PARTES.match(hora)
    if not partes:
        return None

    fracao = partes.group(4) or ""
    microssegundo = int((fracao + "000000")[:6]) if fracao else 0
    local = partes.group(5) == "L"

    try:
        instante = datetime(
            int(ano),
            int(mmdd[0:2]),
            int(mmdd[2:4]),
            int(partes.group(1)),
            int(partes.group(2) or 0),
            int(partes.group(3) or 0),
            microssegundo,
            tzinfo=FUSO_LOCAL if local else timezone.utc,
        )
    except ValueError:
        return None
    if local:
        instante = instante.astimezone(timezone.utc)
    return instante


def _autor_sisbra(resto: str) -> str:
    """Nome entre parênteses que abre o resto da linha, se existir."""
    resto = resto.strip()
    if not resto.startswith("("):
        return ""
    fecha = resto.find(")")
    if fecha < 0:
        return resto[1:].strip()
    return resto[1:fecha].strip()


def _campos_colunas_fixas(linha: str) -> Optional[Dict[str, object]]:
    """Campos crus lidos nas colunas do brief. None se lat/lon não convertem."""
    lat = _float_ou_none(_campo(linha, 19, 25))
    lon = _float_ou_none(_campo(linha, 26, 32))
    if lat is None or lon is None:
        return None
    return {
        "lat": lat,
        "lon": lon,
        "uf": _campo(linha, 37, 39),
        "profundidade": _campo(linha, 40, 45),
        "magnitude": _campo(linha, 46, 49),
        "tipo_magnitude": _campo(linha, 50, 52),
        "categoria": _campo(linha, 53, 56),
        "localidade": _campo(linha, 66, 89),
        "autor": _autor_sisbra(linha[89:]),
    }


def _campos_colunas_deslocadas(linha: str) -> Optional[Dict[str, object]]:
    """Recupera linhas em que as colunas depois da longitude andaram.

    O catálogo tem linhas escritas com hora de 9 caracteres (`132539.31`) ou
    latitude/longitude de largura variável (`-4.81`, `-08.2635`). O deslocamento
    medido no início da longitude (posição 26, de +1 a +4 nas linhas
    desalinhadas do catálogo) **não** vale para a linha inteira: os campos
    seguintes ficam separados por um espaço e voltam a encostar nas colunas
    originais perto do fim. Por isso recuperamos a
    latitude/longitude pelo primeiro par de números do trecho e os campos do
    meio (`err st depth mag tm CAT Io [Af]`) por tokens; localidade e autor
    continuam nas colunas fixas, que essas linhas não deslocam.

    Devolve None quando a linha não encaixa no formato: melhor descartar do que
    gravar coordenada ou magnitude errada.
    """
    achados = list(_COORDENADA.finditer(linha[19:40]))
    if len(achados) < 2:
        return None
    achado_lat, achado_lon = achados[0], achados[1]
    fim_lat = achado_lat.start() + len(achado_lat.group())
    if achado_lon.start() < fim_lat:
        return None

    # Deslocamento do início da longitude em relação à coluna 26 do brief.
    deslocamento = achado_lon.start() + 19 - 26
    if not 0 <= deslocamento <= 8:
        return None
    fim_lon = achado_lon.start() + 19 + len(achado_lon.group())

    tokens = linha[fim_lon:66].split()
    if len(tokens) not in (7, 8):
        return None
    uf, profundidade, magnitude, tipo_magnitude, categoria = tokens[1:6]

    if len(uf) != 2 or not uf.isalpha():
        return None
    if categoria not in CATEGORIAS_SISBRA:
        return None
    if tipo_magnitude != "-1":
        if len(tipo_magnitude) != 1 or not tipo_magnitude.isdigit():
            return None
    if _float_ou_none(profundidade) is None or _float_ou_none(magnitude) is None:
        return None

    return {
        "lat": float(achado_lat.group()),
        "lon": float(achado_lon.group()),
        "uf": uf,
        "profundidade": profundidade,
        "magnitude": magnitude,
        "tipo_magnitude": tipo_magnitude,
        "categoria": categoria,
        "localidade": _campo(linha, 66, 89),
        "autor": _autor_sisbra(linha[89:]),
    }


def _montar_evento(
    linha: str, ano: str, campos: Dict[str, object]
) -> Optional[Dict[str, object]]:
    """Aplica as regras de normalização comuns a todas as linhas."""
    lat = campos["lat"]
    lon = campos["lon"]
    if not -90.0 <= lat <= 90.0 or not -180.0 <= lon <= 180.0:
        return None

    mmdd = _campo(linha, 6, 10)
    hora = _hora_da_linha(linha)

    tipo_magnitude = campos["tipo_magnitude"] or None
    profundidade = _float_ou_none(campos["profundidade"])
    if profundidade == 0.0:
        profundidade = None
    magnitude = _float_ou_none(campos["magnitude"])
    if tipo_magnitude == "-1" or magnitude == 0.0:
        magnitude = None

    return {
        "fonte": FONTE_SISBRA,
        "evento_id": evento_id_sisbra(ano, mmdd, hora, lat, lon, magnitude),
        "data_hora": _data_hora_sisbra(ano, mmdd, hora),
        "ano": int(ano),
        "lat": lat,
        "lon": lon,
        "profundidade_km": profundidade,
        "magnitude": magnitude,
        "tipo_magnitude": tipo_magnitude,
        "categoria": campos["categoria"] or None,
        "uf": campos["uf"] or None,
        "localidade": campos["localidade"] or None,
        "autor": campos["autor"] or None,
    }


def _ler_linha_sisbra(linha: str) -> Optional[Dict[str, object]]:
    """Interpreta uma linha de evento. Devolve None quando deve ser descartada."""
    if len(linha) < 52:
        return None

    ano = _campo(linha, 1, 5)
    if len(ano) != 4 or not ano.isdigit():
        return None

    lat_txt = _campo(linha, 19, 25)
    lon_txt = _campo(linha, 26, 32)
    if lat_txt in ("", "--") or lon_txt in ("", "--"):
        return None

    campos = _campos_colunas_fixas(linha)
    if campos is None:
        campos = _campos_colunas_deslocadas(linha)
    if campos is None:
        return None
    return _montar_evento(linha, ano, campos)


def ler_sisbra(texto: str) -> List[Dict[str, object]]:
    """Lê o catálogo SISBRA em colunas fixas e devolve os eventos normalizados.

    Linhas vazias, comentários (`#`) e eventos sem coordenada são ignorados.
    """
    eventos = []
    for linha in texto.splitlines():
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        evento = _ler_linha_sisbra(linha)
        if evento is not None:
            eventos.append(evento)
    return eventos
