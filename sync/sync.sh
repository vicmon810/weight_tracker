#!/bin/bash
set -euo pipefail 

# Usage:
# ./sysc sh pull <remote_file> <local_file>
# ./sysc sh push <local_file> <remote_file> 


if [ -f "../.env" ];then
    source "../.env"
else 
    echo "Error ../.env"
    exit 1
fi 


: "${HEALTH_REMOTE_USER:?Missing HEALTH_REMOTE_USER}"
: "${HEALTH_REMOTE_HOST:?Missing HEALTH_REMOTE_HOST}"

MODE="${1:-}"
SRC="${2:-}"
DST="${3:-}"

if [ -z "$MODE" ] || [ -z "$SRC" ] || [ -z "$DST" ]; then
    echo "Usage:"
    echo " $0 pull <remote_file> <local_file>"
    echo " $0 push <local_file> <remote_file>"
    exit 1
fi 

RSYNC_SSH=(-e "ssh")
RSYNC_FLAGS=(-avz)

case "$MODE" in
  pull)
    # SRC is remote file, DST is local file
    rsync "${RSYNC_FLAGS[@]}" "${RSYNC_SSH[@]}" \
      "${HEALTH_REMOTE_USER}@${HEALTH_REMOTE_HOST}:${SRC}" \
      "${DST}"
    ;;
  push)
    # SRC is local file, DST is remote file
    rsync "${RSYNC_FLAGS[@]}" "${RSYNC_SSH[@]}" \
      "${SRC}" \
      "${HEALTH_REMOTE_USER}@${HEALTH_REMOTE_HOST}:${DST}"
    ;;
  *)
    echo "Error: MODE must be 'pull' or 'push'"
    exit 1
    ;;
esac
