
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
    title = re.sub(r"\s+", " ", title or "").strip()

    patterns = [
        (r"^(.*?)\s+(?:to\s+)?acquire(?:s|d)?\s+(.+?)(?:\s*[-|:]\s*.*)?$",
         "Acquisition"),
        (r"^(.*?)\s+(?:to\s+)?buy(?:s)?\s+(.+?)(?:\s*[-|:]\s*.*)?$",
         "Acquisition"),
        (r"^(.*?)\s+(?:to\s+)?purchase\s+(.+?)(?:\s*[-|:]\s*.*)?$",
         "Acquisition"),
        (r"^(.*?)\s+(?:to\s+)?take(?:s)?\s+(?:a\s+)?(?:majority\s+|minority\s+)?stake\s+in\s+(.+?)(?:\s*[-|:]\s*.*)?$",
         "Stake purchase"),
        (r"^(.*?)\s+(?:to\s+)?invest(?:s|ed)?\s+in\s+(.+?)(?:\s*[-|:]\s*.*)?$",
         "Investment"),
        (r"^(.*?)\s+acquisition\s+of\s+(.+?)(?:\s*[-|:]\s*.*)?$",
         "Acquisition"),
        (r"^(.+?)\s+(?:raises|raised)\s+.*?(?:led|backed)\s+by\s+(.+?)$",
         "Investment"),
    ]

    for pattern, dtype in patterns:
        match = re.search(pattern, title, flags=re.IGNORECASE)
        if match:
            left = match.group(1).strip(" -:;,")
            right = match.group(2).strip(" -:;,")

            if len(left) < 2 or len(right) < 2:
                continue

            if dtype == "Investment" and "raises" in title.lower():
                target, buyer = left, right
            else:
                buyer, target = left, right

            # Remove generic words that make target names look awkward.
            target = re.sub(
                r"^(?:wellness company|consumer brand|consumer company)\s+",
                "",
                target,
                flags=re.IGNORECASE,
            ).strip()

            bad = [
                "press release", "pr newswire", "citybiz",
                "business wire", "yahoo finance"
            ]

            if any(x in buyer.lower() for x in bad):
                continue
            if any(x in target.lower() for x in bad):
                continue

            return {
                "buyer": buyer,
                "target": target,
                "deal_type": dtype,
            }

    return None


def extract_deal_value(text):
    """Extract a stated transaction/funding value from title/summary."""
    text = text or ""

    patterns = [
        r"(?i)(?:acquire|acquisition|purchase|deal|transaction|investment|funding|raises?|raised|worth|valued at|valuation)[^.]{0,100}?\$?\s*([\d,.]+)\s*(billion|bn|million|mn|m|crore|cr)\b",
        r"(?i)\$?\s*([\d,.]+)\s*(billion|bn|million|mn)\b",
        r"(?i)₹\s*([\d,.]+)\s*(billion|bn|million|mn|crore|cr)\b",
        r"(?i)₹\s*([\d,.]+)\s*(?:crore|cr)\b",
    ]

    for pattern in patterns:
        m = re.search(pattern, text)
        if not m:
            continue

        try:
            amount = float(m.group(1).replace(",", ""))
        except ValueError:
            continue

        unit = m.group(2).lower()

        if unit in {"billion", "bn"}:
            return {"amount": amount, "currency": "$", "unit": "B"}
        if unit in {"million", "mn", "m"}:
            return {"amount": amount, "currency": "$", "unit": "M"}
        if unit in {"crore", "cr"}:
            return {"amount": amount, "currency": "₹", "unit": "Cr"}

    return None


def classify_status(title, summary):
    text = f"{title} {summary}".lower()

    potential_terms = [
        "explores a sale",
        "exploring a sale",
        "seeks buyer",
        "seeking a buyer",
        "considering a sale",
        "potential sale",
        "may acquire",
        "could acquire",
        "in talks",
        "reportedly in talks",
    ]

    completed_terms = [
        "completed the acquisition",
        "completed its acquisition",
        "has completed",
        "closed the acquisition",
        "deal closed",
    ]

    announced_terms = [
        "to acquire",
        "to purchase",
        "agrees to acquire",
        "agreed to acquire",
        "acquires",
        "acquired",
        "acquisition of",
        "raises",
        "raised",
        "investment in",
        "invests in",
        "funding led by",
    ]

    if any(x in text for x in potential_terms):
        return "Potential / Reported"
    if any(x in text for x in completed_terms):
        return "Completed"
    if any(x in text for x in announced_terms):
        return "Announced"
    return "Reported"


def run_pipeline(
    incoming,
    state,
    relevance_threshold=0.35,
    credibility_threshold=0.60,
):
    old_articles = {
        a.get("fingerprint")
        for a in state.get("articles", [])
        if a.get("fingerprint")
    }

    # Fallback for older state files.
    old_urls = {
        a.get("url")
        for a in state.get("articles", [])
        if a.get("url")
    }

    new_articles = []

    for article in incoming:
        title = article.get("title", "")
        source = article.get("source", "")
        fingerprint = norm(f"{title} | {source}")

        article["fingerprint"] = fingerprint

        if fingerprint not in old_articles and article.get("url") not in old_urls:
            new_articles.append(article)

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
        and a.get("fmcg_pass", False)
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
    evidence_only = 0

    for article in unique:
        entities = extract_deal_entities(
            article.get("title", ""),
            article.get("summary", ""),
            article.get("deal_type", "Other"),
        )

        if not entities:
            evidence_only += 1
            continue

        buyer = entities["buyer"]
        target = entities["target"]
        dtype = entities["deal_type"]

        text = f"{article.get('title', '')} {article.get('summary', '')}"
        value = extract_deal_value(text)
        status = classify_status(
            article.get("title", ""),
            article.get("summary", ""),
        )

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

            if value:
                matched["deal_value"] = value

            # Don't downgrade a completed deal.
            if matched.get("status") != "Completed":
                matched["status"] = status

            if len(sources) >= 2 or article["credibility_score"] >= 0.9:
                matched["confidence"] = "High"

            matched["last_updated"] = (
                article.get("published")
                or datetime.now().isoformat()
            )

            updated_deals += 1

        else:
            confidence = (
                "High"
                if (
                    article["final_score"] >= 0.82
                    or article["credibility_score"] >= 0.9
                )
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
                "status": status,
                "deal_value": value,
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

    article_map = {
        a.get("fingerprint") or a.get("url"): a
        for a in state.get("articles", [])
        if a.get("fingerprint") or a.get("url")
    }

    for article in scored:
        key = article.get("fingerprint") or article.get("url")
        if key:
            article_map[key] = article

    trace = [
        f"✓ Retrieved {len(incoming)} public articles",
        f"✓ {len(new_articles)} new articles since last refresh",
        f"✓ {len(relevant)} passed FMCG + relevance + credibility filters",
        f"✓ {duplicates_removed} near-duplicate articles removed",
        f"✓ {evidence_only} relevant articles kept as evidence only",
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
