
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


def generate_newsletter(deals):
    today = datetime.now().strftime("%d %b %Y")

    lines = [
        "# FMCG DEAL INTELLIGENCE",
        "",
        f"*Latest screened public-source activity — {today}*",
        "",
        "## Executive Take",
        "",
        "Consumer deal activity remains concentrated in wellness, beauty, "
        "personal care and food brands, with strategic buyers using "
        "acquisitions to broaden portfolios and access attractive consumer segments.",
        "",
        "## Key Developments",
        "",
    ]

    for i, deal in enumerate(deals[:8], 1):
        buyer = deal.get("buyer", "Unknown")
        target = deal.get("target", "Unknown")
        dtype = deal.get("deal_type", "Transaction")
        status = deal.get("status", "Reported")
        confidence = deal.get("confidence", "Medium")
        value = format_value(deal.get("deal_value"))

        lines.append(
            f"**{i}. {buyer} → {target}**  \n"
            f"{dtype} | {value} | {status} | Confidence: {confidence}"
        )

        summary = deal.get("summary", "")
        if summary:
            lines.append(summary)

        lines.append(
            f"Sources: {len(deal.get('sources', []))}"
        )
        lines.append("")

    lines.extend([
        "## What to Watch",
        "",
        "• Strategic consolidation in wellness, beauty and personal care",
        "• Consumer companies acquiring differentiated D2C brands",
        "• Premiumisation and functional nutrition as investment themes",
        "",
        "---",
        "",
        "*Credibility is a source-quality heuristic, not independent fact verification. "
        "Public-source discovery is not guaranteed to be exhaustive.*",
    ])

    return "\n".join(lines)
