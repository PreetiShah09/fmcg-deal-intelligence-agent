
import json,re
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
from scoring import norm,relevance,deal_type
from credibility import score_source

STATE=Path(__file__).parent.parent/"data/state.json"
def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"articles":[],"deals":[],"trace":[],"stats":{},"last_refresh":None}
def save_state(s): STATE.write_text(json.dumps(s,ensure_ascii=False,indent=2))
def run_pipeline(incoming,state):
    old={a["url"] for a in state.get("articles",[]) if a.get("url")}
    new=[a for a in incoming if a.get("url") not in old]
    scored=[]
    for a in new:
        r=relevance(a["title"],a["summary"]); c=score_source(a["source"])
        a.update(relevance_score=r,credibility_score=c,final_score=round(.65*r+.35*c,3),deal_type=deal_type(a["title"]+" "+a["summary"]))
        scored.append(a)
    relevant=[a for a in scored if a["relevance_score"]>=.50 and a["credibility_score"]>=.70]
    unique=[]
    for a in sorted(relevant,key=lambda x:x["final_score"],reverse=True):
        if any(SequenceMatcher(None,norm(a["title"]),norm(x["title"])).ratio()>=.86 for x in unique): continue
        unique.append(a)
    deals=state.get("deals",[]); new_deals=0; updated=0
    for a in unique:
        parts=re.split(r"\s(?:acquires|acquire|buys|to acquire|invests in|agrees to acquire)\s",a["title"],flags=re.I)
        if len(parts)<2: continue
        buyer,target=parts[0].strip(" -:"),parts[1].strip(" -:")
        fp=norm(buyer+" "+target+" "+a["deal_type"])
        match=None
        for d in deals:
            if SequenceMatcher(None,fp,d.get("fingerprint","")).ratio()>=.78: match=d; break
        if match:
            match.setdefault("sources",[]).append(a["url"]); match["last_updated"]=a.get("published",""); updated+=1
        else:
            d={"deal_id":f"DEAL-{len(deals)+1:04d}","buyer":buyer,"target":target,
               "fingerprint":fp,"deal_type":a["deal_type"],"sector":"FMCG / Consumer",
               "status":"Reported / Announced","deal_value_inr_cr":None,
               "confidence":"High" if a["final_score"]>=.82 else "Medium",
               "summary":re.sub(r"\s+"," ",a["summary"]).strip()[:400],
               "sources":[a["url"]],"last_updated":a.get("published","")}
            deals.append(d); a["deal_id"]=d["deal_id"]; new_deals+=1
    trace=[
        f"✓ Retrieved {len(incoming)} public articles",
        f"✓ {len(new)} new since last refresh",
        f"✓ {len(relevant)} passed relevance + credibility",
        f"✓ {len(relevant)-len(unique)} near-duplicates removed",
        f"✓ {new_deals} new deals detected",
        f"✓ {updated} existing deals updated",
        f"✓ Newsletter regenerated from {len(deals)} tracked deals"]
    amap={a.get("url"):a for a in state.get("articles",[]) if a.get("url")}
    for a in scored: amap[a["url"]]=a
    return {"articles":list(amap.values()),"deals":deals,"trace":trace,
            "stats":{"articles_scanned":len(incoming),"new_articles":len(new),
                     "relevant_articles":len(relevant),"duplicates_removed":len(relevant)-len(unique),
                     "new_deals":new_deals,"updated_deals":updated}}
