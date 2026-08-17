
import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent/"src"))
from ingestion import fetch_latest_articles
from pipeline import run_pipeline,load_state,save_state,STATE_FILE
from newsletter import generate_newsletter

st.set_page_config(page_title="FMCG Deal Intelligence",page_icon="📰",layout="wide")
st.title("📰 FMCG Deal Intelligence")
st.caption("On-demand live screen of publicly available FMCG M&A and investment activity")

with st.sidebar:
    st.header("Screen settings")
    lookback=st.slider("Look-back window (days)",1,30,7)
    relevance_threshold=st.slider("Relevance threshold",0.0,1.0,0.35,0.05)
    credibility_threshold=st.slider("Credibility threshold",0.0,1.0,0.60,0.05)
    st.caption("Only FMCG-relevant transactions with clear deal language enter Deal Monitor.")
    if st.button("Reset Deal Store"):
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        st.rerun()

state=load_state()

refresh=st.button("🔄 Refresh Now",type="primary",use_container_width=True)

if refresh:
    with st.status("Running FMCG intelligence pipeline...",expanded=True) as status:
        st.write("1/6 — Ingesting latest public articles")
        articles=fetch_latest_articles(lookback)
        st.write(f"Found {len(articles)} candidate articles.")
        st.write("2/6 — Cleaning and normalising")
        result=run_pipeline(articles,state,relevance_threshold,credibility_threshold)
        st.write("3/6 — FMCG + deal relevance scoring")
        st.write("4/6 — Source credibility checks")
        st.write("5/6 — Article/deal de-duplication")
        st.write("6/6 — Newsletter regeneration")
        result["last_refresh"]=datetime.now().astimezone().strftime("%d %b %Y, %H:%M %Z")
        save_state(result); state=result
        status.update(label="Pipeline complete",state="complete")

st.markdown(f"**Last refreshed:** {state.get('last_refresh') or 'Not yet run'}")

stats=state.get("stats",{})
metrics=[("Articles scanned",stats.get("articles_scanned",0)),("New articles",stats.get("new_articles",0)),
("Relevant",stats.get("relevant_articles",0)),("Duplicates removed",stats.get("duplicates_removed",0)),
("New deals",stats.get("new_deals",0)),("Deals tracked",len(state.get("deals",[])))]
cols=st.columns(6)
for c,(label,value) in zip(cols,metrics): c.metric(label,value)

tabs=st.tabs(["📰 Newsletter","💼 Deal Monitor","🔎 Article Evidence","⚙️ Agent Trace"])
with tabs[0]:
    deals=state.get("deals",[])
    st.markdown(generate_newsletter(deals) if deals else "Click **Refresh Now** to run the live public-news screen.")
with tabs[1]:
    deals=state.get("deals",[])
    if deals:
        rows=[{"Buyer / Investor":d.get("buyer",""),"Target":d.get("target",""),"Deal Type":d.get("deal_type",""),
               "Sector":d.get("sector",""),"Value (₹ Cr)":d.get("deal_value_inr_cr",""),
               "Confidence":d.get("confidence",""),"Sources":len(d.get("sources",[])),"Last Updated":d.get("last_updated","")} for d in deals]
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    else: st.info("No confirmed deal records yet.")
with tabs[2]:
    articles=state.get("articles",[])
    if articles:
        df=pd.DataFrame(articles)
        wanted=["published","title","source","fmcg_pass","relevance_score","credibility_score","final_score","deal_id","url"]
        cols=[c for c in wanted if c in df.columns]
        st.dataframe(df[cols].sort_values("final_score",ascending=False),use_container_width=True,hide_index=True)
    else: st.info("No articles yet.")
with tabs[3]:
    for line in state.get("trace",[]): st.write(line)
    if not state.get("trace"): st.info("Run Refresh Now to see the agent trace.")

st.divider()
st.caption("Credibility is a source-quality heuristic, not independent fact verification. Public-source discovery is not guaranteed to be exhaustive.")
