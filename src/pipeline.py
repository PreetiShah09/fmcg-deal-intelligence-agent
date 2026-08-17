
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


def headline_similarity(a, b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def extract_deal_entities(title, summary, article_type):
    """
    Conservative extraction.
    Only creates a deal when the headline contains a clear transaction pattern.
    Otherwise the article remains evidence but is NOT promoted to Deal Monitor.
    """
    title = re.sub(r"\s+", " ", title or "").strip()

    patterns = [
        # Buyer -> target
        (r"^(.*?)\s+(?:to\s+)?acquire(?:s|d)?\s+(.+?)(?:\s*[-|:]\s*.*)?$",
         "Acquisition"),
        (r"^(.*?)\s+(?:to\s+)?buy(?:s)?\s+(.+?)(?:\s*[-|:]\s*.*)?$",
         "Acquisition"),
        (r"^(.*?)\s+(?:to\s+)?take(?:s)?\s+(?:a\s+)?(?:majority\s+|minority\s+)?stake\s+in\s+(.+?)(?:\s*[-|:]\s*.*)?$",
         "Stake purchase"),
        (r"^(.*?)\s+(?:to\s+)?invest(?:s|ed)?\s+in\s+(.+?)(?:\s*[-|:]\s*.*)?$",
         "Investment"),
        (r"^(.*?)\s+acquisition\s+of\s+(.+?)(?:\s*[-|:]\s*.*)?$",
         "Acquisition"),
        # Target raises funding led by investor
        (r"^(.+?)\s+(?:raises|raised)\s+.*?(?:led|backed)\s+by\s+(.+?)$",
         "Investment"),
    ]

    for pattern, dtype in patterns:
        match = re.search(pattern, title, flags=re.IGNORECASE)
        if match:
            left = match.group(1).strip(" -:;,")
            right = match.group(2).strip(" -:;,")
            if len(left) >= 2 and len(right) >= 2:
                if dtype == "Investment" and "raises" in title.lower():
                    target = left
                    buyer = right
                else:
                    buyer = left
                    target = right

                # Reject obvious publisher/category text.
                bad_fragments = [
                    "press release", "pr newswire", "citybiz",
                    "business wire", "yahoo finance"
                ]
                if any(x in buyer.lower() for x in bad_fragments):
                    return None
                if any(x in target.lower() for x in bad_fragments):
                    return None

                return {
                    "buyer": buyer,
                    "target": target,
                    "deal_type": dtype,
                }

    return None


def run_pipeline(
    incoming,
    state,
    relevance_threshold=0.35,
    credibility_threshold=0.60,
):
    old_articles = {
        a.get("url")
        for a in state.get("articles", [])
        if a.get("url")
    }

    new_articles = [
        a for a in incoming
        if a.get("url") not in old_articles
    ]

    scored = []

    for article in new_articles:
        title = article.get("title", "")
        summary = article.get("summary", "")
        source = article.get("source", "")

        r = relevance(title, summary)
        c = score_source(source)
        final = round(0.65 * r + 0.35 * c, 3)

        article["relevance_score"] = r
        article["credibility_score"] = c
        article["final_score"] = final
        article["deal_type"] = deal_type(f"{title} {summary}")

        scored.append(article)

    relevant = [
        a for a in scored
        if a["relevance_score"] >= relevance_threshold
        and a["credibility_score"] >= credibility_threshold
    ]

    unique = []
    duplicates_removed = 0

    for article in sorted(
        relevant,
        key=lambda x: x["final_score"],
        reverse=True,
    ):
        duplicate = any(
            headline_similarity(
                article.get("title", ""),
                existing.get("title", ""),
            ) >= 0.86
            for existing in unique
        )

        if duplicate:
            duplicates_removed += 1
        else:
            unique.append(article)

    deals = state.get("deals", [])
    new_deals = 0
    updated_deals = 0
    rejected_deal_candidates = 0

    for article in unique:
        entities = extract_deal_entities(
            article.get("title", ""),
            article.get("summary", ""),
            article.get("deal_type", "Other"),
        )

        # Critical safeguard:
        # relevant article != confirmed deal.
        if not entities:
            rejected_deal_candidates += 1
            continue

        buyer = entities["buyer"]
        target = entities["target"]
        dtype = entities["deal_type"]

        fingerprint = norm(f"{buyer} {target} {dtype}")

        matched = None
        for deal in deals:
            similarity = SequenceMatcher(
                None,
                fingerprint,
                deal.get("fingerprint", ""),
            ).ratio()

            if similarity >= 0.78:
                matched = deal
                break

        if matched:
            sources = matched.setdefault("sources", [])
            url = article.get("url")

            if url and url not in sources:
                sources.append(url)

            matched["last_updated"] = (
                article.get("published")
                or datetime.now().isoformat()
            )

            if len(sources) >= 2:
                matched["confidence"] = "High"

            updated_deals += 1

        else:
            confidence = (
                "High"
                if article["final_score"] >= 0.82
                else "Medium"
            )

            deal_id = f"DEAL-{len(deals) + 1:04d}"

            deals.append({
                "deal_id": deal_id,
                "buyer": buyer,
                "target": target,
                "fingerprint": fingerprint,
                "deal_type": dtype,
                "sector": "FMCG / Consumer",
                "status": "Reported / Announced",
                "deal_value_inr_cr": None,
                "confidence": confidence,
                "summary": re.sub(
                    r"\s+",
                    " ",
                    article.get("summary", ""),
                ).strip()[:420],
                "sources": [article.get("url")],
                "last_updated": (
                    article.get("published")
                    or datetime.now().isoformat()
                ),
            })

            article["deal_id"] = deal_id
            new_deals += 1

    # Preserve article evidence even when it is not promoted to a deal.
    article_map = {
        a.get("url"): a
        for a in state.get("articles", [])
        if a.get("url")
    }

    for article in scored:
        if article.get("url"):
            article_map[article["url"]] = article

    trace = [
        f"✓ Retrieved {len(incoming)} public articles",
        f"✓ {len(new_articles)} new articles since last refresh",
        f"✓ {len(relevant)} passed relevance + credibility filters",
        f"✓ {duplicates_removed} near-duplicate articles removed",
        f"✓ {rejected_deal_candidates} relevant articles kept as evidence only",
        f"✓ {new_deals} new deals detected",
        f"✓ {updated_deals} existing deals updated",
        f"✓ Newsletter regenerated from {len(deals)} tracked deals",
    ]

    return {
        "articles": list(article_map.values()),
        "deals": deals,
        "trace": trace,
        "stats": {
            "articles_scanned": len(incoming),
            "new_articles": len(new_articles),
            "relevant_articles": len(relevant),
            "duplicates_removed": duplicates_removed,
            "new_deals": new_deals,
            "updated_deals": updated_deals,
        },
    }
