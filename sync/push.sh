#!/bin/bash 

set -euo pipefail 

if [ -f "../.env" ];then
    source "../.env"
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