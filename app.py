import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(str(Path(__file__).parent / "src"))

from ingestion import fetch_latest_articles
from pipeline import run_pipeline, load_state, save_state
from newsletter import generate_newsletter, dedupe_deals

st.set_page_config(
    page_title="FMCG Deal Intelligence",
    page_icon="📰",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --navy: #183B56;
        --teal: #1F8A8A;
        --teal-soft: #EAF7F6;
        --sand: #F7F4EE;
        --ink: #233044;
        --muted: #6B7280;
        --line: #D9E2EA;
    }

    .stApp { background: var(--sand); }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px; }
    h1, h2, h3 { color: var(--navy) !important; }
    h1 { letter-spacing: -0.03em; }
    h2 { margin-top: 1.6rem; }
    .app-subtitle { color: var(--muted); margin-top: -10px; margin-bottom: 24px; }
    .section-note { color: var(--muted); font-size: 0.92rem; }

    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid var(--line);
        border-top: 4px solid var(--teal);
        border-radius: 10px;
        padding: 12px 14px;
        box-shadow: 0 2px 8px rgba(24,59,86,0.05);
    }
    div[data-testid="stMetricLabel"] { color: var(--muted); }
    div[data-testid="stMetricValue"] { color: var(--navy); }

    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] { color: var(--navy); font-weight: 600; }
    .stTabs [aria-selected="true"] { color: var(--teal) !important; }

    .stButton > button[kind="primary"] {
        background: var(--navy);
        border-color: var(--navy);
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--teal);
        border-color: var(--teal);
    }

    .stMarkdown blockquote {
        border-left: 4px solid var(--teal);
        background: var(--teal-soft);
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
    }
    .stMarkdown table {
        background: white;
        border-radius: 8px;
        overflow: hidden;
    }
    .stMarkdown th { background: #EAF0F5 !important; color: var(--navy) !important; }
    .stMarkdown td, .stMarkdown th { border-color: var(--line) !important; }
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



deals = dedupe_deals(state.get("deals", []))
articles = state.get("articles", [])
deals_df = deal_dataframe(deals)
articles_df = article_dataframe(articles)
newsletter_text = generate_newsletter(deals)

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

    else:
        st.info("Click Refresh Now to run the live public-news screen.")

with tab_deals:
    if deals:
        st.dataframe(deals_df, use_container_width=True, hide_index=True)
    else:
        st.info("No confirmed deal records yet.")

with tab_articles:
    if articles:
        st.dataframe(articles_df, use_container_width=True, hide_index=True)
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
