import json, sys, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding="utf-8")
for q in sys.argv[1:]:
    if q.startswith("10."):
        url = "https://api.crossref.org/works/" + urllib.parse.quote(q)
        try: items = [json.load(urllib.request.urlopen(url, timeout=60))["message"]]
        except Exception as e: print("DOI", q, "ERR", e); continue
    else:
        url = "https://api.crossref.org/works?" + urllib.parse.urlencode({"query.bibliographic": q, "rows": "3", "mailto": "audit@example.org"})
        items = json.load(urllib.request.urlopen(url, timeout=60))["message"]["items"]
    print("Q:", q)
    for it in items:
        au = ", ".join("%s %s" % (a.get("given",""), a.get("family","")) for a in it.get("author", [])[:8])
        yr = (it.get("issued",{}).get("date-parts") or [[None]])[0][0]
        print("   %s | %s | %s | %s | vol %s(%s) %s | %s" % (yr, (it.get("title") or [""])[0][:120], au, (it.get("container-title") or [""])[0][:50], it.get("volume"), it.get("issue"), it.get("page"), it.get("DOI")))
