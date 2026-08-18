from datetime import datetime
from difflib import SequenceMatcher
import re


# Words that add little value when deciding whether two records describe
# the same underlying transaction.
_DEAL_STOPWORDS = {
    "consumer", "care", "international", "company", "group", "brand",
    "brands", "inc", "limited", "ltd", "private", "pvt", "the",
    "premium", "skincare", "skin", "personal", "beauty", "acquire",
    "acquisition", "buys", "buy", "buys", "stake", "majority",
    "minority", "of", "in", "for", "rs", "cr", "crore", "deal",
}


def _normalise_entity(value):
    text = re.sub(r"[^a-z0-9 ]+", " ", (value or "").lower())
    text = re.sub(r"\s+", " ", text).strip()
    tokens = [t for t in text.split() if t not in _DEAL_STOPWORDS and not t.isdigit()]
    return set(tokens)


def _same_deal(a, b):
    buyer_a = _normalise_entity(a.get("buyer"))
    buyer_b = _normalise_entity(b.get("buyer"))
    target_a = _normalise_entity(a.get("target"))
    target_b = _normalise_entity(b.get("target"))

    if not buyer_a or not buyer_b or not target_a or not target_b:
        return False

    buyer_overlap = len(buyer_a & buyer_b) / max(1, min(len(buyer_a), len(buyer_b)))
    target_overlap = len(target_a & target_b) / max(1, min(len(target_a), len(target_b)))

    # Exact/near-exact buyer + target identity is enough to collapse syndicated
    # or differently worded coverage of the same transaction.
    if buyer_overlap >= 0.70 and target_overlap >= 0.70:
        return True

    # Handle cases such as "Wipro Consumer Care" vs "Wipro" where the
    # remaining buyer identity is very short but the target is distinctive.
    buyer_text_a = " ".join(sorted(buyer_a))
    buyer_text_b = " ".join(sorted(buyer_b))
    target_text_a = " ".join(sorted(target_a))
    target_text_b = " ".join(sorted(target_b))

    buyer_similarity = SequenceMatcher(None, buyer_text_a, buyer_text_b).ratio()
    target_similarity = SequenceMatcher(None, target_text_a, target_text_b).ratio()

    return buyer_similarity >= 0.55 and target_similarity >= 0.75


def _deal_quality(deal):
    confidence_rank = {"High": 3, "Medium": 2, "Low": 1}
    status_rank = {"Completed": 4, "Announced": 3, "Reported": 2, "Potential / Reported": 1}
    sources = len(deal.get("sources", []))
    # Certainty is more important than a reported transaction value. This
    # prevents a lower-quality reported article from replacing an announced
    # record simply because it contains a number.
    return (
        confidence_rank.get(deal.get("confidence"), 0),
        status_rank.get(deal.get("status"), 0),
        sources,
    )


def dedupe_deals(deals):
    """Collapse multiple articles describing the same underlying transaction."""
    unique = []

    for deal in deals or []:
        match = next((existing for existing in unique if _same_deal(existing, deal)), None)

        if match is None:
            unique.append(dict(deal))
            continue

        # Keep the strongest record, but retain all evidence links.
        stronger, weaker = (
            (deal, match) if _deal_quality(deal) > _deal_quality(match) else (match, deal)
        )
        merged = dict(stronger)
        sources = list(dict.fromkeys((match.get("sources", []) or []) + (deal.get("sources", []) or [])))
        merged["sources"] = sources
        unique[unique.index(match)] = merged

    return unique


def format_value(value):
    if not value:
        return "Undisclosed"

    amount = value.get("amount")
    currency = value.get("currency", "")
    unit = value.get("unit", "")

    if amount is None:
        return "Undisclosed"

    return f"{currency}{amount:g}{unit}"


def _source_links(sources):
    links = []
    for i, url in enumerate(sources or [], 1):
        if url:
            links.append(f"[Source {i}]({url})")
    return " · ".join(links) if links else "No source link available"


def generate_newsletter(deals):
    """Generate a professional, skimmable Markdown newsletter from tracked deals."""
    today = datetime.now().strftime("%d %b %Y")
    deals = dedupe_deals(deals)[:8]

    if not deals:
        return "\n".join([
            "# FMCG DEAL INTELLIGENCE",
            "",
            f"*Latest screened public-source activity — {today}*",
            "",
            "> **No tracked deals yet.** Run **Refresh Now** to screen the latest public sources.",
            "",
            "---",
            "",
            "*Public-source discovery is not guaranteed to be exhaustive. "
            "Credibility is a source-quality heuristic, not independent fact verification.*",
        ])

    announced = sum(1 for d in deals if d.get("status") == "Announced")
    completed = sum(1 for d in deals if d.get("status") == "Completed")
    reported = sum(1 for d in deals if "Reported" in d.get("status", "") or "Potential" in d.get("status", ""))
    undisclosed = sum(1 for d in deals if not d.get("deal_value"))

    lines = [
        "# FMCG DEAL INTELLIGENCE",
        "",
        f"*Latest screened public-source activity — {today}*",
        "",
        "| Screen snapshot | |",
        "|---|---:|",
        f"| **Tracked deals** | **{len(deals)}** |",
        f"| Announced | {announced} |",
        f"| Completed | {completed} |",
        f"| Reported / potential | {reported} |",
        f"| Value undisclosed | {undisclosed} |",
        "",
        "## Executive Take",
        "",
        "> Consumer deal activity remains concentrated in **wellness, beauty, personal care and food brands**, "
        "with strategic buyers using acquisitions and investments to broaden portfolios and reach attractive consumer segments.",
        "",
        "**Key themes:** strategic consolidation · differentiated D2C brands · premiumisation · functional nutrition",
        "",
        "## Key Developments",
        "",
    ]

    for i, deal in enumerate(deals, 1):
        buyer = deal.get("buyer", "Unknown")
        target = deal.get("target", "Unknown")
        dtype = deal.get("deal_type", "Transaction")
        status = deal.get("status", "Reported")
        confidence = deal.get("confidence", "Medium")
        value = format_value(deal.get("deal_value"))
        sector = deal.get("sector", "FMCG / Consumer")
        summary = " ".join((deal.get("summary") or "").split())

        lines.extend([
            f"### {i:02d} · {buyer} → {target}",
            "",
            "| Deal type | Status | Value | Confidence |",
            "|---|---|---:|---|",
            f"| {dtype} | **{status}** | **{value}** | {confidence} |",
            "",
            f"**Sector:** {sector}",
            "",
        ])

        if summary:
            lines.extend([summary[:420], ""])

        lines.extend([
            f"**Evidence:** {_source_links(deal.get('sources', []))}",
            "",
            "---",
            "",
        ])

    lines.extend([
        "## What to Watch",
        "",
        "- **Strategic consolidation:** incumbents expanding into adjacent consumer categories through acquisitions.",
        "- **D2C → scale:** digitally native brands becoming attractive where strategic buyers can add distribution and offline reach.",
        "- **Premiumisation:** premium snacking, beauty, wellness and functional nutrition remain active investment themes.",
        "- **Deal certainty:** announced and completed transactions should be distinguished from reported or potential processes.",
        "",
        "## Method Note",
        "",
        "The screen combines FMCG relevance, deal-language signals, source credibility and near-duplicate removal. "
        "Deal status reflects the wording available in the cited public source; undisclosed consideration is not estimated.",
        "",
        "---",
        "",
        "*Credibility is a source-quality heuristic, not independent fact verification. "
        "Public-source discovery is not guaranteed to be exhaustive.*",
    ])

    return "\n".join(lines)
