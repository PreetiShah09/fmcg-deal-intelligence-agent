
import re

DEAL = {
    "acquisition": 5, "acquire": 5, "acquired": 5, "acquires": 5,
    "purchase": 5, "purchases": 5, "buy": 5, "buys": 5,
    "merger": 5, "buyout": 5, "takeover": 5, "stake": 4,
    "investment": 4, "invests": 4, "funding": 4, "raises": 4,
    "raised": 4, "m&a": 5, "deal": 3, "transaction": 3
}

# Require actual FMCG/CPG product/category evidence.
FMCG = {
    "fmcg": 6, "consumer packaged goods": 6, "consumer goods": 5,
    "food": 4, "beverage": 4, "snack": 4, "snacking": 4,
    "packaged food": 5, "nutrition": 3, "supplement": 5,
    "wellness": 4, "personal care": 5, "beauty": 5,
    "cosmetics": 5, "skincare": 5, "haircare": 5, "grooming": 4,
    "home care": 5, "household products": 5, "hygiene": 4,
    "dairy": 4, "grocery": 4, "pet care": 4, "consumer health": 5,
    "d2c": 3, "direct-to-consumer": 3, "brand": 1
}

# Explicit non-FMCG categories. These are strong negative signals.
NON_FMCG = {
    "fintech": 8, "financial services": 8, "credit management": 8,
    "banking": 8, "insurance": 8, "saas": 8, "software": 7,
    "enterprise software": 8, "edtech": 8, "real estate": 8,
    "property": 7, "infrastructure": 7, "construction": 7,
    "industrial": 7, "manufacturing": 5, "landscaping": 8,
    "landscape": 7, "logistics": 7, "cybersecurity": 8,
    "outdoor living products": 7, "steel": 6
}

NOISE = {
    "share price": 3, "stock price": 3, "quarterly results": 3,
    "earnings": 3, "commodity prices": 3, "ipo listing": 3,
    "revenue growth": 2, "profit rises": 2
}

def norm(x):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", (x or "").lower())).strip()

def relevance(title, summary):
    text = norm(f"{title} {summary}")
    deal_score = sum(v for k,v in DEAL.items() if k in text)
    fmcg_score = sum(v for k,v in FMCG.items() if k in text)
    non_fmcg_score = sum(v for k,v in NON_FMCG.items() if k in text)
    noise_score = sum(v for k,v in NOISE.items() if k in text)

    raw = max(0, deal_score + fmcg_score - non_fmcg_score - noise_score)
    return round(min(1.0, raw / 20.0), 3)

def is_fmcg(title, summary):
    text = norm(f"{title} {summary}")
    positive = sum(v for k,v in FMCG.items() if k in text)
    negative = sum(v for k,v in NON_FMCG.items() if k in text)
    return positive >= 4 and positive > negative

def deal_type(text):
    t = norm(text)
    if "merger" in t:
        return "Merger"
    if any(x in t for x in ["acquisition","acquire","acquired","acquires","purchase","purchases","buyout","takeover","buy ","buys"]):
        return "Acquisition"
    if "majority stake" in t:
        return "Majority stake"
    if "stake" in t:
        return "Stake purchase"
    if any(x in t for x in ["funding","raises","raised","investment","invests"]):
        return "Investment"
    return "Other"
