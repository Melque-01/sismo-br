#!/usr/bin/env bash
# Estado do Sismos BR em servidor sem systemd.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

echo "==> Processos"
pgrep -af "python app.py" || echo "app parado"
pgrep -af "cloudflared tunnel" || echo "túnel parado"
pg_isready -h 127.0.0.1 -p 5432 || true

echo
echo "==> API"
curl -fsS -m 10 http://127.0.0.1:8080/api/status || echo "API não respondeu"
echo
echo "==> URL pública"
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' tunnel.log | tail -n1 || echo "sem URL no log"
