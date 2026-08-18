from datetime import datetime


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
    deals = deals[:8]

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
