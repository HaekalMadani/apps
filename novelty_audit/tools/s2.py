import json, sys, time, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding="utf-8")
q = sys.argv[1]
p = {"query": q, "limit": "15", "fields": "title,year,venue,externalIds,citationCount"}
url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode(p)
for attempt in range(4):
    try:
        d = json.load(urllib.request.urlopen(url, timeout=60))
        break
    except Exception as e:
        if attempt == 3:
            print("Q=%r ERROR %s" % (q, e)); sys.exit(0)
        time.sleep(5 * (attempt + 1))
print("Q=%r total=%s" % (q, d.get("total")))
for w in d.get("data", []):
    doi = (w.get("externalIds") or {}).get("DOI") or (w.get("externalIds") or {}).get("ArXiv")
    print("  %s | %s | %s | %s | c=%s" % (w.get("year"), (w.get("title") or "")[:110], (w.get("venue") or "")[:35], doi, w.get("citationCount")))
