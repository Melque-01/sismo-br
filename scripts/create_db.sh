#!/usr/bin/env bash
# Cria o papel, o banco e o schema do Sismos BR.
# Uso: sudo bash scripts/create_db.sh 'senha-do-banco'
set -euo pipefail

SENHA="${1:?uso: create_db.sh 'senha-do-banco'}"
DIRETORIO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

como_postgres() {
  sudo -u postgres "$@"
}

echo "==> Papel e banco"
como_postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sismos_br') THEN
    CREATE ROLE sismos_br LOGIN PASSWORD '${SENHA}';
  ELSE
    ALTER ROLE sismos_br WITH LOGIN PASSWORD '${SENHA}';
  END IF;
END
\$\$;
SQL

if ! como_postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname = 'sismos_br'" | grep -q 1; then
  como_postgres createdb -O sismos_br sismos_br
fi

echo "==> PostGIS"
como_postgres psql -v ON_ERROR_STOP=1 -d sismos_br -c "CREATE EXTENSION IF NOT EXISTS postgis;"

echo "==> Schema"
como_postgres psql -v ON_ERROR_STOP=1 -d sismos_br -f "${DIRETORIO}/db/schema.sql"

echo "==> Permissões para o usuário da aplicação"
como_postgres psql -v ON_ERROR_STOP=1 -d sismos_br <<'SQL'
GRANT USAGE, CREATE ON SCHEMA public TO sismos_br;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO sismos_br;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO sismos_br;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sismos_br;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO sismos_br;

-- As tabelas passam a pertencer ao usuário da aplicação: o boot repete
-- CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS e o Postgres exige
-- ser dono da tabela mesmo quando ela já existe.
DO $$
DECLARE
  item record;
BEGIN
  FOR item IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I OWNER TO sismos_br', item.tablename);
  END LOOP;
  FOR item IN SELECT sequencename FROM pg_sequences WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER SEQUENCE public.%I OWNER TO sismos_br', item.sequencename);
  END LOOP;
END
$$;
SQL

echo "Banco sismos_br pronto."
