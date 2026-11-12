"""Configurações do projeto.

Lê o arquivo `.env` (se existir) e expõe os valores usados pelo resto do
código. Nada aqui acessa a rede ou o banco.
"""

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent


def _carregar_env(caminho=RAIZ / ".env"):
    """Lê pares CHAVE=VALOR do .env sem dependência externa."""
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


_carregar_env()

# --- Servidor -------------------------------------------------------------
HOST = os.getenv("HOST", "127.0.0.1")
PORTA = int(os.getenv("PORTA", "8000"))

# --- PostgreSQL / PostGIS -------------------------------------------------
BANCO = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "sismos_br"),
    "user": os.getenv("DB_USER", "sismos_br"),
    "password": os.getenv("DB_PASSWORD", "sismos_br"),
    "connect_timeout": int(os.getenv("DB_TIMEOUT", "5")),
}

# --- Fontes de dados ------------------------------------------------------
# Catálogo do SISBRA (CSUSP/IAG-USP) e serviço FDSN do Moho/IAG-USP.
URL_SISBRA = os.getenv(
    "URL_SISBRA",
    "https://seiscode.iag.usp.br/CSUSP/sisbra/raw/branch/master/catalogo_RAW.dat",
)
URL_FDSN = os.getenv("URL_FDSN", "http://www.moho.iag.usp.br/fdsnws/event/1/query")
FDSN_DESDE = os.getenv("FDSN_DESDE", "2024-01-01")

# Recorte que cobre o território brasileiro.
FDSN_BBOX = {
    "minlatitude": -34.0,
    "maxlatitude": 6.0,
    "minlongitude": -74.0,
    "maxlongitude": -34.0,
}

# --- Mapa de densidade ----------------------------------------------------
# Tamanho da célula da grade, em graus.
CELULAS = (0.25, 0.5, 1.0, 2.0)
CELULA_PADRAO = 0.5

# Limite de pontos enviados ao navegador e teto para o recorte.
LIMITE_PONTOS = 6000
TETO_PONTOS = 20000

# Ano mínimo aceito nos filtros (descarta datas absurdas do catálogo).
ANO_MIN = 1500

# --- Login ---------------------------------------------------------------
# Credenciais do único usuário do site. Sem LOGIN_SENHA, o login fica
# desabilitado (ninguém entra).
LOGIN_EMAIL = os.getenv("LOGIN_EMAIL", "")
LOGIN_SENHA = os.getenv("LOGIN_SENHA", "")

# Segredo que assina o cookie de sessão. Se vazio, um segredo aleatório é
# gerado no boot (sessões caem a cada reinício).
SEGREDO_SESSAO = os.getenv("SESSION_SECRET", "")
SESSAO_TTL = int(os.getenv("SESSION_TTL", "43200"))  # 12 horas

# --- Caminhos -------------------------------------------------------------
PASTA_DADOS = RAIZ / "dados"
PASTA_BRUTOS = PASTA_DADOS / "brutos"
ARQUIVO_ESTADOS = PASTA_DADOS / "brasil_uf.geojson"

# --- Unidades federativas ------------------------------------------------
UFS = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)
