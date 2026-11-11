#!/usr/bin/env bash
# Publica a aplicação em /opt/sismos-br e reinicia o serviço systemd.
# Uso: sudo bash scripts/deploy_app.sh [origem]
set -euo pipefail

ORIGEM="${1:-$(pwd)}"
DESTINO="/opt/sismos-br"
SERVICO="sismos-br"

if [ ! -f "${ORIGEM}/app.py" ]; then
  echo "origem inválida: ${ORIGEM}/app.py não existe" >&2
  exit 1
fi

echo "==> Copiando arquivos para ${DESTINO}"
sudo mkdir -p "${DESTINO}"
sudo rsync -a --delete \
  --exclude ".git" \
  --exclude ".venv" \
  --exclude "__pycache__" \
  --exclude ".superpowers" \
  --exclude ".env" \
  --exclude "dados/brutos" \
  "${ORIGEM}/" "${DESTINO}/"

echo "==> Ambiente virtual e dependências"
if [ ! -x "${DESTINO}/.venv/bin/python" ]; then
  sudo python3 -m venv "${DESTINO}/.venv"
fi
sudo "${DESTINO}/.venv/bin/pip" install --quiet --upgrade pip
sudo "${DESTINO}/.venv/bin/pip" install --quiet -r "${DESTINO}/requirements.txt"

echo "==> Arquivo .env"
if [ ! -f "${DESTINO}/.env" ] || [ "${FORCAR_ENV:-0}" = "1" ]; then
  sudo cp "${DESTINO}/.env.vm" "${DESTINO}/.env"
fi

sudo chown -R melque:melque "${DESTINO}"
sudo chmod +x "${DESTINO}/scripts/"*.sh

echo "==> Serviço systemd"
sudo install -m 0644 "${DESTINO}/deploy/${SERVICO}.service" "/etc/systemd/system/${SERVICO}.service"
sudo install -m 0644 "${DESTINO}/deploy/sismos-atualizar.service" "/etc/systemd/system/sismos-atualizar.service"
sudo install -m 0644 "${DESTINO}/deploy/sismos-atualizar.timer" "/etc/systemd/system/sismos-atualizar.timer"
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICO}"
sudo systemctl restart "${SERVICO}"
sudo systemctl enable --now sismos-atualizar.timer

sleep 2
echo "==> Teste rápido"
PORTA_APP="$(grep -E '^PORTA=' "${DESTINO}/.env" | cut -d= -f2)"
curl -fsS -m 10 "http://127.0.0.1:${PORTA_APP:-8080}/api/status" | head -c 300 || {
  echo "AVISO: /api/status não respondeu; veja: journalctl -u ${SERVICO} -n 50" >&2
}
echo
echo "Deploy concluído."
