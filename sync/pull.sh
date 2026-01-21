# usr/bin

set -e

rsync -av "$SNAP" @user@remote:/store/health.db
rsync -av user@primary:store/healthpi.db ./store/healthpi.db
