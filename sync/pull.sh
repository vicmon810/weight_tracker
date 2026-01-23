# !/usr/bin 

set -euo pipefail 


if [ -f "../.env" ];then
    source "../.env"
else 
    echo "Error ../.env"
    exit 1
fi 


LOCAL_DB="../store/health.db"
INCOMING_DB="../store/incoming.db"
SNAPSHOT_DB="../store/health_snap.db"
MERGE_SQL="merge_income.sql"

: "${HEALTH_REMOTE_INCOME_FILE:?Missing HEALTH_REMOTE_INCOME_FILE}" #REMOTE file local 

echo "Pulling remote income db" 
./sync.sh pull "$HEALTH_REMOTE_INCOME_FILE" "$INCOMING_DB"

echo "Snapshot local db"
sqlite3 "$LOCAL_DB" ".backup '$SNAPSHOT_DB'"

echo "Merge incoming -> local" 
if [ ! -f "$MERGE_SQL"]; then
    echo "Error: merge SQL '$MERGE_SQL' not found!"
    exit 1
fi 

sqlite3 "$LOCAL_DB" < "$MERGE_SQL"

rm -f "$INCOMING_DB"

echo "Pull completed"