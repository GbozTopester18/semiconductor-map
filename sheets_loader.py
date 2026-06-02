"""
sheets_loader.py — reads live from Google Sheets with aggressive timeout + fallback
"""
import csv, json, io, time

SHEET_ID = "1JlHUEVu-_vnh8qQy-7V0qRoIY3J_5SFf0fr3ZgUJhAo"
YEARS    = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
_cache   = {"data": None, "ts": 0}
CACHE_TTL = 120  # 2 minutes

def csv_url(gid):
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"

def fetch_csv(gid, timeout=5):
    import urllib.request
    url = csv_url(gid)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return list(csv.reader(io.StringIO(resp.read().decode("utf-8"))))

def get_sheet_gids(timeout=5):
    import urllib.request, re
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        html = resp.read().decode("utf-8")
    gids = {}
    for name, gid in re.findall(r'"name":"([^"]+)"[^}]*?"gid":(\d+)', html):
        gids[name.upper()] = int(gid)
    return gids if gids else {"FAB_COUNT":1,"FABS":2,"MILESTONES":3}

def parse_fab_count(rows):
    result = {str(y): {} for y in YEARS}
    if not rows: return result
    for row in rows[1:]:
        if not row or not row[0].strip() or row[0].upper() in ("COUNTRY","TOTAL"): continue
        country = row[0].strip()
        col = 1
        for y in YEARS:
            try: active = int(row[col]) if col < len(row) and row[col].strip() else 0
            except: active = 0
            try: constr = int(row[col+1]) if col+1 < len(row) and row[col+1].strip() else 0
            except: constr = 0
            result[str(y)][country] = {"active": active, "construction": constr}
            col += 2
    return result

def parse_fabs(rows):
    fabs = []
    if not rows: return fabs
    for row in rows[1:]:
        if not row or not row[0].strip() or row[0].upper() == "FAB_ID": continue
        years = {}
        for yi, y in enumerate(YEARS):
            ci = 6 + yi
            if ci < len(row) and row[ci].strip():
                years[str(y)] = row[ci].strip()
        fabs.append({"id":row[0].strip(),"company":row[1].strip() if len(row)>1 else "","loc":row[3].strip() if len(row)>3 else "","name":row[4].strip() if len(row)>4 else "","years":years})
    return fabs

def parse_milestones(rows):
    result = {str(y): [] for y in YEARS}
    if not rows: return result
    for row in rows[1:]:
        if not row or not row[0].strip(): continue
        try: year = str(int(float(row[0].strip())))
        except: continue
        if len(row) > 1 and row[1].strip() and year in result:
            result[year].append(row[1].strip())
    return result

def load_from_sheets(base_data):
    try:
        gids = get_sheet_gids(timeout=4)
        fab_count_rows = fetch_csv(gids.get("FAB_COUNT",1), timeout=4)
        fabs_rows      = fetch_csv(gids.get("FABS",2), timeout=4)
        ms_rows        = fetch_csv(gids.get("MILESTONES",3), timeout=4)
        base_data["fab_count_by_country"] = parse_fab_count(fab_count_rows)
        base_data["fabs"]                 = parse_fabs(fabs_rows)
        base_data["milestones"]           = parse_milestones(ms_rows)
        return base_data, None
    except Exception as e:
        return base_data, str(e)

def get_data(base_data):
    global _cache
    now = time.time()
    if _cache["data"] is None or (now - _cache["ts"]) > CACHE_TTL:
        merged, err = load_from_sheets(dict(base_data))
        if err:
            print(f"[sheets_loader] Warning: {err} — using local data")
            if _cache["data"] is None:
                _cache["data"] = base_data
        else:
            _cache["data"] = merged
            _cache["ts"] = now
    return _cache["data"]
