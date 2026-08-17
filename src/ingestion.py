
import feedparser, re
from urllib.parse import quote

QUERIES=[
"FMCG acquisition investment","consumer goods M&A acquisition",
"FMCG acquisition India","personal care acquisition India",
"beauty brand acquisition India","packaged food acquisition India",
"D2C brand acquisition India","consumer brand funding India",
"FMCG private equity investment","snacking brand acquisition India"]

def fetch_latest_articles(days=7):
    out=[]; seen=set()
    for q in QUERIES:
        url="https://news.google.com/rss/search?q="+quote(f"{q} when:{days}d")+"&hl=en-IN&gl=IN&ceid=IN:en"
        feed=feedparser.parse(url)
        for e in feed.entries:
            u=e.get("link",""); title=e.get("title","").strip()
            if not u or not title or u in seen: continue
            seen.add(u)
            out.append({"url":u,"title":title,
                        "summary":re.sub("<[^>]+>"," ",e.get("summary","")),
                        "published":e.get("published",""),
                        "source":e.get("source",{}).get("title","Unknown")})
    return out
