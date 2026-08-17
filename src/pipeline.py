import json
import re
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

from scoring import norm, relevance, deal_type
from credibility import score_source


STATE_FILE = Path(__file__).parent.parent / "data" / "state.json"


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))

    return {
        "articles": [],
        "deals": [],
        "trace": [],
        "stats": {},
        "last_refresh": None,
    }


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def headline_similarity(title_a, title_b):
    return SequenceMatcher(
        None,
        norm(title_a),
        norm(title_b),
    ).ratio()


def run_pipeline(
    incoming,
    state,
    relevance_threshold=0.35,
    credibility_threshold=0.60,
):

    old_articles = {
        article.get("url")
        for article in state.get("articles", [])
        if article.get("url")
    }

    # --------------------------------
    # 1. Identify genuinely new articles
    # --------------------------------

    new_articles = [
        article
        for article in incoming
        if article.get("url") not in old_articles
    ]

    # --------------------------------
    # 2. Score every new article
    # --------------------------------

    scored_articles = []

    for article in new_articles:

        title = article.get("title", "")
        summary = article.get("summary", "")
        source = article.get("source", "")

        relevance_score = relevance(title, summary)
        credibility_score = score_source(source)

        final_score = round(
            0.65 * relevance_score
            + 0.35 * credibility_score,
            3,
        )

        article["relevance_score"] = relevance_score
        article["credibility_score"] = credibility_score
        article["final_score"] = final_score
        article["deal_type"] = deal_type(
            f"{title} {summary}"
        )

        scored_articles.append(article)

    # --------------------------------
    # 3. Relevance + credibility filter
    # --------------------------------

    relevant_articles = [
        article
        for article in scored_articles
        if (
            article["relevance_score"] >= relevance_threshold
            and article["credibility_score"] >= credibility_threshold
        )
    ]

    # --------------------------------
    # 4. Article-level de-duplication
    # --------------------------------

    unique_articles = []
    duplicates_removed = 0

    for article in sorted(
        relevant_articles,
        key=lambda x: x["final_score"],
        reverse=True,
    ):

        duplicate = False

        for existing in unique_articles:

            similarity = headline_similarity(
                article.get("title", ""),
                existing.get("title", ""),
            )

            if similarity >= 0.86:
                duplicate = True
                break

        if duplicate:
            duplicates_removed += 1
        else:
            unique_articles.append(article)

    # --------------------------------
    # 5. Deal-level matching
    # --------------------------------

    deals = state.get("deals", [])

    new_deals = 0
    updated_deals = 0

    for article in unique_articles:

        title = article.get("title", "")

        # Simple, transparent entity extraction.
        # We intentionally avoid hallucinating buyer/target names.

        match = re.split(
            r"\s(?:acquires|acquire|buys|to acquire|invests in|agrees to acquire)\s",
            title,
            flags=re.IGNORECASE,
        )

        if len(match) < 2:
            continue

        buyer = match[0].strip(" -:")
        target = match[1].strip(" -:")

        fingerprint = norm(
            f"{buyer} {target} {article.get('deal_type', 'Other')}"
        )

        matched_deal = None

        for deal in deals:

            similarity = SequenceMatcher(
                None,
                fingerprint,
                deal.get("fingerprint", ""),
            ).ratio()

            if similarity >= 0.78:
                matched_deal = deal
                break

        # --------------------------------
        # Existing deal
        # --------------------------------

        if matched_deal:

            sources = matched_deal.setdefault(
                "sources",
                [],
            )

            url = article.get("url")

            if url and url not in sources:
                sources.append(url)

            matched_deal["last_updated"] = (
                article.get("published")
                or datetime.now().isoformat()
            )

            updated_deals += 1

        # --------------------------------
        # New deal
        # --------------------------------

        else:

            deal_id = f"DEAL-{len(deals) + 1:04d}"

            confidence = (
                "High"
                if article["final_score"] >= 0.82
                else "Medium"
            )

            new_deal = {
                "deal_id": deal_id,
                "buyer": buyer,
                "target": target,
                "fingerprint": fingerprint,
                "deal_type": article.get(
                    "deal_type",
                    "Other",
                ),
                "sector": "FMCG / Consumer",
                "status": "Reported / Announced",
                "deal_value_inr_cr": None,
                "confidence": confidence,
                "summary": re.sub(
                    r"\s+",
                    " ",
                    article.get("summary", ""),
                ).strip()[:400],
                "sources": [
                    article.get("url")
                ],
                "last_updated": (
                    article.get("published")
                    or datetime.now().isoformat()
                ),
            }

            deals.append(new_deal)

            article["deal_id"] = deal_id

            new_deals += 1

    # --------------------------------
    # 6. Merge article history
    # --------------------------------

    article_map = {
        article.get("url"): article
        for article in state.get("articles", [])
        if article.get("url")
    }

    for article in scored_articles:

        url = article.get("url")

        if url:
            article_map[url] = article

    # --------------------------------
    # 7. Agent trace
    # --------------------------------

    trace = [
        f"✓ Retrieved {len(incoming)} public articles",
        f"✓ {len(new_articles)} new articles since last refresh",
        (
            f"✓ {len(relevant_articles)} passed "
            "relevance + credibility filters"
        ),
        (
            f"✓ {duplicates_removed} near-duplicate "
            "articles removed"
        ),
        f"✓ {new_deals} new deals detected",
        f"✓ {updated_deals} existing deals updated",
        f"✓ Newsletter regenerated from {len(deals)} tracked deals",
    ]

    # --------------------------------
    # 8. Return updated state
    # --------------------------------

    return {
        "articles": list(article_map.values()),
        "deals": deals,
        "trace": trace,
        "stats": {
            "articles_scanned": len(incoming),
            "new_articles": len(new_articles),
            "relevant_articles": len(relevant_articles),
            "duplicates_removed": duplicates_removed,
            "new_deals": new_deals,
            "updated_deals": updated_deals,
        },
    }
