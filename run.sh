#!/usr/bin/env bash
# Terps Hoops 2026-27 Preview: (optional re-fetch) -> build -> smoke test -> serve dist/ on :4252 (nohup)
#   ./run.sh          build from cached data/
#   ./run.sh --fetch  re-fetch umterps.com + ESPN first
set -euo pipefail
cd "$(dirname "$0")"
PORT=${PORT:-4252}
[ "${1:-}" = "--fetch" ] && ./fetch.sh
python3 build.py
python3 tests/smoke_test.py
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then echo "port $PORT already serving"; else
  nohup python3 -m http.server "$PORT" --bind 0.0.0.0 --directory dist > server.log 2>&1 &
  echo "serving http://localhost:$PORT/ (pid $!)"
fi
