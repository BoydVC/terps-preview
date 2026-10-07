#!/usr/bin/env python3
"""Build the Terps Hoops 2026-27 Preview from raw source files in data/. Nothing is typed in by hand
except the Dispatch poll, which is a transcription of the fetched article (data/dispatch_b1g_poll.json)."""
import json, os, re, sys, datetime as dt
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
ROOT = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(ROOT, "data")
sys.path.insert(0, ROOT)
from nuxt import load_payload, resolver, find_objects
ET = ZoneInfo("America/New_York")
rd = lambda f: open(os.path.join(D, f), encoding="utf-8").read()
jl = lambda f: json.load(open(os.path.join(D, f)))

# ---------------- roster ----------------
def roster(fname):
    arr = load_payload(rd(fname)); r = resolver(arr); out = []
    for i, v in enumerate(arr):
        if isinstance(v, dict) and "jerseyNumber" in v and "heightFeet" in v:
            o = r(i)
            out.append({"id": o["playerId"], "first": o["firstName"], "last": o["lastName"],
                        "name": f'{o["firstName"]} {o["lastName"]}'.strip(), "num": o["jerseyNumber"],
                        "pos": o["positionShort"], "pos_long": o.get("positionLong"), "cls": o["academicYearShort"],
                        "ht": f'{o["heightFeet"]}\' {o["heightInches"]}"' if o["heightFeet"] else None,
                        "ht_in": (int(o["heightFeet"]) * 12 + int(o["heightInches"] or 0)) if o["heightFeet"] else None,
                        "wt": o["weight"], "hometown": o["hometown"], "hs": o["highSchool"],
                        "prev": (o["previousSchool"] or "").strip() or None, "captain": bool(o.get("isCaptain"))})
    seen = set(); uniq = []
    for p in out:
        if p["id"] not in seen: seen.add(p["id"]); uniq.append(p)
    return uniq
cur = roster("umterps_roster.html"); last = roster("umterps_roster_2025-26.html")
last_ids = {p["id"] for p in last}; cur_ids = {p["id"] for p in cur}
for p in cur:
    if p["id"] in last_ids: p["status"] = "Returner"
    elif p["prev"]: p["status"] = "Transfer"
    elif p["cls"] in ("Fr.", "R-Fr."): p["status"] = "Freshman"
    else: p["status"] = "Newcomer"
departures = [dict(p, final_cls=p["cls"]) for p in last if p["id"] not in cur_ids]
counts = {k: sum(1 for p in cur if p["status"] == k) for k in ("Returner", "Transfer", "Freshman", "Newcomer")}
avg_ht = sum(p["ht_in"] for p in cur if p["ht_in"]) / len([p for p in cur if p["ht_in"]])
tallest = max(cur, key=lambda p: p["ht_in"] or 0)
cls_counts = {}
for p in cur: cls_counts[p["cls"]] = cls_counts.get(p["cls"], 0) + 1

# ---------------- staff ----------------
ch = rd("umterps_coaches.html"); soup = BeautifulSoup(ch, "html.parser")
ptxt = re.sub(r"[ \t\xa0]+", " ", soup.get_text("\n", strip=True))
i_coach = ptxt.find("Coaching Staff"); i_sup = ptxt.find("Support Staff")
def section_for(name):
    j = ptxt.find(name.split(",")[0], i_coach)
    if j < 0: return ""
    return "Coaching Staff" if (i_sup < 0 or j < i_sup) else "Support Staff"
arr = load_payload(ch); r = resolver(arr); staff = []
for i, v in enumerate(arr):
    if isinstance(v, dict) and "staffId" in v:
        o = r(i); name = re.sub(r"\s+", " ", f'{o["firstName"]} {o["lastName"]}').strip()
        sec = section_for(name)
        bio = BeautifulSoup(o.get("bio") or "", "html.parser")
        paras = []
        for p in bio.find_all(["p", "div"]):
            t = re.sub(r"\s+", " ", p.get_text(" ", strip=True))
            if 80 < len(t) < 1500 and t not in paras and not t.startswith("Personal Information"): paras.append(t)
        left = bio.select_one(".coach-left")
        if left:
            sents = re.split(r"(?<=[.!?])\s+(?=[A-Z])", re.sub(r"\s+", " ", left.get_text(" ", strip=True)))
            t = " ".join(sents[:4])
            if t and t not in paras: paras.insert(1 if paras else 0, t)
        staff.append({"name": name, "title": o["title"], "section": sec, "bio": paras[:2]})
