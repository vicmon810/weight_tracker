#!/bin/bash 

set -euo pipefail 

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [ -f "../.env" ];then
    source $ENV_FILE
else 
    echo "Error ../.env"
    exit 1
fi 

LOCAL_DB="../store/health.db" 
OUTGOING_DB="../store/outgoing.db" 

: "${HEALTH_REMOTE_INCOMING_FILE:?Missing HEALTH_REMOTE_IMCOMING_FILE}"



echo "Creating outgoing db"
rm -f "$OUTGOING_DB"
sqlite3 "$LOCAL_DB" ".backup '$OUTGOING_DB'"

echo "Pushing outgoing db"
./sync.sh push "$OUTGOINNG_DB" "$HEALTH_REMOTE_INCOMING_FILE"

echo "push completed"