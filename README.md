# FMCG Deal Intelligence Newsletter Agent

A lightweight Streamlit application that screens publicly available news for recent FMCG M&A and investment activity, filters and scores the evidence, consolidates duplicate coverage into deal records, and generates a concise investment-style newsletter.

## Live Demo

**Streamlit App:** https://fmcg-deal-agent-17082026.streamlit.app/

**GitHub Repository:** https://github.com/PreetiShah09/fmcg-deal-intelligence-agent

---

## 1. Problem

FMCG deal activity is reported across many public news sources and can be difficult to scan quickly. This application provides a lightweight intelligence workflow that turns recent public-source coverage into a short, structured view of relevant FMCG M&A and investment activity.

The goal is not to replace primary-source diligence. It is to provide a fast first-pass screen of recent deal activity.

---

## 2. Architecture

```text
                    PUBLIC NEWS / RSS SOURCES
                              │
                              ▼
                       ┌─────────────┐
                       │  INGESTION  │
                       └──────┬──────┘
                              │
                              ▼
                       ┌─────────────┐
                       │   CLEANING  │
                       │ Normalize   │
                       │ + Fingerprint│
                       └──────┬──────┘
                              │
                              ▼
                  ┌─────────────────────────┐
                  │ FMCG + DEAL SCREENING   │
                  │ Relevance + Credibility │
                  └───────────┬─────────────┘
                              │
                              ▼
                       ┌─────────────┐
                       │ DE-DUPLICATE│
                       │   ARTICLES  │
                       └──────┬──────┘
                              │
                              ▼
                       ┌─────────────┐
                       │ DEAL MATCH  │
                       │ Buyer/Target│
                       │ Type/Value  │
                       └──────┬──────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
             DEAL MONITOR          EVIDENCE
                    │                   │
                    └─────────┬─────────┘
                              ▼
                       ┌─────────────┐
                       │ NEWSLETTER  │
                       └─────────────┘
```

### Pipeline

**Ingestion → cleaning → FMCG classification → relevance & credibility scoring → de-duplication → deal matching → newsletter**

---

## 3. How the Agent Works

### 3.1 Ingestion

The application retrieves recent articles from the configured public RSS/news sources. A look-back window controls the screening period.

When the user clicks **Refresh Now**, the application checks the latest available source universe and compares articles with its persisted article history.

### 3.2 FMCG Classification

Articles are screened for FMCG/consumer signals such as:

- Food and packaged foods
- Beverages
- Snacks and confectionery
- Beauty and cosmetics
- Personal care
- Wellness and supplements
- Consumer health
- Home/household care
- D2C consumer brands
- Nutrition and functional foods

Clear non-FMCG categories can override generic consumer language. Examples include fintech, credit management, SaaS/software, logistics, industrial, infrastructure and landscaping.

This helps prevent a generic "consumer" or "B2C" article from being incorrectly treated as an FMCG deal.

### 3.3 Relevance + Credibility Scoring

Each new article receives:

- A **relevance score** based on deal/FMCG signals
- A **source credibility score** based on the configured source-quality heuristic
- A combined screening score

Only articles above the selected thresholds continue through the main screening path.

**Important assumption:** credibility is a source-quality heuristic, not independent fact verification.

### 3.4 Near-Duplicate Removal

Relevant articles are compared using normalized headline similarity.

A headline similarity of **≥ 0.86** is treated as a near duplicate, with the stronger-ranked article retained for the immediate evidence set.

Article-level deduplication is separate from deal-level consolidation.

### 3.5 Deal Extraction and Matching

Clear transaction language is used to identify:

- Buyer / investor
- Target
- Deal type
- Deal status
- Disclosed transaction value when available

The system distinguishes statuses such as:

- Announced
- Completed
- Potential / Reported
- Reported

Existing deals are matched using a deal fingerprint based on **buyer + target + deal type**. This means multiple articles about the same transaction can be consolidated into one deal record rather than creating duplicate deals.

For example, multiple articles covering the Wipro Consumer Care → Dermatouch transaction can be consolidated into one tracked deal with multiple evidence sources.

If one source provides a disclosed value while another does not, the disclosed value is retained rather than being overwritten by an "undisclosed" record.

---

## 4. Refresh Now vs Reset Deal Store

### Refresh Now

**Refresh Now** is the normal operating action.

It:

