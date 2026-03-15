#!/usr/bin/env python3
"""
TENNO FRAME — Data Pre-fetcher
Run this script once whenever you want to update the embedded data.
It fetches from the Warframe API, trims to only what the app needs,
and writes a ready-to-embed data file.

Requirements: pip install requests
Usage: python3 fetch_data.py
Output: tennoframe_data.js  (embed this in index.html)
"""

import requests, json, time, sys

BASE = "https://api.warframestat.us"
TIMEOUT = 30

def fetch(url, label):
    print(f"Fetching {label}...", end=" ", flush=True)
    t0 = time.time()
    r = requests.get(url, timeout=TIMEOUT, headers={"Accept-Language":"en"})
    r.raise_for_status()
    print(f"OK ({len(r.content)//1024}KB in {time.time()-t0:.1f}s)")
    return r.json()

def trim_warframe(w):
    return {
        "name":        w.get("name",""),
        "health":      w.get("health"),
        "shield":      w.get("shield"),
        "armor":       w.get("armor"),
        "power":       w.get("power"),
        "sprintSpeed": w.get("sprintSpeed"),
        "description": w.get("description",""),
        "imageName":   w.get("imageName",""),
        "wikiaThumbnail": w.get("wikiaThumbnail",""),
        "introduced":  w.get("introduced",{}).get("name","") if isinstance(w.get("introduced"),dict) else "",
        "abilities":   [{"name":a.get("name",""),"description":a.get("description","")} 
                        for a in (w.get("abilities") or [])],
    }

def trim_weapon(w):
    return {
        "name":               w.get("name",""),
        "category":           w.get("category",""),
        "type":               w.get("type",""),
        "totalDamage":        w.get("totalDamage"),
        "criticalChance":     w.get("criticalChance"),
        "criticalMultiplier": w.get("criticalMultiplier"),
        "statusChance":       w.get("statusChance"),
        "fireRate":           w.get("fireRate"),
        "magazine":           w.get("magazine"),
        "reload":             w.get("reload"),
        "noise":              w.get("noise",""),
        "masteryReq":         w.get("masteryReq"),
        "description":        w.get("description",""),
        "imageName":          w.get("imageName",""),
        "wikiaThumbnail":     w.get("wikiaThumbnail",""),
        "damageTypes":        w.get("damageTypes",{}),
    }

def trim_mod(m):
    return {
        "name":        m.get("name",""),
        "description": m.get("description",""),
        "rarity":      m.get("rarity",""),
        "compatName":  m.get("compatName",""),
        "baseDrain":   m.get("baseDrain"),
        "fusionLimit": m.get("fusionLimit"),
        "tradable":    m.get("tradable",False),
        "imageName":   m.get("imageName",""),
        "wikiaThumbnail": m.get("wikiaThumbnail",""),
        "levelStats":  m.get("levelStats",[]),
    }

try:
    wf_raw  = fetch(f"{BASE}/warframes", "warframes")
    wp_raw  = fetch(f"{BASE}/weapons",   "weapons")
    mo_raw  = fetch(f"{BASE}/mods",      "mods")
except Exception as e:
    print(f"\nERROR: {e}")
    sys.exit(1)

# Trim
warframes = [trim_warframe(w) for w in wf_raw if w.get("name")]
# Dedupe
seen = set()
warframes = [w for w in warframes if w["name"] not in seen and not seen.add(w["name"])]
warframes.sort(key=lambda x: x["name"])

weapons_raw = [trim_weapon(w) for w in wp_raw if w.get("name") and w.get("category")]
seen = set()
weapons = [w for w in weapons_raw if w["name"] not in seen and not seen.add(w["name"])]
weapons.sort(key=lambda x: x["name"])

mods_raw = [trim_mod(m) for m in mo_raw if m.get("name") and m.get("description")]
seen = set()
mods = [m for m in mods_raw if m["name"] not in seen and not seen.add(m["name"])]
mods.sort(key=lambda x: x["name"])

print(f"\nTrimmed: {len(warframes)} warframes, {len(weapons)} weapons, {len(mods)} mods")

# Write compact JS that the app picks up immediately
out = "/* TENNO FRAME — Pre-fetched data. Re-run fetch_data.py to update. */\n"
out += f"window.TF_DATA = {{\n"
out += f"  warframes: {json.dumps(warframes, separators=(',',':'))},\n"
out += f"  weapons:   {json.dumps(weapons,   separators=(',',':'))},\n"
out += f"  mods:      {json.dumps(mods,      separators=(',',':'))}\n"
out += "};\n"

with open("tennoframe_data.js","w",encoding="utf-8") as f:
    f.write(out)

size_kb = len(out.encode()) // 1024
print(f"Written: tennoframe_data.js ({size_kb}KB)")
print("\nNow run: python3 embed_data.py")
print("  — or add this to index.html head: <script src=\"tennoframe_data.js\"></script>")
