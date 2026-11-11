#!/usr/bin/env bash
# Confere o estado real da VM: serviço, API, banco e túnel.
set -uo pipefail

echo "==> Serviço"
systemctl is-active sismos-br || true
systemctl is-enabled sismos-br || true

echo
echo "==> API"
PORTA_APP="$(grep -E '^PORTA=' /opt/sismos-br/.env | cut -d= -f2)"
curl -fsS -m 10 "http://127.0.0.1:${PORTA_APP:-8080}/api/status" || echo "API não respondeu"
echo

echo "==> Contagem por fonte"
sudo -u postgres psql -d sismos_br -Atc \
  "SELECT fonte, count(*) FROM sismos GROUP BY fonte ORDER BY fonte;" || true

echo
echo "==> Eventos fora da malha do IBGE (deve ser 0)"
sudo -u postgres psql -d sismos_br -Atc \
  "SELECT count(*) FROM sismos s WHERE NOT EXISTS (SELECT 1 FROM estados e WHERE ST_Contains(e.geom, s.geom));" || true

echo
echo "==> UFs carregadas (deve ser 27)"
sudo -u postgres psql -d sismos_br -Atc "SELECT count(*) FROM estados;" || true

echo
echo "==> Últimas importações"
sudo -u postgres psql -d sismos_br -Atc \
  "SELECT fonte, linhas_lidas, linhas_importadas, linhas_descartadas, concluido_em FROM importacoes ORDER BY id DESC LIMIT 5;" || true

echo
echo "==> Túnel"
if systemctl is-active --quiet cloudflared-quick; then
  echo "cloudflared-quick: ativo"
  sudo journalctl -u cloudflared-quick -n 120 --no-pager \
    | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | tail -n1 || true
elif systemctl is-active --quiet cloudflared; then
  echo "cloudflared (nomeado): ativo"
else
  echo "sem túnel ativo"
fi

echo
echo "==> Saúde do sistema"
uptime
free -h | head -n 2
df -h / | tail -n 1
