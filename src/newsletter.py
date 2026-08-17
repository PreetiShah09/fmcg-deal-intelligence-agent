
from datetime import datetime
def generate_newsletter(deals):
    if not deals:return "## FMCG DEAL INTELLIGENCE\n\nNo high-confidence activity yet."
    lines=["## FMCG DEAL INTELLIGENCE",f"*Latest screened public-source activity — {datetime.now().strftime('%d %b %Y')}*",
           "","### Executive Take","Strategic buyers and consumer-focused investors continue to use acquisitions and investments to add differentiated brands, especially across personal care, beauty, packaged foods and digital-first consumer businesses.","","### Key Developments"]
    for i,d in enumerate(deals[:7],1):
        lines += [f"**{i}. {d['buyer']} → {d['target']}**",
                  f"*{d['deal_type']} | {d['status']} | Confidence: {d['confidence']}*",
                  d.get("summary") or "Transaction identified through the public-source screen.",""]
    lines += ["### What to Watch","• Strategic consolidation in personal care and packaged foods",
              "• Incumbents using acquisitions to scale D2C brands",
              "• Premiumisation, wellness and snacking as recurring investment themes"]
    return "\n".join(lines)
