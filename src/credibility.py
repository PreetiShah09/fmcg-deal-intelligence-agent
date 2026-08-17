
TIERS={"reuters":1.0,"economictimes":.95,"business standard":.95,"mint":.90,
"moneycontrol":.90,"financial express":.90,"marico":1.0,"loreal":1.0,
"wipro":1.0,"unilever":1.0,"reliance":1.0,"cci":1.0}
def score_source(source):
    s=(source or "").lower()
    for k,v in TIERS.items():
        if k in s:return v
    return .60
