"""
sheets_loader.py
Reads data directly from a public Google Sheet (CSV export endpoints).
No API key needed — sheet just needs to be "Anyone with link can view".

Sheet ID: 1JlHUEVu-_vnh8qQy-7V0qRoIY3J_5SFf0fr3ZgUJhAo
Tabs (gid):
  SOURCES       = 0
  FAB_COUNT     = automatically found by tab name
  FABS          = automatically found by tab name
  MILESTONES    = automatically found by tab name
"""

import csv
import json
import io
import urllib.request
import urllib.error
import time

SHEET_ID = "1JlHUEVu-_vnh8qQy-7V0qRoIY3J_5SFf0fr3ZgUJhAo"
YEARS    = [2020, 2021, 2022, 2023, 2024, 2025, 2026]

# Cache so we don't hammer Google on every request
_cache = {"data": None, "ts": 0}
CACHE_TTL = 60  # seconds


def csv_url(gid):
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"


def fetch_csv(gid):
    url = csv_url(gid)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return list(csv.reader(io.StringIO(resp.read().decode("utf-8"))))


def get_sheet_gids():
    """Fetch the sheet HTML to find tab gids by name."""
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8")
        import re
        # Find all gid:"NUMBER" and name pairs
        gids = {}
        matches = re.findall(r'"name":"([^"]+)"[^}]*?"gid":(\d+)', html)
        for name, gid in matches:
            gids[name.upper()] = int(gid)
        return gids
    except Exception:
        # fallback defaults
        return {"SOURCES": 0, "FAB_COUNT": 1, "FABS": 2, "MILESTONES": 3}


def parse_fab_count(rows):
    """Rows: Country | 2020_Active | 2020_Construction | ... | Source"""
    result = {str(y): {} for y in YEARS}
    if not rows:
        return result
    # Skip header row(s)
    header = rows[0]
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        country = row[0].strip()
        if country.upper() in ("COUNTRY", "TOTAL", ""):
            continue
        col = 1
        for y in YEARS:
            try:
                active = int(row[col]) if col < len(row) and row[col].strip() else 0
            except ValueError:
                active = 0
            try:
                constr = int(row[col+1]) if col+1 < len(row) and row[col+1].strip() else 0
            except ValueError:
                constr = 0
            result[str(y)][country] = {"active": active, "construction": constr}
            col += 2
    return result


def parse_fabs(rows, companies):
    """Rows: Fab_ID | Company | Category | Loc | Name | Country | 2020..2026 | Source"""
    fabs = []
    if not rows:
        return fabs
    for row in rows[1:]:
        if not row or not row[0].strip() or row[0].strip().upper() == "FAB_ID":
            continue
        fab_id  = row[0].strip()
        company = row[1].strip() if len(row) > 1 else ""
        loc     = row[3].strip() if len(row) > 3 else ""
        name    = row[4].strip() if len(row) > 4 else ""
        years = {}
        for yi, y in enumerate(YEARS):
            ci = 6 + yi
            if ci < len(row) and row[ci].strip():
                years[str(y)] = row[ci].strip()
        fabs.append({"id": fab_id, "company": company, "loc": loc,
                     "name": name, "years": years})
    return fabs


def parse_milestones(rows):
    """Rows: Year | Milestone | Source"""
    result = {str(y): [] for y in YEARS}
    if not rows:
        return result
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        try:
            year = str(int(float(row[0].strip())))
        except (ValueError, TypeError):
            continue
        if len(row) > 1 and row[1].strip() and year in result:
            result[year].append(row[1].strip())
    return result


def load_from_sheets(base_data):
    """
    Fetch all tabs from Google Sheets and merge into base_data.
    base_data should contain 'companies' and 'coords' (kept from data.json).
    Returns merged data dict.
    """
    try:
        gids = get_sheet_gids()
        fab_count_gid = gids.get("FAB_COUNT", 1)
        fabs_gid      = gids.get("FABS", 2)
        ms_gid        = gids.get("MILESTONES", 3)

        fab_count_rows = fetch_csv(fab_count_gid)
        fabs_rows      = fetch_csv(fabs_gid)
        ms_rows        = fetch_csv(ms_gid)

        base_data["fab_count_by_country"] = parse_fab_count(fab_count_rows)
        base_data["fabs"]       = parse_fabs(fabs_rows, base_data.get("companies", {}))
        base_data["milestones"] = parse_milestones(ms_rows)
        return base_data, None
    except Exception as e:
        return base_data, str(e)


def get_data(base_data):
    """Return cached data, refreshing from Sheets if cache is stale."""
    global _cache
    now = time.time()
    if _cache["data"] is None or (now - _cache["ts"]) > CACHE_TTL:
        merged, err = load_from_sheets(dict(base_data))
        if err:
            print(f"[sheets_loader] Warning: {err} — using cached/local data")
            if _cache["data"] is None:
                _cache["data"] = base_data
        else:
            _cache["data"] = merged
            _cache["ts"] = now
    return _cache["data"]