coaching = [s for s in staff if s["section"] == "Coaching Staff"]
head = next(s for s in coaching if s["title"] == "Head Coach")
last_staff_titles = {}
try:
    s2 = BeautifulSoup(rd("umterps_roster_2025-26.html"), "html.parser")
    for card in s2.select('[data-test-id="s-person-card-list__root"]'):
        t = card.get_text(" ", strip=True)
        if "Head Coach" in t and "Assistant" not in t: last_staff_titles["head"] = t.split(" Head Coach")[0]
except Exception: pass

# ---------------- 2026-27 schedule ----------------
sh = rd("umterps_schedule.html")
games = find_objects(sh, ["date", "opponent", "at_vs", "location"])
# venue titles published on cards (by order)
sched = []
for k, g in enumerate(games):
    d = dt.datetime.fromisoformat(g["date"])
    opp = (g.get("opponent") or {}).get("title") or "TBA"
    tour = g["tournament"]["title"] if isinstance(g.get("tournament"), dict) else None
    fac = g["facility"]["title"] if isinstance(g.get("facility"), dict) else None
    promo = g.get("promotion") or ""
    # umterps publishes the arena name for its Baltimore games as the game-card label ("promotion" field)
    venue = fac or (promo if re.search(r"Arena|Center|Centre|Stadium|Field|Pavilion|Garden", promo) else None)
    sched.append({"date": d.date().isoformat(), "dow": d.strftime("%a"), "time": None if g["tbd"] or not g["time"] else g["time"],
                  "opp": opp, "exh": g["type"] == "S" or "(Exh.)" in opp, "at_vs": g["at_vs"], "site": g["location_indicator"],
                  "location": g["location"], "venue": venue, "tv": (g.get("media") or {}).get("tv") or None,
                  "radio": (g.get("media") or {}).get("radio") or None, "b1g": bool(g["conference"]), "event": tour,
                  "id": g["id"]})
reg = [g for g in sched if not g["exh"]]

# ---------------- 2025-26 results (umterps + ESPN cross-check) ----------------
lg = find_objects(rd("umterps_schedule_2025-26.html"), ["date", "opponent", "at_vs", "location"])
results = []
for g in lg:
    res = g["result"] if isinstance(g.get("result"), dict) else {}
    if g["type"] == "S" or not res.get("status"): continue
    d = dt.datetime.fromisoformat(g["date"])
    opp = g["opponent"]["title"]; rank = None
    m = re.match(r"^(#\d+|RV)\s+(.*)$", opp)
    if m: rank, opp = m.group(1), m.group(2)
    tour = g["tournament"]["title"] if isinstance(g.get("tournament"), dict) else None
    results.append({"date": d.date().isoformat(), "opp": opp, "opp_rank": rank, "at_vs": g["at_vs"], "site": g["location_indicator"],
                    "res": res["status"], "pf": int(res["team_score"]), "pa": int(res["opponent_score"]),
                    "note": res.get("postscore_info") or "", "b1g": bool(g["conference"]), "event": tour,
                    "post": g["type"] == "P", "local_time": d.strftime("%H:%M")})
W = L = 0
for x in results:
    W += x["res"] == "W"; L += x["res"] == "L"; x["w"], x["l"] = W, L
cw = sum(1 for x in results if x["b1g"] and x["res"] == "W"); cl = sum(1 for x in results if x["b1g"] and x["res"] == "L")
def rec(xs): return {"w": sum(1 for x in xs if x["res"] == "W"), "l": sum(1 for x in xs if x["res"] == "L")}
last_season = {"w": W, "l": L, "conf_w": cw, "conf_l": cl, "home": rec([x for x in results if x["site"] == "H"]),
               "away": rec([x for x in results if x["site"] == "A"]), "neutral": rec([x for x in results if x["site"] == "N"]),
               "vs_ranked": rec([x for x in results if x["opp_rank"] and x["opp_rank"].startswith("#")]),
               "pf": sum(x["pf"] for x in results), "pa": sum(x["pa"] for x in results), "games": len(results)}
