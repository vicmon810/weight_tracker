#!/bin/bash
set -e 

DB = ../store/health.db
SNAP = ../store/health_snap.db

sqlite3 "$DB"".backup '$SNAP'"
rsync -av "$SNAP" @user@remote:/store/health.db