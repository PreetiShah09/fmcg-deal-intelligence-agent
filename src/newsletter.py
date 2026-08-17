
from datetime import datetime

def generate_newsletter(deals):
    if not deals:
        return "## FMCG DEAL INTELLIGENCE\n\nNo high-confidence FMCG deal activity passed the current screen."

    selected=sorted(deals,key=lambda x:x.get("last_updated",""),reverse=True)[:7]

    lines=[
        "## FMCG DEAL INTELLIGENCE",
        f"*Latest screened public-source activity — {datetime.now().strftime('%d %b %Y')}*",
        "",
        "### Executive Take",
        "Consumer deal activity remains focused on wellness, beauty, personal care and food brands, with strategic buyers using acquisitions to broaden portfolios and reach attractive consumer segments.",
        "",
        "### Key Developments",
    ]

    for i,d in enumerate(selected,1):
        value=f"₹{d['deal_value_inr_cr']} Cr" if d.get("deal_value_inr_cr") else "Undisclosed"
        lines += [
            f"**{i}. {d.get('buyer','')} → {d.get('target','')}**",
            f"*{d.get('deal_type','')} | {value} | {d.get('status','')} | Confidence: {d.get('confidence','')}*",
            d.get("summary") or "Transaction identified through the public-source screen.",
            f"**Sources:** {len(d.get('sources',[]))}",
            ""
        ]

    lines += [
        "### What to Watch",
        "• Strategic consolidation in wellness, beauty and personal care",
        "• Consumer companies acquiring differentiated D2C brands",
        "• Premiumisation and functional nutrition as investment themes",
    ]
    return "\n".join(lines)
