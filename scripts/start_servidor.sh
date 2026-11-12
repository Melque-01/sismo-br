#!/usr/bin/env bash
# Sobe/religa o Sismos BR em um servidor SEM systemd (container com SSH).
# Uso: bash scripts/start_servidor.sh
set -u

DIRETORIO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIRETORIO}"

echo "==> PostgreSQL"
if ! pg_isready -q -h 127.0.0.1 -p 5432 2>/dev/null; then
  sudo pg_ctlcluster 16 main start || true
  sleep 2
fi
pg_isready -h 127.0.0.1 -p 5432 || true

echo "==> Aplicação"
if ! pgrep -f "python app.py" >/dev/null 2>&1; then
  setsid -f .venv/bin/python app.py >> app.log 2>&1 < /dev/null
  sleep 3
fi
pgrep -af "python app.py" | head -n1 || echo "app não subiu"

echo "==> Túnel"
if ! pgrep -f "cloudflared tunnel" >/dev/null 2>&1; then
  setsid -f cloudflared tunnel --no-autoupdate --protocol http2 \
    --url http://127.0.0.1:8080 > tunnel.log 2>&1 < /dev/null
  sleep 10
fi
pgrep -af "cloudflared tunnel" | head -n1 || echo "túnel não subiu"

echo
echo "==> API"
curl -fsS -m 10 http://127.0.0.1:8080/api/status || echo "API não respondeu"
echo
echo "==> URL pública"
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' tunnel.log | tail -n1 \
  || echo "URL ainda não apareceu; veja tunnel.log"