# ESPN standings: seed / conference finish
seed = None; espn_conf = None; espn_overall = None
def walk(o):
    global seed, espn_conf, espn_overall
    if isinstance(o, dict):
        if isinstance(o.get("standings"), dict) and "entries" in o["standings"]:
            for e in o["standings"]["entries"]:
                if e["team"].get("id") == "120":
                    st = {s["name"]: s.get("displayValue") for s in e["stats"]}
                    seed = st.get("playoffSeed"); espn_overall = st.get("overall")
                    espn_conf = next((s.get("displayValue") for s in e["stats"] if s.get("type") == "vsconf" or s["name"] == "vs. Conf."), None)
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(jl("espn_b1g_standings_2026.json"))
last_season.update({"b1g_seed": seed, "espn_overall": espn_overall})
espn_summary = jl("espn_team.json")["team"].get("standingSummary")
# Big Ten tournament and postseason
btt = [x for x in results if x["post"]]
last_season["btt"] = [{"opp": x["opp"], "res": x["res"], "pf": x["pf"], "pa": x["pa"], "date": x["date"]} for x in btt]

# ---------------- rankings / projections ----------------
rk = jl("espn_rankings.json"); polls = []
for p in rk.get("rankings", []):
    md = any(t["team"].get("id") == "120" for t in p.get("ranks", []))
    mo = any(t["team"].get("id") == "120" for t in p.get("others", []))
    polls.append({"name": p["name"], "headline": p.get("headline"), "date": p.get("date"), "maryland_ranked": md, "maryland_votes": mo})
latest_poll_date = max((p["date"] for p in polls if p.get("date")), default=None)
ap_preseason_published = bool(latest_poll_date and latest_poll_date >= "2026-10-01")
dispatch = jl("dispatch_b1g_poll.json")
md_poll = next(t for t in dispatch["standings"] if t["team"] == "Maryland")
poll_rank = {t["team"]: t["rank"] for t in dispatch["standings"]}

# ---------------- games to circle (rule-based, from real schedule) ----------------
last_vs = {}
for x in results:
    last_vs.setdefault(x["opp"], []).append(x)
nat_tv = {"FOX", "ESPN", "ESPN2", "CBS", "FS1", "Peacock/NBCSN", "NBC", "TNT", "truTV", "ABC"}
circle = []
for g in reg:
    score = 0; why = []
    pr = poll_rank.get(g["opp"])
    if pr and pr <= 5: score += 6 - pr + 3; why.append(f"Picked {['','1st','2nd','3rd','4th','5th'][pr]} in the Big Ten preseason media poll")
    lv = last_vs.get(g["opp"], [])
    for x in lv:
        if x["res"] == "L" and x["pa"] - x["pf"] >= 15: score += 3; why.append(f"Rematch: lost {x['pf']}-{x['pa']} last season ({dt.date.fromisoformat(x['date']).strftime('%b %-d')})"); break
        if x["res"] == "L": score += 1.5; why.append(f"Rematch: lost {x['pf']}-{x['pa']} last season"); break
        if x["res"] == "W": score += .5; why.append(f"Won {x['pf']}-{x['pa']} last season"); break
    if g["tv"] in ("FOX", "ESPN", "CBS", "ABC"): score += 2; why.append(f"National TV on {g['tv']}")
    if g["location"] and g["location"].startswith("Baltimore"): score += 4.5; why.append(f"Neutral-site game in Baltimore{' at ' + g['venue'] if g['venue'] else ''}")
    if g["event"]: score += 2; why.append(g["event"] + (f", {g['location']}" if g["location"] else ""))
    if g["opp"] in ("Georgetown", "Virginia") : score += 2; why.append("Regional non-conference matchup")
    if g["date"] == max(x["date"] for x in reg): score += 1.5; why.append("Regular-season finale")
    if g["b1g"] and g["date"] == min(x["date"] for x in reg if x["b1g"]): score += 1; why.append("Big Ten opener")
    if score >= 3.5 and g["opp"] != "TBA" and "/" not in g["opp"]:
        circle.append(dict(g, score=round(score, 1), why=why))
