#!/usr/bin/env python3
"""
TENNO FRAME — Data Fetcher + Injector
1. Fetches all warframes, weapons, mods from the Warframe API
2. Writes tennoframe_data.js (loaded by browser automatically)
3. ALSO injects the data directly into index.html as inline fallback

Run:   python3 fetch_data.py
Needs: pip install requests
"""

import requests, json, time, sys, os, re

BASE    = "https://api.warframestat.us"
TIMEOUT = 30

def fetch(url, label):
    print(f"Fetching {label}...", end=" ", flush=True)
    t0 = time.time()
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={"Accept-Language": "en"})
        r.raise_for_status()
        data = r.json()
        print(f"OK  {len(data)} items  {len(r.content)//1024}KB  {time.time()-t0:.1f}s")
        return data
    except Exception as e:
        print(f"FAILED: {e}")
        return []

def trim_warframe(w):
    abilities = []
    for a in (w.get("abilities") or []):
        if isinstance(a, dict) and a.get("name"):
            abilities.append({
                "name":        a.get("name", ""),
                "description": a.get("description", "")
            })
    return {
        "name":           w.get("name", ""),
        "health":         w.get("health"),
        "shield":         w.get("shield"),
        "armor":          w.get("armor"),
        "power":          w.get("power"),
        "sprintSpeed":    w.get("sprintSpeed"),
        "masteryReq":     w.get("masteryReq", 0),
        "imageName":      w.get("imageName", ""),
        "wikiaThumbnail": w.get("wikiaThumbnail", ""),
        "abilities":      abilities,
    }

def trim_weapon(w):
    return {
        "name":               w.get("name", ""),
        "category":           w.get("category", ""),
        "type":               w.get("type", ""),
        "damage":             w.get("totalDamage") or w.get("damage"),
        "criticalChance":     w.get("criticalChance"),
        "criticalMultiplier": w.get("criticalMultiplier"),
        "procChance":         w.get("statusChance") or w.get("procChance"),
        "fireRate":           w.get("fireRate"),
        "magazine":           w.get("magazine"),
        "masteryReq":         w.get("masteryReq", 0),
        "imageName":          w.get("imageName", ""),
        "wikiaThumbnail":     w.get("wikiaThumbnail", ""),
        "damageTypes":        w.get("damageTypes", {}),
    }

def trim_mod(m):
    return {
        "name":           m.get("name", ""),
        "type":           m.get("compatName", "") or m.get("type", ""),
        "polarity":       m.get("polarity", ""),
        "rarity":         m.get("rarity", ""),
        "baseDrain":      m.get("baseDrain", 0),
        "fusionLimit":    m.get("fusionLimit", 0),
        "tradable":       m.get("tradable", False),
        "imageName":      m.get("imageName", ""),
        "wikiaThumbnail": m.get("wikiaThumbnail", ""),
        "levelStats":     m.get("levelStats", []),
    }

def dedupe_sort(items):
    seen, out = set(), []
    for item in items:
        n = item.get("name", "")
        if n and n not in seen:
            seen.add(n); out.append(item)
    return sorted(out, key=lambda x: x["name"])

# ── Fetch ──────────────────────────────────────────────────────
print("=" * 55)
print("TENNO FRAME — Data Fetcher")
print("=" * 55)

wf_raw = fetch(f"{BASE}/warframes?language=en", "warframes")
wp_raw = fetch(f"{BASE}/weapons?language=en",   "weapons  ")
mo_raw = fetch(f"{BASE}/mods?language=en",      "mods     ")

if not any([wf_raw, wp_raw, mo_raw]):
    print("\nAll fetches failed — keeping existing data.")
    sys.exit(0)  # exit 0 so Netlify build doesn't fail

# ── Process ────────────────────────────────────────────────────
warframes = dedupe_sort([trim_warframe(w) for w in wf_raw if w.get("name")])

CATS = {"Primary", "Secondary", "Melee"}
weapons = dedupe_sort([
    trim_weapon(w) for w in wp_raw
    if w.get("name") and w.get("category") in CATS
])

mods = dedupe_sort([trim_mod(m) for m in mo_raw if m.get("name") and m.get("polarity")])

print(f"\nProcessed: {len(warframes)} warframes  {len(weapons)} weapons  {len(mods)} mods")

# ── Build JS data string ───────────────────────────────────────
data_iife = (
    "(function(){\n"
    "  if(window.TF_DATA) return;\n"
    "  window.TF_DATA = {\n"
    f"    warframes: {json.dumps(warframes, separators=(',',':'))},\n"
    f"    weapons:   {json.dumps(weapons,   separators=(',',':'))},\n"
    f"    mods:      {json.dumps(mods,      separators=(',',':'))}\n"
    "  };\n"
    "  window._usingStaticData = true;\n"
    "})();"
)

# ── Write tennoframe_data.js ───────────────────────────────────
js_content = (
    "/* TENNO FRAME — Live data. Re-run fetch_data.py to update. */\n"
    "window.TF_DATA = {\n"
    f"  warframes: {json.dumps(warframes, separators=(',',':'))},\n"
    f"  weapons:   {json.dumps(weapons,   separators=(',',':'))},\n"
    f"  mods:      {json.dumps(mods,      separators=(',',':'))}\n"
    "};\n"
)
with open("tennoframe_data.js", "w", encoding="utf-8") as f:
    f.write(js_content)
print(f"Written: tennoframe_data.js  ({len(js_content.encode())//1024}KB)")

# ── Inject into index.html ─────────────────────────────────────
html_path = "index.html"
if os.path.exists(html_path):
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    # Replace the inline-data script block content
    # Pattern: <script id="inline-data">...anything...</script>
    pattern = r'(<script id="inline-data">)(.*?)(</script>)'

    def _replace(match):
        return match.group(1) + '\n' + data_iife + '\n' + match.group(3)

    new_html, n = re.subn(pattern, _replace, html, flags=re.DOTALL)

    if n:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(new_html)
        print(f"Injected data into index.html  ({len(new_html.encode())//1024}KB)")
    else:
        print("WARNING: Could not find inline-data script block in index.html")
else:
    print("WARNING: index.html not found — only tennoframe_data.js was written")

print("\nBuild complete.")
