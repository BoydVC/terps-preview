# Terps Hoops 2026–27 Preview

A preseason magazine-style preview of Maryland men's basketball, built for Boyd (UMD) by TokenMax.

- **Live (box only):** http://localhost:4252/ (served from `dist/`)
- **Offline snapshot:** `dist/terps-2026-27-preview.html` is self-contained, with all data inlined and no external scripts, fonts or images
- **Screenshots:** `screenshots/` (best: `00-best-cover.png`)

## Sections
1. **Cover**: roster makeup, media-poll slot, last season's record, and a live countdown to the opener.
2. **Coach & staff**: Buzz Williams, with his bio quoted verbatim from umterps.com, plus the full coaching staff list.
3. **Roster**: all 16 players with number, position, class, height and weight, hometown, high school and previous school. Filter by Returners, Transfers or Freshmen, and sort by any column.
4. **Departures**: the 11 players on the 2025–26 roster who aren't on the 2026–27 one. umterps.com doesn't say where they went, so the page doesn't either.
5. **2025–26 in review**: a game-by-game margin chart with the running record and Big Ten markers, plus splits and the Big Ten Tournament results.
6. **2026–27 schedule**: 34 games (2 exhibitions and 32 regular season, 20 of them Big Ten), with ET times, TV, location and the arena name where published. Filter by Big Ten, non-conference, home, away, neutral or games to circle. Unpublished times and TV show as TBA.
7. **Projections**: the Columbus Dispatch Big Ten preseason media poll (Maryland 12th of 18) and Maryland's individual vote-getters. The AP and Coaches preseason polls are marked as not yet published.
8. **Games to circle**: 10 games picked from the real schedule by stated rules (media-poll top 5, last season's meeting, national TV, the Baltimore game, the Players Era event, the Big Ten opener). Every card lists its reasons.

## Sources (fetched Oct 7, 2026 ~5:30 PM ET; exact times in `data/fetched_*.txt`)
- umterps.com: roster (2026-27 and 2025-26), coaches, schedule (2026-27 and 2025-26). Parsed from the page's embedded Nuxt data (`nuxt.py`).
- ESPN public JSON: 2025-26 schedule and scores, Big Ten standings, AP/Coaches rankings feed.
- The Columbus Dispatch preseason media poll (Oct 5, 2026). A direct curl got HTTP 402, so it was read with a web fetch and transcribed verbatim into `data/dispatch_b1g_poll.json` along with the URL and fetch time.
- Wikipedia was rate-limited (HTTP 429) and isn't used. ESPN's roster endpoint still returned last season's list, so umterps.com is the roster source.

## Run
```bash
./run.sh          # build from cached data/, run smoke test, serve on :4252 (nohup)
./run.sh --fetch  # re-fetch umterps.com + ESPN first
python3 tests/smoke_test.py
```
`tests/smoke_test.py` (35 checks) covers:
- **Roster:** the count and every player's number, name, position, class and height match the visible umterps.com HTML cards, which are parsed independently of the payload used by build.py. Returner, departure and transfer counts are recomputed.
- **Schedule:** the game count, 20 Big Ten tags, exhibitions and every date and weekday match the umterps.com game cards.
- **Times:** umterps.com times are confirmed Eastern (31 of 31 of last season's tip times match ESPN's UTC times converted to ET).
- **Last season:** all 33 scores match ESPN, and ESPN's standings agree on overall, conference, home, road and vs-AP records, points, and seed.
- **Poll:** the poll is consistent.
- **Games to circle:** every pick is a real game.
- **Snapshot:** it's offline-safe.

## Files
`fetch.sh` → `data/*` → `build.py` (+ `nuxt.py`) → `data/preview.json` → `src/template.html` → `dist/index.html`, `dist/terps-2026-27-preview.html`


---
## Repo notes
- **Built:** Oct 7, 2026, by TokenMax (Boyd's Grok Bot) on the Grok Bot box.
- **Run:** `./run.sh` (then open the localhost URL it prints).
- Imported from `/workspace/tokenmax/terps-preview` on Oct 23, 2026. node_modules, virtualenvs, logs and files over 20 MB were left out.
- Personal details (emails, phone numbers, home street address) were replaced with `[redacted-…]` placeholders.