circle.sort(key=lambda g: (-g["score"], g["date"]))
circle = sorted(circle[:10], key=lambda g: g["date"])

# ---------------- meta ----------------
f_um = rd("fetched_umterps.txt").strip(); f_es = rd("fetched_espn.txt").strip()
sources = [
  {"name": "umterps.com: 2026-27 roster", "url": "https://umterps.com/sports/mens-basketball/roster", "fetched": f_um},
  {"name": "umterps.com: 2025-26 roster (for returners/departures)", "url": "https://umterps.com/sports/mens-basketball/roster/2025-26", "fetched": f_um},
  {"name": "umterps.com: coaching staff and Buzz Williams bio", "url": "https://umterps.com/sports/mens-basketball/coaches", "fetched": f_um},
  {"name": "umterps.com: 2026-27 schedule (dates, times, TV, venues)", "url": "https://umterps.com/sports/mens-basketball/schedule", "fetched": f_um},
  {"name": "umterps.com: 2025-26 schedule and results", "url": "https://umterps.com/sports/mens-basketball/schedule/2025-26", "fetched": f_um},
  {"name": "ESPN public JSON: 2025-26 Maryland schedule (score cross-check)", "url": "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/120/schedule?season=2026", "fetched": f_es},
  {"name": "ESPN public JSON: 2025-26 Big Ten standings", "url": "https://site.api.espn.com/apis/v2/sports/basketball/mens-college-basketball/standings?group=7&season=2026", "fetched": f_es},
  {"name": "ESPN public JSON: AP / Coaches rankings feed", "url": "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/rankings", "fetched": f_es},
  {"name": dispatch["source"], "url": dispatch["url"], "fetched": dispatch["fetched_at"]},
]
out = {"meta": {"built_at": dt.datetime.now(ET).isoformat(timespec="seconds"), "fetched_umterps": f_um, "fetched_espn": f_es, "sources": sources},
       "head": head, "coaching": coaching, "roster": sorted(cur, key=lambda p: int(p["num"]) if str(p["num"]).isdigit() else 99),
       "counts": counts, "cls_counts": cls_counts, "avg_ht": round(avg_ht, 1), "tallest": {"name": tallest["name"], "ht": tallest["ht"]},
       "departures": departures, "last_roster_size": len(last), "last_season": last_season, "results": results,
       "espn_summary": espn_summary, "schedule": sched,
       "sched_counts": {"total": len(sched), "exh": sum(1 for g in sched if g["exh"]), "reg": len(reg), "b1g": sum(1 for g in reg if g["b1g"]),
                        "home": sum(1 for g in reg if g["site"] == "H"), "away": sum(1 for g in reg if g["site"] == "A"),
                        "neutral": sum(1 for g in reg if g["site"] == "N"), "tba_time": sum(1 for g in reg if not g["time"]),
                        "tv_listed": sum(1 for g in reg if g["tv"])},
       "polls": polls, "ap_preseason_published": ap_preseason_published, "latest_poll_date": latest_poll_date,
       "dispatch": dispatch, "md_poll": md_poll, "circle": circle}
json.dump(out, open(os.path.join(D, "preview.json"), "w"), indent=1)
tpl = rd("../src/template.html") if False else open(os.path.join(ROOT, "src", "template.html"), encoding="utf-8").read()
html = tpl.replace("/*__DATA__*/null", json.dumps(out, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/"))
for p in ("dist/index.html", "dist/terps-2026-27-preview.html"):
    open(os.path.join(ROOT, p), "w", encoding="utf-8").write(html)
print(f"roster {len(cur)} ({counts}), departures {len(departures)}, sched {len(sched)} ({len(reg)} reg, {out['sched_counts']['b1g']} B1G), last {W}-{L} ({cw}-{cl}), circle {len(circle)}")
for g in circle: print("  circle", g["date"], g["opp"], g["score"], g["why"])
