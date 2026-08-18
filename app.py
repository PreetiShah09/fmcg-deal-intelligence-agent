import io
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(str(Path(__file__).parent / "src"))

from ingestion import fetch_latest_articles
from pipeline import run_pipeline, load_state, save_state
from newsletter import generate_newsletter

st.set_page_config(
    page_title="FMCG Deal Intelligence",
    page_icon="📰",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    .app-subtitle {color:#667085; margin-top:-10px; margin-bottom:24px;}
    .section-note {color:#667085; font-size:0.92rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("FMCG Deal Intelligence")
st.markdown(
    '<div class="app-subtitle">On-demand public-source screen for FMCG M&A and investment activity</div>',
    unsafe_allow_html=True,
)

state = load_state()

with st.sidebar:
    st.header("Screen settings")
    lookback = st.slider("Look-back window (days)", 1, 30, 7)
    relevance_threshold = st.slider("Relevance threshold", 0.0, 1.0, 0.35, 0.05)
    credibility_threshold = st.slider("Credibility threshold", 0.0, 1.0, 0.60, 0.05)

    st.caption(
        "**Refresh Now** scans the latest public sources and processes only unseen articles. "
        "Existing tracked deals are retained."
    )

    if st.button("🗑 Reset Deal Store", use_container_width=True):
        state = {
            "articles": [],
            "deals": [],
            "trace": [],
            "stats": {},
            "last_refresh": None,
        }
        save_state(state)
        st.success("Deal store cleared. Click Refresh Now to start a fresh screen.")
        st.rerun()

refresh = st.button("🔄 Refresh Now", type="primary", use_container_width=True)

if refresh:
    with st.status("Running FMCG intelligence pipeline...", expanded=True) as status:
        st.write("1/6 — Ingesting latest public articles")
        articles = fetch_latest_articles(lookback)
        st.write(f"Found {len(articles)} candidate articles.")

        st.write("2/6 — Cleaning and normalising")
        st.write("3/6 — Scoring FMCG deal relevance")
        st.write("4/6 — Checking source credibility")
        st.write("5/6 — Matching deals and removing near-duplicates")

        result = run_pipeline(
            articles,
            state,
            relevance_threshold=relevance_threshold,
            credibility_threshold=credibility_threshold,
        )

        st.write("6/6 — Regenerating newsletter")
        result["last_refresh"] = datetime.now().astimezone().strftime("%d %b %Y, %H:%M %Z")
        save_state(result)
        state = result
        status.update(label="Pipeline complete", state="complete")

st.markdown(f"**Last refreshed:** {state.get('last_refresh') or 'Not yet run'}")

stats = state.get("stats", {})
metrics = [
    ("Articles scanned", stats.get("articles_scanned", 0)),
    ("New articles", stats.get("new_articles", 0)),
    ("FMCG-relevant", stats.get("current_relevant_articles", stats.get("relevant_articles", 0))),
    ("Duplicates removed", stats.get("duplicates_removed", 0)),
    ("New deals", stats.get("new_deals", 0)),
    ("Deals tracked", len(state.get("deals", []))),
]

cols = st.columns(6)
for col, (label, value) in zip(cols, metrics):
    col.metric(label, value)


def deal_dataframe(deals):
    rows = []
    for deal in deals:
        value = deal.get("deal_value") or {}
        value_display = "Undisclosed"
        if value:
            value_display = f"{value.get('currency', '')}{value.get('amount', '')}{value.get('unit', '')}"
        rows.append({
            "Deal ID": deal.get("deal_id", ""),
            "Buyer / Investor": deal.get("buyer", ""),
            "Target": deal.get("target", ""),
            "Deal Type": deal.get("deal_type", ""),
            "Status": deal.get("status", ""),
            "Sector": deal.get("sector", ""),
            "Value": value_display,
            "Confidence": deal.get("confidence", ""),
            "Sources": len(deal.get("sources", [])),
            "Last Updated": deal.get("last_updated", ""),
        })
    return pd.DataFrame(rows)


def article_dataframe(articles):
    df = pd.DataFrame(articles)
    wanted = [
        "published", "title", "source", "fmcg_pass",
        "relevance_score", "credibility_score", "final_score", "deal_id", "url"
    ]
    display_cols = [c for c in wanted if c in df.columns]
    if "final_score" in df.columns:
        df = df.sort_values("final_score", ascending=False)
    return df[display_cols] if display_cols else df


def workbook_bytes(deals_df, articles_df, newsletter_text):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        deals_df.to_excel(writer, index=False, sheet_name="Deal Tracker")
        articles_df.to_excel(writer, index=False, sheet_name="Article Evidence")
        pd.DataFrame({"Newsletter": newsletter_text.splitlines()}).to_excel(
            writer, index=False, sheet_name="Newsletter"
        )
    output.seek(0)
    return output.getvalue()


deals = state.get("deals", [])
articles = state.get("articles", [])
deals_df = deal_dataframe(deals)
articles_df = article_dataframe(articles)
newsletter_text = generate_newsletter(deals)

# Export package is generated from the same persistent state shown in the UI.
json_bytes = json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8")
deals_csv = deals_df.to_csv(index=False).encode("utf-8-sig")
articles_csv = articles_df.to_csv(index=False).encode("utf-8-sig")
workbook = None
try:
    workbook = workbook_bytes(deals_df, articles_df, newsletter_text)
except Exception:
    # The app remains usable even if the optional Excel writer is unavailable.
    workbook = None


tab_newsletter, tab_deals, tab_articles, tab_trace = st.tabs(
    ["📰 Newsletter", "💼 Deal Monitor", "🔎 Article Evidence", "⚙️ Agent Trace"]
)

with tab_newsletter:
    if deals:
        st.markdown("### Investment brief")
        st.markdown(
            '<div class="section-note">A ranked, skimmable view of the highest-priority tracked transactions.</div>',
            unsafe_allow_html=True,
        )
        st.markdown(newsletter_text)

        st.divider()
        st.markdown("**Export this screen**")
        export_cols = st.columns(4)
        with export_cols[0]:
            st.download_button(
                "Download Newsletter",
                newsletter_text,
                file_name="FMCG_Deal_Intelligence_Newsletter.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with export_cols[1]:
            st.download_button(
                "Download Deals CSV",
                deals_csv,
                file_name="fmcg_deal_tracker.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with export_cols[2]:
            st.download_button(
                "Download Articles CSV",
                articles_csv,
                file_name="fmcg_article_evidence.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with export_cols[3]:
            if workbook:
                st.download_button(
                    "Download Excel Workbook",
                    workbook,
                    file_name="FMCG_Deal_Intelligence.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            else:
                st.caption("Excel export requires openpyxl.")
    else:
        st.info("Click Refresh Now to run the live public-news screen.")

with tab_deals:
    if deals:
        st.dataframe(deals_df, use_container_width=True, hide_index=True)
        st.download_button(
            "Download Deal Tracker CSV",
            deals_csv,
            file_name="fmcg_deal_tracker.csv",
            mime="text/csv",
        )
    else:
        st.info("No confirmed deal records yet.")

with tab_articles:
    if articles:
        st.dataframe(articles_df, use_container_width=True, hide_index=True)
        st.download_button(
            "Download Article Evidence CSV",
            articles_csv,
            file_name="fmcg_article_evidence.csv",
            mime="text/csv",
        )
    else:
        st.info("No articles yet.")

with tab_trace:
    trace = state.get("trace", [])
    if trace:
        for line in trace:
            st.write(line)
    else:
        st.info("Run Refresh Now to see the agent trace.")

st.divider()
st.caption(
    "Method note: public-source discovery is not guaranteed to be exhaustive. "
    "Credibility is a source-quality heuristic, not independent fact verification."
)