1. Retrieves the latest public articles.
2. Identifies articles that have not previously been processed.
3. Scores and filters the new articles.
4. Removes near-duplicate coverage.
5. Matches new evidence to existing deals.
6. Creates genuinely new deal records when appropriate.
7. Updates existing deals when new evidence is found.
8. Regenerates the newsletter from the current deal store.

If no new articles are available, **New articles = 0** and **New deals = 0**, while previously tracked deals remain visible.

### Reset Deal Store

**Reset Deal Store** is a testing/demo control, not a normal operating action.

It clears the locally persisted article and deal state so the current source universe can be treated as a fresh first run.

Recommended clean-demo flow:

**Reset Deal Store → Refresh Now**

---

## 5. User Interface

### Newsletter

A concise investment-style brief containing:

- Screen snapshot
- Executive Take
- Key Themes
- Key Developments
- Deal type, status, disclosed value and confidence
- Evidence/source information
- What to Watch
- Method Note

### Deal Monitor

Shows persistent tracked deals with:

- Buyer / investor
- Target
- Deal type
- Status
- Disclosed value
- Confidence
- Source count
- Last updated

### Article Evidence

Shows the article-level evidence and screening fields, including:

- FMCG pass
- Relevance score
- Credibility score
- Final score
- Deal ID
- Source / URL

### Agent Trace

Shows the pipeline counts for the latest refresh:

**Retrieved → new articles → FMCG/relevance/credibility matches → duplicates → evidence-only articles → new deals → updated deals → newsletter**

---

## 6. Final Deliverables

The project submission includes:

- **Live Streamlit demo:** https://fmcg-deal-agent-17082026.streamlit.app/
- **GitHub source code:** https://github.com/PreetiShah09/fmcg-deal-intelligence-agent
- **Raw deal data:** CSV
- **Structured newsletter:** Excel
- **Architecture and methodology:** this README
- **Agent trace and evidence:** available in the Streamlit application

The Excel newsletter is a **point-in-time snapshot** of the deal intelligence screen. The live application can continue to update independently when refreshed.

---

## 7. Methodology and Limitations

- Public-source discovery is not guaranteed to be exhaustive.
- The system is dependent on the configured public news/RSS sources.
- Deal status is based on the wording and evidence available in cited public sources.
- Undisclosed transaction consideration is not estimated.
- Source credibility is a heuristic rather than independent fact verification.
- Relevance thresholds are configurable and can affect the number of articles that pass.
- Near-duplicate detection uses similarity thresholds and may not catch every semantically equivalent article.
- The application is an intelligence-screening tool, not investment advice or a replacement for primary-source diligence.

---

## 8. Why This Is an Agent-Style Workflow

The application is designed as a lightweight decision pipeline rather than a simple news scraper.

On each refresh it:

1. Retrieves current public-source information.
2. Determines whether the content is relevant to FMCG.
3. Scores relevance and source credibility.
4. Removes duplicate/near-duplicate coverage.
5. Determines whether the article contains actionable transaction language.
6. Matches the transaction against previously tracked deals.
7. Updates the deal record when additional evidence appears.
8. Regenerates the newsletter from the current deal store.

This creates a simple:

**Sense → Screen → Consolidate → Track → Summarize**

workflow.

---

## 9. Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 10. Repository Structure

```text
.
├── app.py
├── src/
│   ├── ingestion.py
│   ├── pipeline.py
│   ├── scoring.py
│   └── credibility.py
├── newsletter.py
├── data/
│   └── state.json
├── requirements.txt
└── README.md
```

---

## 11. Final Demo Flow

1. Open the Streamlit application.
2. Set the look-back window and screening thresholds.
3. Click **Refresh Now**.
4. Review **Newsletter → Deal Monitor → Article Evidence → Agent Trace**.
5. Use **Reset Deal Store** only when demonstrating a clean first run.
6. Provide the structured newsletter Excel and raw CSV as separate submission artifacts.

---

## 12. Submission Checklist

- [x] Live Streamlit application
- [x] Public-source ingestion
- [x] FMCG relevance filtering
- [x] Source credibility scoring
- [x] Near-duplicate removal
- [x] Deal-level consolidation
- [x] Persistent deal tracking
- [x] Article evidence view
- [x] Agent trace
- [x] Professional newsletter structure
- [x] Raw CSV data
- [x] Structured newsletter Excel
- [x] README documenting architecture, methodology and limitations
