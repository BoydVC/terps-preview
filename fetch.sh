#!/usr/bin/env bash
# Re-fetch public source data (read-only GETs). The Dispatch poll is kept as a transcription (data/dispatch_b1g_poll.json).
set -euo pipefail
cd "$(dirname "$0")/data"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129 Safari/537.36"
U=https://umterps.com/sports/mens-basketball
curl -sfL -m 30 -A "$UA" "$U/roster" -o umterps_roster.html
curl -sfL -m 30 -A "$UA" "$U/roster/2025-26" -o umterps_roster_2025-26.html
curl -sfL -m 30 -A "$UA" "$U/schedule" -o umterps_schedule.html
curl -sfL -m 30 -A "$UA" "$U/schedule/2025-26" -o umterps_schedule_2025-26.html
curl -sfL -m 30 -A "$UA" "$U/coaches" -o umterps_coaches.html
date -Iseconds > fetched_umterps.txt
E=https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball
curl -sf -m 30 "$E/teams/120" -o espn_team.json
curl -sf -m 30 "$E/teams/120/roster" -o espn_roster.json
curl -sf -m 30 "$E/teams/120/schedule?season=2026" -o espn_sched_2026.json
curl -sf -m 30 "$E/teams/120/schedule?season=2027" -o espn_sched_2027.json
curl -sf -m 30 "$E/rankings" -o espn_rankings.json
curl -sf -m 30 "https://site.api.espn.com/apis/v2/sports/basketball/mens-college-basketball/standings?group=7&season=2026" -o espn_b1g_standings_2026.json
date -Iseconds > fetched_espn.txt
echo "fetched: umterps $(cat fetched_umterps.txt), espn $(cat fetched_espn.txt)"
