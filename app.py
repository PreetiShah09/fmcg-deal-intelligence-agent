
import streamlit as st
import pandas as pd
from datetime import datetime
import sys, json
from pathlib import Path
sys.path.append(str(Path(__file__).parent/"src"))
from ingestion import fetch_latest_articles
from pipeline import run_pipeline, load_state, save_state
from newsletter import generate_newsletter

st.set_page_config(page_title="FMCG Deal Intelligence", page_icon="📰", layout="wide")
st.title("📰 FMCG Deal Intelligence")
st.caption("Live public-source screen for FMCG M&A and investment activity")

state = load_state()
st.write("**Last refreshed:** " + (state.get("last_refresh") or "Not yet run"))

if st.button("🔄 Refresh Now", type="primary"):
    with st.status("Running intelligence pipeline...", expanded=True) as s:
        st.write("1/6 Ingesting latest public articles")
        articles = fetch_latest_articles(7)
        st.write(f"2/6 Cleaning {len(articles)} articles")
        result = run_pipeline(articles, state)
        st.write("3/6 Scoring FMCG deal relevance")
        st.write("4/6 Checking source credibility")
        st.write("5/6 Matching deals + removing near-duplicates")
        st.write("6/6 Regenerating newsletter")
        result["last_refresh"] = datetime.now().astimezone().strftime("%d %b %Y, %H:%M %Z")
        save_state(result)
        state = result
        s.update(label="Pipeline complete", state="complete")

stats = state.get("stats", {})
cols = st.columns(6)
for c,(label,key) in zip(cols,[
    ("Articles scanned","articles_scanned"),("New articles","new_articles"),
    ("Relevant","relevant_articles"),("Duplicates removed","duplicates_removed"),
    ("New deals","new_deals"),("Deals tracked",None)]):
    c.metric(label, len(state.get("deals",[])) if key is None else stats.get(key,0))

tab1,tab2,tab3,tab4 = st.tabs(["📰 Newsletter","💼 Deal Monitor","🔎 Article Evidence","⚙️ Agent Trace"])

with tab1:
    st.markdown(generate_newsletter(state.get("deals",[])) if state.get("deals") else
                "Click **Refresh Now** to run the live public-news screen.")

with tab2:
    rows=[]
    for d in state.get("deals",[]):
        rows.append({k:d.get(k,"") for k in
            ["status","buyer","target","deal_type","sector","deal_value_inr_cr","confidence","last_updated"]})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True) if rows else st.info("No deals yet.")

with tab3:
    df=pd.DataFrame(state.get("articles",[]))
    if not df.empty:
        cols=[c for c in ["published","title","source","relevance_score","credibility_score","final_score","deal_id","url"] if c in df]
        st.dataframe(df[cols].sort_values("final_score",ascending=False),use_container_width=True,hide_index=True)
    else: st.info("No articles yet.")

with tab4:
    st.code("\n".join(state.get("trace",[])) if state.get("trace") else "Run Refresh Now to see the agent trace.")
st.caption("Credibility is a source-quality heuristic, not independent fact verification. Public-source discovery is not guaranteed to be exhaustive.")
