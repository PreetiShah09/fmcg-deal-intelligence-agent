import json
import re
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

from scoring import norm, relevance, deal_type
from credibility import score_source


STATE_FILE = Path(__file__).parent.parent / "data" / "state.json"


FMCG_POSITIVE = {
    "fmcg", "consumer goods", "consumer brand", "food", "foods", "snack",
    "snacks", "beverage", "beverages", "drink", "drinks", "dairy",
    "grocery", "packaged food", "packaged foods", "nutrition",
    "supplement", "supplements", "wellness", "beauty", "cosmetics",
    "personal care", "skin care", "skincare", "hair care", "haircare",
    "hygiene", "home care", "household", "oral care", "baby care",
    "pet care", "consumer health", "functional nutrition", "natural foods",
    "better-for-you", "d2c", "direct-to-consumer", "confectionery",
    "chocolate", "bakery", "granola", "seasoning", "sauces"
}


FMCG_NEGATIVE = {
    "fintech", "credit management", "banking", "lending", "insurance",
    "saas", "software", "enterprise software", "edtech", "proptech",
    "real estate", "logistics", "infrastructure", "industrial",
    "landscaping", "construction", "telecom", "cybersecurity",
    "payments", "crypto", "agritech", "automotive", "manufacturing"
}


# Generic words that are not useful for deciding whether two records
# represent the same buyer/target.
_DEAL_STOPWORDS = {
    "consumer",
    "care",
    "international",
    "company",
    "companies",
    "group",
    "brand",
    "brands",
    "inc",
    "limited",
    "ltd",
    "private",
    "pvt",
    "the",
    "premium",
    "skincare",
    "skin",
    "personal",
    "beauty",
    "acquire",
    "acquisition",
    "acquires",
    "acquired",
    "buys",
    "buy",
    "purchase",
    "stake",
    "majority",
    "minority",
    "of",
    "in",
    "for",
    "deal",
    "transaction",
}


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


def fmcg_classify(title, summary):
    text = f"{title} {summary}".lower()

    positive_hits = sum(
        1 for k in FMCG_POSITIVE
        if k in text
    )

    negative_hits = sum(
        1 for k in FMCG_NEGATIVE
        if k in text
    )

    # A clear non-FMCG business category overrides generic consumer language.
    if negative_hits > 0 and positive_hits <= 2:
        return False

    return positive_hits > 0


def headline_similarity(a, b):
    return SequenceMatcher(
        None,
        norm(a),
        norm(b)
    ).ratio()


