import json, sys, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding="utf-8")
q = sys.argv[1]; flt = sys.argv[2] if len(sys.argv) > 2 else ""
p = {"search": q, "per-page": "15", "mailto": "audit@example.org"}
if flt: p["filter"] = flt
url = "https://api.openalex.org/works?" + urllib.parse.urlencode(p)
d = json.load(urllib.request.urlopen(url, timeout=60))
print("Q=%r filter=%r count=%d" % (q, flt, d["meta"]["count"]))
for w in d["results"]:
    v = (w.get("primary_location") or {}).get("source") or {}
    print("  %s | %s | %s | %s" % (w.get("publication_year"), (w.get("title") or "")[:110], (v.get("display_name") or "")[:40], w.get("doi")))
