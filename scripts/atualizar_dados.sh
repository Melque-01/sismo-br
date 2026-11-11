#!/usr/bin/env bash
# Atualiza os catálogos na VM (usado pelo timer do systemd).
set -euo pipefail

cd /opt/sismos-br
exec .venv/bin/python scripts/importar_catalogo.py "$@"