def _normalise_deal_entity(value):
    """
    Normalise buyer/target names before deal matching.

    Example:
        Wipro Consumer Care
        Wipro

    become much closer after removing generic words.
    """

    text = re.sub(
        r"[^a-z0-9 ]+",
        " ",
        (value or "").lower()
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    tokens = [
        token
        for token in text.split()
        if token not in _DEAL_STOPWORDS
        and not token.isdigit()
    ]

    return set(tokens)


def _entity_similarity(a, b):
    """
    Compare two company/brand names using both
    token overlap and SequenceMatcher.
    """

    a_tokens = _normalise_deal_entity(a)
    b_tokens = _normalise_deal_entity(b)

    if not a_tokens or not b_tokens:
        return 0.0

    # If one meaningful entity is contained inside the other,
    # treat it as an extremely strong match.
    if (
        a_tokens.issubset(b_tokens)
        or b_tokens.issubset(a_tokens)
    ):
        return 1.0

    token_overlap = (
        len(a_tokens & b_tokens)
        / max(1, min(len(a_tokens), len(b_tokens)))
    )

    a_text = " ".join(sorted(a_tokens))
    b_text = " ".join(sorted(b_tokens))

    text_similarity = SequenceMatcher(
        None,
        a_text,
        b_text
    ).ratio()

    return max(
        token_overlap,
        text_similarity
    )


def _same_deal(
    buyer_a,
    target_a,
    type_a,
    buyer_b,
    target_b,
    type_b,
):
    """
    Determine whether two extracted records represent
    the same underlying transaction.
    """

    # Deal type must be compatible.
    if (
        type_a
        and type_b
        and type_a != type_b
    ):
        return False

    buyer_score = _entity_similarity(
        buyer_a,
        buyer_b
    )

    target_score = _entity_similarity(
        target_a,
        target_b
    )

    # Strong buyer + target match.
    if (
        buyer_score >= 0.70
        and target_score >= 0.70
    ):
        return True

    # Handle cases where the buyer name is abbreviated
    # but the target is highly distinctive.
    if (
        buyer_score >= 0.90
        and target_score >= 0.85
    ):
        return True

    return False


def extract_deal_entities(title, summary, article_type):
    title = re.sub(
        r"\s+",
        " ",
        title or ""
    ).strip()

    patterns = [
        (
            r"^(.*?)\s+(?:to\s+)?acquire(?:s|d)?\s+(.+?)(?:\s*[-|:]\s*.*)?$",
            "Acquisition",
        ),
        (
            r"^(.*?)\s+(?:to\s+)?buy(?:s)?\s+(.+?)(?:\s*[-|:]\s*.*)?$",
            "Acquisition",
        ),
        (
            r"^(.*?)\s+(?:to\s+)?purchase\s+(.+?)(?:\s*[-|:]\s*.*)?$",
            "Acquisition",
        ),
        (
            r"^(.*?)\s+(?:to\s+)?take(?:s)?\s+(?:a\s+)?(?:majority\s+|minority\s+)?stake\s+in\s+(.+?)(?:\s*[-|:]\s*.*)?$",
            "Stake purchase",
        ),
        (
            r"^(.*?)\s+(?:to\s+)?invest(?:s|ed)?\s+in\s+(.+?)(?:\s*[-|:]\s*.*)?$",
            "Investment",
        ),
        (
            r"^(.*?)\s+acquisition\s+of\s+(.+?)(?:\s*[-|:]\s*.*)?$",
            "Acquisition",
        ),
        (
            r"^(.+?)\s+(?:raises|raised)\s+.*?(?:led|backed)\s+by\s+(.+?)$",
            "Investment",
        ),
    ]

    for pattern, dtype in patterns:

        match = re.search(
            pattern,
            title,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        left = match.group(1).strip(" -:;,")
        right = match.group(2).strip(" -:;,")

        if len(left) < 2 or len(right) < 2:
            continue

        if (
            dtype == "Investment"
            and "raises" in title.lower()
        ):
            target = left
            buyer = right
        else:
            buyer = left
            target = right

        target = re.sub(
            r"^(?:wellness company|consumer brand|consumer company)\s+",
            "",
            target,
            flags=re.IGNORECASE,
        ).strip()

        bad = [
            "press release",
            "pr newswire",
            "citybiz",
            "business wire",
            "yahoo finance",
        ]

        if (
            any(x in buyer.lower() for x in bad)
            or any(x in target.lower() for x in bad)
        ):
            continue

        return {
            "buyer": buyer,
            "target": target,
            "deal_type": dtype,
        }

    return None


def extract_deal_value(text):
    patterns = [
        r"(?i)(?:acquire|acquisition|purchase|deal|transaction|investment|funding|raises?|raised|worth|valued at|valuation)[^.]{0,100}?\$?\s*([\d,.]+)\s*(billion|bn|million|mn|m|crore|cr)\b",
        r"(?i)\$?\s*([\d,.]+)\s*(billion|bn|million|mn)\b",
        r"(?i)₹\s*([\d,.]+)\s*(billion|bn|million|mn|crore|cr)\b",
        r"(?i)₹\s*([\d,.]+)\s*(?:crore|cr)\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text or ""
        )

        if not match:
            continue

        try:
            amount = float(
                match.group(1).replace(",", "")
            )
        except ValueError:
            continue

        unit = match.group(2).lower()

        if unit in {"billion", "bn"}:
            return {
                "amount": amount,
                "currency": "$",
                "unit": "B",
            }

        if unit in {"million", "mn", "m"}:
            return {
                "amount": amount,
                "currency": "$",
                "unit": "M",
            }

        if unit in {"crore", "cr"}:
            return {
                "amount": amount,
                "currency": "₹",
                "unit": "Cr",
            }

    return None


def classify_status(title, summary):
    text = f"{title} {summary}".lower()

    if any(
        x in text
        for x in [
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
    ):
        return "Potential / Reported"

    if any(
        x in text
        for x in [
            "completed the acquisition",
            "completed its acquisition",
            "has completed",
            "closed the acquisition",
            "deal closed",
        ]
    ):
        return "Completed"

    if any(
        x in text
        for x in [
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
    ):
        return "Announced"

    return "Reported"


def run_pipeline(
    incoming,
    state,
    relevance_threshold=0.35,
    credibility_threshold=0.60,
):
    old_fingerprints = {
        a.get("fingerprint")
        for a in state.get("articles", [])
        if a.get("fingerprint")
    }

    old_urls = {
        a.get("url")
        for a in state.get("articles", [])
        if a.get("url")
    }

    new_articles = []

    for article in incoming:

        title = article.get(
            "title",
            ""
        )

        source = article.get(
            "source",
            ""
        )

        fingerprint = norm(
            f"{title} | {source}"
        )

        article["fingerprint"] = fingerprint

        if (
            fingerprint not in old_fingerprints
            and article.get("url") not in old_urls
        ):
            new_articles.append(article)

    scored = []

    for article in new_articles:

        title = article.get(
            "title",
            ""
        )

        summary = article.get(
            "summary",
            ""
        )

        source = article.get(
            "source",
            ""
        )

        r = relevance(
            title,
            summary
        )

        c = score_source(
            source
        )

        final = round(
            0.65 * r + 0.35 * c,
            3
        )

        article["fmcg_pass"] = fmcg_classify(
            title,
            summary
        )

        article["relevance_score"] = r
        article["credibility_score"] = c
        article["final_score"] = final

        article["deal_type"] = deal_type(
            f"{title} {summary}"
        )

        scored.append(article)

    relevant = [
        a
        for a in scored
        if a["fmcg_pass"]
        and a["relevance_score"] >= relevance_threshold
        and a["credibility_score"] >= credibility_threshold
    ]

    # ---------------------------------------------------------
    # ARTICLE-LEVEL DEDUPLICATION
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # DEAL-LEVEL MATCHING
    # ---------------------------------------------------------

    deals = state.get(
        "deals",
        []
    )

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

        text = (
            f"{article.get('title', '')} "
            f"{article.get('summary', '')}"
        )

        value = extract_deal_value(
            text
        )

        status = classify_status(
            article.get("title", ""),
            article.get("summary", ""),
        )

        fingerprint = norm(
            f"{buyer} {target} {dtype}"
        )

        # -----------------------------------------------------
        # IMPORTANT:
        # Do NOT compare the entire fingerprint anymore.
        #
        # Compare buyer + target + deal type separately.
        # This fixes cases such as:
        #
        # Wipro Consumer Care
        # Wipro
        #
        # both referring to the same transaction.
        # -----------------------------------------------------

        matched = None

        for deal in deals:

            if _same_deal(
                buyer,
                target,
                dtype,
                deal.get("buyer", ""),
                deal.get("target", ""),
                deal.get("deal_type", ""),
            ):
                matched = deal
                break

        # -----------------------------------------------------
        # EXISTING DEAL
        # -----------------------------------------------------

        if matched:

            sources = matched.setdefault(
                "sources",
                []
            )

            url = article.get(
                "url"
            )

            if (
                url
                and url not in sources
            ):
                sources.append(url)

            # Preserve disclosed value.
            if value:
                matched["deal_value"] = value

            # Do not downgrade completed transactions.
            if matched.get("status") != "Completed":
                matched["status"] = status

            # More evidence increases confidence.
            if (
                len(sources) >= 2
                or article["credibility_score"] >= 0.90
            ):
                matched["confidence"] = "High"

            matched["last_updated"] = (
                article.get("published")
                or datetime.now().isoformat()
            )

            updated_deals += 1

            # Attach the existing deal ID to this article.
            article["deal_id"] = matched.get(
                "deal_id"
            )

        # -----------------------------------------------------
        # NEW DEAL
        # -----------------------------------------------------

        else:

            confidence = (
                "High"
                if (
                    article["final_score"] >= 0.82
                    or article["credibility_score"] >= 0.90
                )
                else "Medium"
            )

            deal_id = (
                f"DEAL-{len(deals) + 1:04d}"
            )

            deals.append(
                {
                    "deal_id": deal_id,
                    "buyer": buyer,
                    "target": target,
                    "fingerprint": fingerprint,
                    "deal_type": dtype,
                    "sector": "FMCG / Consumer",
                    "status": status,
                    "deal_value": value,
                    "confidence": confidence,
                    "summary": re.sub(
                        r"\s+",
                        " ",
                        article.get(
                            "summary",
                            ""
                        ),
                    ).strip()[:420],
                    "sources": [
                        article.get("url")
                    ],
                    "last_updated": (
                        article.get("published")
                        or datetime.now().isoformat()
                    ),
                }
            )

            article["deal_id"] = deal_id

            new_deals += 1

    # ---------------------------------------------------------
    # ARTICLE STATE
    # ---------------------------------------------------------

    article_map = {
        a.get("fingerprint") or a.get("url"): a
        for a in state.get("articles", [])
        if a.get("fingerprint") or a.get("url")
    }

    for article in scored:

        key = (
            article.get("fingerprint")
            or article.get("url")
        )

        if key:
            article_map[key] = article

    stored_articles = list(
        article_map.values()
    )

    # ---------------------------------------------------------
    # CURRENT RELEVANT ARTICLE COUNT
    # ---------------------------------------------------------

    total_relevant_articles = sum(
        1
        for a in stored_articles
        if a.get("fmcg_pass")
        and a.get("relevance_score", 0)
        >= relevance_threshold
        and a.get("credibility_score", 0)
        >= credibility_threshold
    )

    # ---------------------------------------------------------
    # PIPELINE TRACE
    # ---------------------------------------------------------

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
        "articles": stored_articles,
        "deals": deals,
        "trace": trace,
        "stats": {
            "articles_scanned": len(incoming),
            "new_articles": len(new_articles),
            "relevant_articles": total_relevant_articles,
            "duplicates_removed": duplicates_removed,
            "new_deals": new_deals,
            "updated_deals": updated_deals,
        },
    }
