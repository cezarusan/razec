#!/bin/bash
# Dashboard de Apontamentos Geral — Inicialização automática (Linux/Mac)
#
# Para rodar na inicialização do sistema (Linux com systemd):
#   sudo cp scripts/apontamentos.service /etc/systemd/system/
#   sudo systemctl enable --now apontamentos
#
# Ou via crontab:
#   crontab -e
#   @reboot cd /caminho/do/repo && bash scripts/iniciar.sh

set -e
cd "$(dirname "$0")/.."

# verifica Python
if ! command -v python3 &>/dev/null; then
    echo "[ERRO] python3 não encontrado."
    exit 1
fi

echo ""
echo "  Dashboard de Apontamentos Geral"
echo "  http://localhost:5002"
echo ""

# abre browser depois de 2s (em paralelo)
(sleep 2 && {
    if command -v xdg-open &>/dev/null; then
        xdg-open http://localhost:5002
    elif command -v open &>/dev/null; then
        open http://localhost:5002
    fi
}) &

# inicia proxy
python3 scripts/proxy.py
