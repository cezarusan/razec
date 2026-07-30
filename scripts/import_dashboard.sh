#!/bin/bash
# Importa o dashboard Apontamentos Geral no Grafana
# Uso: ./scripts/import_dashboard.sh [usuario] [senha]

GRAFANA_URL="http://172.16.0.27:3000"
USER="${1:-admin}"
PASS="${2:-admin}"
DASHBOARD_FILE="dashboards/apontamentos-geral.json"

if [ ! -f "$DASHBOARD_FILE" ]; then
  echo "Arquivo não encontrado: $DASHBOARD_FILE"
  exit 1
fi

PAYLOAD=$(python3 -c "
import json, sys
with open('$DASHBOARD_FILE') as f:
    db = json.load(f)
print(json.dumps({'dashboard': db, 'overwrite': True, 'folderId': 0}))
")

echo "Importando dashboard para $GRAFANA_URL ..."

RESPONSE=$(curl -s -w "\n%{http_code}" \
  -u "$USER:$PASS" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  "$GRAFANA_URL/api/dashboards/db")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
  URL=$(echo "$BODY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('url',''))" 2>/dev/null)
  echo "Dashboard importado com sucesso!"
  echo "Acesse: $GRAFANA_URL$URL"
else
  echo "Erro HTTP $HTTP_CODE:"
  echo "$BODY"
  exit 1
fi
