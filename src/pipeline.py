
import json
import re
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

from scoring import norm, relevance, deal_type, is_fmcg
from credibility import score_source

# V4 uses a fresh state file so old false-positive deals do not survive the fix.
STATE_FILE = Path(__file__).parent.parent / "data" / "state_v4.json"

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"articles":[],"deals":[],"trace":[],"stats":{},"last_refresh":None}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True,exist_ok=True)
    STATE_FILE.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")

def sim(a,b):
    return SequenceMatcher(None,norm(a),norm(b)).ratio()

def extract_deal(title,summary):
    t=re.sub(r"\s+"," ",title or "").strip()

    patterns=[
        (r"^(.*?)\s+(?:to\s+)?acquire(?:s|d)?\s+(.+)$","Acquisition"),
        (r"^(.*?)\s+(?:to\s+)?purchase(?:s|d)?\s+(.+)$","Acquisition"),
        (r"^(.*?)\s+(?:to\s+)?buy(?:s)?\s+(.+)$","Acquisition"),
        (r"^(.*?)\s+(?:to\s+)?take(?:s)?\s+(?:a\s+)?(?:majority\s+|minority\s+)?stake\s+in\s+(.+)$","Stake purchase"),
        (r"^(.*?)\s+(?:to\s+)?invest(?:s|ed)?\s+in\s+(.+)$","Investment"),
    ]

    for pattern,dtype in patterns:
        m=re.search(pattern,t,flags=re.I)
        if not m:
            continue

        buyer=m.group(1).strip(" -:,")
        target=m.group(2).strip(" -:")

        # Remove source/category suffixes commonly appended to headlines.
        target=re.split(r"\s+-\s+(?:PR Newswire|PR Newswire UK|citybiz|Consumer Goods Technology|ANI News|IndianWeb2|Whalesbook).*$",
                        target,flags=re.I)[0].strip()

        # Remove descriptive clause after comma when it is clearly an appositive.
        if "," in target:
            first=target.split(",")[0].strip()
            if len(first)>=3:
                target=first

        if len(buyer)<2 or len(target)<2:
            return None

        bad=("pr newswire","citybiz","consumer goods technology","indianweb2","whalesbook")
        if any(x in buyer.lower() for x in bad) or any(x in target.lower() for x in bad):
            return None

        return {"buyer":buyer,"target":target,"deal_type":dtype}

    # Funding headlines: "Target raises ... led by Investor"
    m=re.search(r"^(.+?)\s+(?:raises|raised)\s+.+?\s+(?:led|backed)\s+by\s+(.+)$",t,flags=re.I)
    if m:
        target=m.group(1).strip(" -:,")
        buyer=m.group(2).strip(" -:,")
        return {"buyer":buyer,"target":target,"deal_type":"Investment"}

    return None

def run_pipeline(incoming,state,relevance_threshold=0.35,credibility_threshold=0.60):
    old_urls={a.get("url") for a in state.get("articles",[]) if a.get("url")}
    new=[a for a in incoming if a.get("url") not in old_urls]

    scored=[]
    for a in new:
        title=a.get("title",""); summary=a.get("summary",""); source=a.get("source","")
        r=relevance(title,summary); c=score_source(source)
        a["relevance_score"]=r
        a["credibility_score"]=c
        a["final_score"]=round(.65*r+.35*c,3)
        a["deal_type"]=deal_type(f"{title} {summary}")
        a["fmcg_pass"]=is_fmcg(title,summary)
        scored.append(a)

    relevant=[a for a in scored if a["relevance_score"]>=relevance_threshold and a["credibility_score"]>=credibility_threshold and a["fmcg_pass"]]

    unique=[]; duplicates=0
    for a in sorted(relevant,key=lambda x:x["final_score"],reverse=True):
        if any(sim(a.get("title",""),x.get("title",""))>=.86 for x in unique):
            duplicates+=1
        else:
            unique.append(a)

    deals=state.get("deals",[])
    new_deals=0; updated=0; evidence_only=0

    for a in unique:
        e=extract_deal(a.get("title",""),a.get("summary",""))
        if not e:
            evidence_only+=1
            continue

        buyer,target,dtype=e["buyer"],e["target"],e["deal_type"]
        fp=norm(f"{buyer} {target} {dtype}")
        matched=None

        for d in deals:
            if sim(fp,d.get("fingerprint",""))>=.78:
                matched=d
                break

        if matched:
            if a.get("url") and a["url"] not in matched.setdefault("sources",[]):
                matched["sources"].append(a["url"])
            matched["last_updated"]=a.get("published") or datetime.now().isoformat()
            if len(matched["sources"])>=2:
                matched["confidence"]="High"
            updated+=1
        else:
            did=f"DEAL-{len(deals)+1:04d}"
            deals.append({
                "deal_id":did,"buyer":buyer,"target":target,"fingerprint":fp,
                "deal_type":dtype,"sector":"FMCG / Consumer",
                "status":"Reported / Announced","deal_value_inr_cr":None,
                "confidence":"High" if a["final_score"]>=.82 else "Medium",
                "summary":re.sub(r"\s+"," ",a.get("summary","")).strip()[:420],
                "sources":[a.get("url")],
                "last_updated":a.get("published") or datetime.now().isoformat()
            })
            a["deal_id"]=did
            new_deals+=1

    amap={a.get("url"):a for a in state.get("articles",[]) if a.get("url")}
    for a in scored:
        if a.get("url"): amap[a["url"]]=a

    trace=[
        f"✓ Retrieved {len(incoming)} public articles",
        f"✓ {len(new)} new articles since last refresh",
        f"✓ {len(relevant)} passed FMCG + relevance + credibility filters",
        f"✓ {duplicates} near-duplicate articles removed",
        f"✓ {evidence_only} relevant articles kept as evidence only",
        f"✓ {new_deals} new deals detected",
        f"✓ {updated} existing deals updated",
        f"✓ Newsletter regenerated from {len(deals)} tracked deals",
    ]

    return {
        "articles":list(amap.values()),"deals":deals,"trace":trace,
        "stats":{"articles_scanned":len(incoming),"new_articles":len(new),
                 "relevant_articles":len(relevant),"duplicates_removed":duplicates,
                 "new_deals":new_deals,"updated_deals":updated}
    }
