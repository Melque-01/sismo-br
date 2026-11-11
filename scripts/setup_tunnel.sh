#!/usr/bin/env bash
# Publica o serviço na internet pelo Cloudflare Tunnel.
# Uso: sudo bash scripts/setup_tunnel.sh quick
#      sudo bash scripts/setup_tunnel.sh token <TOKEN-DO-TUNEL>
set -euo pipefail

MODO="${1:-quick}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "==> Instalando cloudflared"
  ARQUIVO="/tmp/cloudflared-linux-amd64.deb"
  curl -fsSL -o "${ARQUIVO}" \
    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
  sudo dpkg -i "${ARQUIVO}"
fi

if [ "${MODO}" = "token" ]; then
  TOKEN="${2:?uso: setup_tunnel.sh token <TOKEN-DO-TUNEL>}"
  echo "==> Túnel nomeado (token)"
  sudo cloudflared service install "${TOKEN}"
  sudo systemctl enable --now cloudflared
  echo "Túnel nomeado configurado. O domínio é o definido no painel da Cloudflare."
  exit 0
fi

echo "==> Túnel rápido (URL temporária)"
sudo tee /etc/systemd/system/cloudflared-quick.service >/dev/null <<'UNIT'
[Unit]
Description=Cloudflare Quick Tunnel para o Sismos BR
After=network-online.target sismos-br.service
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/cloudflared tunnel --no-autoupdate --protocol http2 --url http://127.0.0.1:8080
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now cloudflared-quick
sleep 8

URL="$(sudo journalctl -u cloudflared-quick -n 100 --no-pager \
  | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | tail -n1 || true)"
if [ -n "${URL}" ]; then
  echo "URL pública: ${URL}"
else
  echo "A URL ainda não apareceu. Rode:"
  echo "  sudo journalctl -u cloudflared-quick -n 100 --no-pager | grep trycloudflare"
fi
