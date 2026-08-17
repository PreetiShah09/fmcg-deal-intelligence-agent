
import re

DEAL = {
    "acquisition": 5, "acquire": 5, "acquired": 5, "acquires": 5,
    "merger": 5, "buyout": 5, "takeover": 5, "stake": 4,
    "investment": 4, "invests": 4, "funding": 4, "raises": 4,
    "raised": 4, "m&a": 5, "deal": 3, "transaction": 3
}
FMCG = {
    "fmcg": 5, "consumer goods": 5, "consumer brand": 4,
    "personal care": 4, "beauty": 4, "skincare": 4, "cosmetics": 3,
    "packaged food": 4, "food brand": 4, "snack": 3, "snacking": 3,
    "beverage": 3, "home care": 4, "household": 3, "hygiene": 3,
    "grocery": 3, "d2c": 4, "direct-to-consumer": 4,
    "wellness": 3, "supplement": 3, "consumer": 2, "brand": 2
}
NOISE = {
    "share price": 2, "stock price": 2, "quarterly results": 2,
    "earnings": 2, "commodity prices": 2, "ipo listing": 2
}
def norm(x):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", (x or "").lower())).strip()
def relevance(title, summary):
    text = norm(f"{title} {summary}")
    raw = max(0, sum(v for k,v in DEAL.items() if k in text)
                 + sum(v for k,v in FMCG.items() if k in text)
                 - sum(v for k,v in NOISE.items() if k in text))
    return round(min(1.0, raw / 20.0), 3)
def deal_type(text):
    t = norm(text)
    if "merger" in t: return "Merger"
    if any(x in t for x in ["acquisition","acquire","acquired","acquires","buyout","takeover"]):
        return "Acquisition"
    if "majority stake" in t: return "Majority stake"
    if "stake" in t: return "Stake purchase"
    if any(x in t for x in ["funding","raises","raised","investment","invests"]):
        return "Investment"
    return "Other"

