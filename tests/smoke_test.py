#!/usr/bin/env python3
"""Smoke test: cross-check roster, schedule and last-season counts on the page against the raw sources."""
import json, os, re, sys, datetime as dt
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); D = os.path.join(ROOT, "data")
sys.path.insert(0, ROOT)
from nuxt import find_objects
P = json.load(open(os.path.join(D, "preview.json")))
fails = []
def check(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
rd = lambda f: open(os.path.join(D, f), encoding="utf-8").read()

# --- Roster vs umterps visible HTML cards (independent of the Nuxt payload used by build.py)
def html_players(f):
    s = BeautifulSoup(rd(f), "html.parser"); out = []
    for c in s.select('[data-test-id="s-person-card-list__root"]'):
        t = re.sub(r"\s+", " ", c.get_text(" ", strip=True))
        m = re.match(r"Jersey Number (\d+) (.+?) Position (\S+) Academic Year (\S+) Height (\d)' (\d+)''", t)
        if m: out.append({"num": m.group(1), "name": m.group(2), "pos": m.group(3), "cls": m.group(4), "ht": f"{m.group(5)}' {m.group(6)}\""})
    return out
hp = html_players("umterps_roster.html")
check(len(hp) == len(P["roster"]) == 16, f"2026-27 roster count: HTML cards {len(hp)} == page {len(P['roster'])}")
pg = {p["num"]: p for p in P["roster"]}
mism = [h for h in hp if h["num"] not in pg or pg[h["num"]]["name"] != h["name"] or pg[h["num"]]["cls"] != h["cls"] or pg[h["num"]]["pos"] != h["pos"] or pg[h["num"]]["ht"] != h["ht"]]
check(not mism, f"every player's number/name/position/class/height matches umterps HTML ({len(mism)} mismatches)")
hl = html_players("umterps_roster_2025-26.html")
check(len(hl) == P["last_roster_size"], f"2025-26 roster count {len(hl)} == {P['last_roster_size']}")
c = P["counts"]
check(sum(c.values()) == len(P["roster"]), f"returners+transfers+freshmen+newcomers {sum(c.values())} == roster")
names_last = {h["name"] for h in hl}; names_cur = {h["name"] for h in hp}
check(c["Returner"] == len(names_last & names_cur), f"returners {c['Returner']} == name overlap {len(names_last & names_cur)}")
check(sorted(p["name"] for p in P["departures"]) == sorted(names_last - names_cur), f"departures ({len(P['departures'])}) == last roster minus current")
check(all(p["prev"] for p in P["roster"] if p["status"] == "Transfer"), "every transfer has a published previous school")
# --- Staff
check(P["head"]["name"] == "Buzz Williams" and P["head"]["title"] == "Head Coach", "head coach is the umterps.com Head Coach")
ctext = BeautifulSoup(rd("umterps_coaches.html"), "html.parser").get_text(" ", strip=True)
check(all(s["name"].split(",")[0].split()[-1] in ctext for s in P["coaching"]), "all staff names appear on the coaches page")
staff_raw = find_objects(rd("umterps_coaches.html"), ["staffId", "bio"])
bio_txt = re.sub(r"\s+", " ", BeautifulSoup(next(o["bio"] for o in staff_raw if o["title"] == "Head Coach"), "html.parser").get_text(" ")).replace("\xa0", " ")
check(all(re.sub(r"\s+", " ", b.replace("\xa0", " "))[:80] in bio_txt for b in P["head"]["bio"]), "head-coach bio text is quoted verbatim from umterps.com")
# --- Schedule vs visible HTML game cards
cards = BeautifulSoup(rd("umterps_schedule.html"), "html.parser").select('[data-test-id="s-game-card-standard__root"]')
check(len(cards) == len(P["schedule"]) == P["sched_counts"]["total"], f"schedule count: HTML cards {len(cards)} == page {len(P['schedule'])}")
b1g_html = sum(1 for cd in cards if re.search(r"\bBig Ten\b", cd.get_text(" ", strip=True)))
check(b1g_html == P["sched_counts"]["b1g"] == 20, f"Big Ten games: HTML tags {b1g_html} == page {P['sched_counts']['b1g']} (Big Ten plays 20)")
exh_html = sum(1 for cd in cards if "(Exh.)" in cd.get_text(" ", strip=True))
check(exh_html == P["sched_counts"]["exh"], f"exhibitions {exh_html} == {P['sched_counts']['exh']}")
for cd, g in zip(cards, P["schedule"]):
    d = cd.select_one('[data-test-id="s-game-card-standard__header-game-date"]')
    lab = re.sub(r"\s+", " ", d.get_text(" ", strip=True)) if d else ""
    want = dt.date.fromisoformat(g["date"]).strftime("%b %-d")
    if want not in lab: check(False, f"date mismatch {g['date']} vs card '{lab}'")
check(True, "every game date matches its umterps card")
for g in P["schedule"]:
    if dt.date.fromisoformat(g["date"]).strftime("%a") != g["dow"]: check(False, f"weekday mismatch {g['date']}")
tba = [g for g in P["schedule"] if not g["time"]]
check(all(g["opp"] in ("TBA",) or "/" in g["opp"] for g in tba), f"only TBD bracket games lack times ({len(tba)})")
# --- Times are ET: last season's umterps local times == ESPN UTC converted to ET
es = json.load(open(os.path.join(D, "espn_sched_2026.json")))["events"]
espn_by_date = {}
for e in es:
    t = dt.datetime.fromisoformat(e["date"].replace("Z", "+00:00")).astimezone(ZoneInfo("America/New_York"))
    espn_by_date[t.date().isoformat()] = (t.strftime("%H:%M"), e)
ok = tot = 0
for x in P["results"]:
    if x["date"] in espn_by_date and x["local_time"] not in ("23:59", "00:00"):
        tot += 1; ok += espn_by_date[x["date"]][0] == x["local_time"]
check(tot >= 25 and ok == tot, f"umterps times are Eastern: {ok}/{tot} last-season tip times match ESPN (UTC→ET)")
# --- Last season results vs ESPN scores
md = 0; n = 0
for e in es:
    comp = e["competitions"][0]; s = {c["team"]["id"]: c for c in comp["competitors"]}
    if "120" not in s: continue
    me = s.pop("120"); them = list(s.values())[0]
    gs = lambda c: int(c["score"]["displayValue"] if isinstance(c["score"], dict) else c["score"])
    n += 1
    t = dt.datetime.fromisoformat(e["date"].replace("Z", "+00:00")).astimezone(ZoneInfo("America/New_York")).date().isoformat()
    x = next((r for r in P["results"] if r["date"] == t), None)
    if x and x["pf"] == gs(me) and x["pa"] == gs(them): md += 1
check(n == len(P["results"]) and md == n, f"all {md}/{n} last-season scores match ESPN")
LS = P["last_season"]
check(f"{LS['w']}-{LS['l']}" == LS["espn_overall"], f"last season {LS['w']}-{LS['l']} == ESPN standings {LS['espn_overall']}")
check(LS["w"] == sum(1 for r in P["results"] if r["res"] == "W") and LS["w"] + LS["l"] == len(P["results"]), "W-L recomputed from game list")
est = {}
def walk(o):
    if isinstance(o, dict):
        if isinstance(o.get("standings"), dict):
            for e in o["standings"]["entries"]:
                if e["team"]["id"] == "120": est.update({x["type"]: x.get("displayValue") for x in e["stats"]})
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(json.load(open(os.path.join(D, "espn_b1g_standings_2026.json"))))
for key, mine in [("vsconf", f"{LS['conf_w']}-{LS['conf_l']}"), ("home", f"{LS['home']['w']}-{LS['home']['l']}"), ("road", f"{LS['away']['w']}-{LS['away']['l']}"),
                  ("vsaprankedteams", f"{LS['vs_ranked']['w']}-{LS['vs_ranked']['l']}"), ("pointsfor", str(LS["pf"])), ("pointsagainst", str(LS["pa"])), ("playoffseed", str(LS["b1g_seed"]))]:
    check(est.get(key) == mine, f"ESPN standings {key} {est.get(key)} == page {mine}")
# --- Projections
dp = P["dispatch"]
check(len(dp["standings"]) == 18 and [t["rank"] for t in dp["standings"]] == list(range(1, 19)), "media poll has 18 ranked teams")
check(all(dp["standings"][i]["points"] > dp["standings"][i+1]["points"] for i in range(17)), "poll points strictly descending")
check(P["md_poll"]["rank"] == 12 and P["md_poll"]["points"] == 203, "Maryland 12th, 203 points in the poll")
b1g_opps = {g["opp"] for g in P["schedule"] if g["b1g"]}
check(b1g_opps <= {t["team"] for t in dp["standings"]}, "every Big Ten opponent appears in the poll")
check(not P["ap_preseason_published"], "AP/Coaches preseason poll correctly flagged unpublished (feed shows final 2025-26 poll)")
# --- Games to circle are real schedule games
ids = {g["id"] for g in P["schedule"]}
check(all(g["id"] in ids and g["why"] for g in P["circle"]) and 5 <= len(P["circle"]) <= 10, f"{len(P['circle'])} games to circle all come from the schedule with reasons")
# --- Snapshot offline
html = open(os.path.join(ROOT, "dist", "terps-2026-27-preview.html"), encoding="utf-8").read()
check(not re.findall(r'<(?:script|link|img|iframe)[^>]+(?:src|href)=["\']https?://', html), "snapshot loads no external resources")
check("/*__DATA__*/null" not in html, "data embedded in snapshot")
print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED")); sys.exit(1 if fails else 0)
