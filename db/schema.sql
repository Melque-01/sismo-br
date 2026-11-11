-- Schema do mapa de densidade de epicentros (PostgreSQL + PostGIS)
-- Aplicar com: psql -h HOST -U USUARIO -d sismos_br -f db/schema.sql

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS sismos (
    id               BIGSERIAL PRIMARY KEY,
    fonte            TEXT NOT NULL CHECK (fonte IN ('SISBRA','FDSN')),
    evento_id        TEXT NOT NULL,               -- FDSN EventID | hash deterministico SISBRA
    data_hora        TIMESTAMPTZ,                 -- NULL quando a hora e desconhecida
    ano              SMALLINT NOT NULL,           -- sempre presente; base do filtro temporal
    geom             GEOMETRY(Point, 4326) NOT NULL,
    profundidade_km  REAL CHECK (profundidade_km >= 0),
    magnitude        REAL,
    tipo_magnitude   TEXT,                        -- mR, mb, -1, ...
    categoria        TEXT,                        -- SISBRA A..I; NULL no FDSN
    uf               CHAR(2),
    localidade       TEXT,
    autor            TEXT,
    criado_em        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (fonte, evento_id)
);

CREATE INDEX IF NOT EXISTS sismos_geom_idx ON sismos USING GIST (geom);
CREATE INDEX IF NOT EXISTS sismos_ano_idx ON sismos (ano);
CREATE INDEX IF NOT EXISTS sismos_mag_idx ON sismos (magnitude);

CREATE TABLE IF NOT EXISTS estados (
    codarea  TEXT PRIMARY KEY,                    -- codigo IBGE (2 digitos)
    uf       CHAR(2) NOT NULL,
    geom     GEOMETRY(MultiPolygon, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS estados_geom_idx ON estados USING GIST (geom);

CREATE TABLE IF NOT EXISTS importacoes (
    id                BIGSERIAL PRIMARY KEY,
    fonte             TEXT NOT NULL,
    arquivo           TEXT,
    linhas_lidas      INTEGER NOT NULL DEFAULT 0,
    linhas_importadas INTEGER NOT NULL DEFAULT 0,
    linhas_descartadas INTEGER NOT NULL DEFAULT 0,
    iniciado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    concluido_em      TIMESTAMPTZ,
    erro              TEXT
);

CREATE INDEX IF NOT EXISTS importacoes_iniciado_em_idx ON importacoes (iniciado_em DESC);

COMMENT ON TABLE sismos IS 'Epicentros normalizados do SISBRA e do FDSN (somente territorio brasileiro).';
COMMENT ON COLUMN sismos.evento_id IS 'FDSN EventID ou md5(ano|mmdd|hora|lat|lon|mag) no SISBRA.';
COMMENT ON TABLE estados IS 'Malha das 27 UFs do IBGE, usada para filtrar eventos e calcular densidade.';
COMMENT ON TABLE importacoes IS 'Log de cada execucao do importador.';
