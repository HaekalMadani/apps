import json, sys, urllib.request, urllib.parse, re
sys.stdout.reconfigure(encoding="utf-8")
doi = sys.argv[1]; pat = re.compile(sys.argv[2], re.I) if len(sys.argv) > 2 else None
w = json.load(urllib.request.urlopen("https://api.openalex.org/works/doi:" + doi + "?mailto=audit@example.org", timeout=60))
wid = w["id"].rsplit("/", 1)[1]
print("SEED %s | %s | cited_by=%s" % (w.get("publication_year"), w.get("title"), w.get("cited_by_count")))
cursor = "*"; n = 0; kept = 0
while cursor:
    p = {"filter": "cites:" + wid, "per-page": "200", "cursor": cursor, "mailto": "audit@example.org", "select": "title,publication_year,doi"}
    d = json.load(urllib.request.urlopen("https://api.openalex.org/works?" + urllib.parse.urlencode(p), timeout=60))
    for r in d["results"]:
        n += 1
        t = r.get("title") or ""
        if pat is None or pat.search(t):
            kept += 1; print("  %s | %s | %s" % (r.get("publication_year"), t[:120], r.get("doi")))
    cursor = d["meta"].get("next_cursor")
    if not d["results"]: break
print("  scanned=%d kept=%d" % (n, kept))
