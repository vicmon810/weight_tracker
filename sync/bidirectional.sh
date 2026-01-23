# !/bin/bash 

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$SCRIPT_DIR"

echo "===Sync time $(date '+%Y-%m-%d %H:%M:%S') ==="

./pull.sh
./push.sh