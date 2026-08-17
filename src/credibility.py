TIERS = {
    "reuters": 1.00, "economic times": 0.95, "economictimes": 0.95,
    "business standard": 0.95, "mint": 0.90, "moneycontrol": 0.90,
    "financial express": 0.90, "marico": 1.00, "loreal": 1.00,
    "wipro": 1.00, "unilever": 1.00, "reliance": 1.00,
    "convergent finance": 1.00, "et retail": 0.95
}
def score_source(source):
    s = (source or "").lower()
    for name, score in TIERS.items():
        if name in s: return score
    return 0.70
