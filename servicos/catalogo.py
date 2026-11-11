"""Leitores dos catálogos de sismos.

Aqui ficam apenas funções puras: recebem texto e devolvem a lista de eventos
normalizados. Nada de rede, nada de banco — quem chama decide de onde vem o
texto (arquivo local ou download).

Evento normalizado (mesmas chaves para todas as fontes):

    fonte, evento_id, data_hora, ano, lat, lon, profundidade_km,
    magnitude, tipo_magnitude, categoria, uf, localidade, autor
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

FONTE_SISBRA = "SISBRA"

# Horário oficial do Brasil (UTC-3), usado quando a hora do SISBRA traz "L".
FUSO_LOCAL = timezone(timedelta(hours=-3))


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

    local = hora.endswith("L") or hora.endswith("l")
    digitos = hora[:-1] if local else hora
    if not digitos.isdigit() or len(digitos) not in (2, 4, 6):
        return None

    hora_int = int(digitos[0:2])
    minuto_int = int(digitos[2:4]) if len(digitos) >= 4 else 0
    segundo_int = int(digitos[4:6]) if len(digitos) >= 6 else 0

    try:
        instante = datetime(
            int(ano),
            int(mmdd[0:2]),
            int(mmdd[2:4]),
            hora_int,
            minuto_int,
            segundo_int,
            tzinfo=FUSO_LOCAL if local else timezone.utc,
        )
    except ValueError:
        return None
    if local:
        instante = instante.astimezone(timezone.utc)
    return instante


def _autor_sisbra(resto: str) -> Optional[str]:
    """Nome entre parênteses que abre o resto da linha, se existir."""
    resto = resto.strip()
    if not resto.startswith("("):
        return None
    fecha = resto.find(")")
    if fecha < 0:
        return resto[1:].strip() or None
    return resto[1:fecha].strip() or None


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
    lat = _float_ou_none(lat_txt)
    lon = _float_ou_none(lon_txt)
    if lat is None or lon is None:
        # Linhas com largura variável desalinham as colunas: descartamos em vez
        # de gravar coordenada errada.
        return None
    if not -90.0 <= lat <= 90.0 or not -180.0 <= lon <= 180.0:
        return None

    mmdd = _campo(linha, 6, 10)
    hora = _campo(linha, 11, 19)
    uf = _campo(linha, 37, 39) or None
    categoria = _campo(linha, 53, 56) or None
    tipo_magnitude = _campo(linha, 50, 52) or None

    profundidade = _float_ou_none(_campo(linha, 40, 45))
    if profundidade == 0.0:
        profundidade = None

    magnitude = _float_ou_none(_campo(linha, 46, 49))
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
        "categoria": categoria,
        "uf": uf,
        "localidade": _campo(linha, 66, 89) or None,
        "autor": _autor_sisbra(linha[89:]),
    }


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
