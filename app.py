
import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from ingestion import fetch_latest_articles
from pipeline import run_pipeline, load_state, save_state
from newsletter import generate_newsletter

st.set_page_config(
    page_title="FMCG Deal Intelligence",
    page_icon="📰",
    layout="wide",
)

st.title("📰 FMCG Deal Intelligence")
st.caption(
    "On-demand live screen of publicly available FMCG M&A and investment activity"
)

state = load_state()

with st.sidebar:
    st.header("Screen settings")

    lookback = st.slider(
        "Look-back window (days)", 1, 30, 7
    )

    relevance_threshold = st.slider(
        "Relevance threshold", 0.0, 1.0, 0.35, 0.05
    )

    credibility_threshold = st.slider(
        "Credibility threshold", 0.0, 1.0, 0.60, 0.05
    )

    st.caption(
        "Only FMCG-relevant transactions with clear deal language "
        "enter Deal Monitor."
    )

    if st.button("🗑 Reset Deal Store"):
        state = {
            "articles": [],
            "deals": [],
            "trace": [],
            "stats": {},
            "last_refresh": None,
        }
        save_state(state)
        st.success("Deal store reset. Click Refresh Now.")

refresh = st.button(
    "🔄 Refresh Now",
    type="primary",
    use_container_width=True,
)

if refresh:
    with st.status(
        "Running FMCG intelligence pipeline...",
        expanded=True,
    ) as status:

        st.write("1/6 — Ingesting latest public articles")
        articles = fetch_latest_articles(lookback)
        st.write(f"Found {len(articles)} candidate articles.")

        st.write("2/6 — Cleaning and normalising")

        result = run_pipeline(
            articles,
            state,
            relevance_threshold=relevance_threshold,
            credibility_threshold=credibility_threshold,
        )

        st.write("3/6 — Scoring FMCG deal relevance")
        st.write("4/6 — Checking source credibility")
        st.write("5/6 — Matching deals and removing near-duplicates")
        st.write("6/6 — Regenerating newsletter")

        result["last_refresh"] = (
            datetime.now()
            .astimezone()
            .strftime("%d %b %Y, %H:%M %Z")
        )

        save_state(result)
        state = result

        status.update(
            label="Pipeline complete",
            state="complete",
        )

st.markdown(
    f"**Last refreshed:** "
    f"{state.get('last_refresh') or 'Not yet run'}"
)

stats = state.get("stats", {})

metrics = [
    ("Articles scanned", stats.get("articles_scanned", 0)),
    ("New articles", stats.get("new_articles", 0)),
    ("FMCG-relevant", stats.get("relevant_articles", 0)),
    ("Duplicates removed", stats.get("duplicates_removed", 0)),
    ("New deals", stats.get("new_deals", 0)),
    ("Deals tracked", len(state.get("deals", []))),
]

cols = st.columns(6)

for col, (label, value) in zip(cols, metrics):
    col.metric(label, value)

tab_newsletter, tab_deals, tab_articles, tab_trace = st.tabs(
    [
        "📰 Newsletter",
        "💼 Deal Monitor",
        "🔎 Article Evidence",
        "⚙️ Agent Trace",
    ]
)

with tab_newsletter:
    deals = state.get("deals", [])

    if deals:
        st.markdown(generate_newsletter(deals))
    else:
        st.info("Click **Refresh Now** to run the live public-news screen.")

with tab_deals:
    deals = state.get("deals", [])

    if deals:
        rows = []

        for deal in deals:
            value = deal.get("deal_value")
            value_display = "Undisclosed"

            if value:
                value_display = (
                    f"{value.get('currency', '')}"
                    f"{value.get('amount', '')}"
                    f"{value.get('unit', '')}"
                )

            rows.append({
                "Buyer / Investor": deal.get("buyer", ""),
                "Target": deal.get("target", ""),
                "Deal Type": deal.get("deal_type", ""),
                "Status": deal.get("status", ""),
                "Value": value_display,
                "Confidence": deal.get("confidence", ""),
                "Sources": len(deal.get("sources", [])),
                "Last Updated": deal.get("last_updated", ""),
            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info("No confirmed deal records yet.")

with tab_articles:
    articles = state.get("articles", [])

    if articles:
        df = pd.DataFrame(articles)

        wanted = [
            "published",
            "title",
            "source",
            "fmcg_pass",
            "relevance_score",
            "credibility_score",
            "final_score",
            "deal_id",
            "url",
        ]

        display_cols = [
            c for c in wanted
            if c in df.columns
        ]

        if "final_score" in df.columns:
            df = df.sort_values(
                "final_score",
                ascending=False,
            )

        st.dataframe(
            df[display_cols],
            use_container_width=True,
            hide_index=True,
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
