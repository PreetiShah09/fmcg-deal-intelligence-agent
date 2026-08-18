# FMCG Deal Intelligence Newsletter Agent

A lightweight Streamlit application that screens publicly available news for recent FMCG M&A and investment activity, filters relevant evidence, consolidates duplicate coverage into deal records, and generates a concise investment-style newsletter.

## Live Demo

**Streamlit App:** https://fmcg-deal-agent-17082026.streamlit.app/

**GitHub Repository:** https://github.com/PreetiShah09/fmcg-deal-intelligence-agent

---

## Problem

FMCG deal activity is reported across multiple public news sources and can be difficult to scan quickly.

This application provides a lightweight screening workflow that turns recent public-source coverage into a structured view of relevant FMCG M&A and investment activity.

The objective is to provide a fast first-pass intelligence screen, rather than replace primary-source diligence.

---

## Architecture

```text
Public News / RSS Sources
          ↓
       Ingestion
          ↓
Cleaning & Normalisation
          ↓
FMCG Relevance + Credibility
          ↓
  Near-Duplicate Removal
          ↓
    Deal Extraction
          ↓
     Deal Matching
          ↓
Deal Monitor + Article Evidence
          ↓
      Newsletter
```

### Pipeline

**Ingestion → Cleaning → FMCG Classification → Relevance & Credibility Scoring → De-duplication → Deal Matching → Newsletter**

---

## How the Agent Works

### 1. Ingestion

The application retrieves recent articles from the configured public RSS/news sources.

A look-back window controls the screening period.

When the user clicks **Refresh Now**, the application checks the latest available source universe and compares articles against previously processed article history.

### 2. FMCG Classification

Articles are screened for FMCG and consumer signals such as:

- Food and packaged foods
- Beverages
- Snacks and confectionery
- Beauty and cosmetics
- Personal care
- Wellness and supplements
- Consumer health
- Household care
- D2C consumer brands
- Nutrition and functional foods

Clear non-FMCG categories can override generic consumer language.

Examples include fintech, credit management, SaaS/software, logistics, industrial, infrastructure and landscaping.

This reduces false positives from articles that contain generic consumer or business terminology but are not relevant to FMCG.

### 3. Relevance and Credibility

Each new article receives:

- A relevance score
- A source credibility score
- A combined screening score

Only articles above the selected thresholds continue through the main screening path.

The credibility score is a source-quality heuristic rather than independent fact verification.

### 4. Near-Duplicate Removal

Relevant articles are compared using normalized headline similarity.

A headline similarity of **≥ 0.86** is treated as a near duplicate, with the stronger-ranked article retained for the immediate evidence set.

Article-level de-duplication is separate from deal-level consolidation.

### 5. Deal Extraction

Clear transaction language is used to identify:

- Buyer / investor
- Target
- Deal type
- Deal status
- Disclosed transaction value, where available

The system distinguishes between statuses such as:

- Announced
- Completed
- Potential / Reported
- Reported

### 6. Deal Matching

Existing deals are matched using a deal fingerprint based on:

**Buyer + Target + Deal Type**

This allows multiple articles about the same underlying transaction to be consolidated into one tracked deal rather than creating duplicate deal records.

For example, multiple articles covering the Wipro Consumer Care → Dermatouch transaction can be consolidated into one deal with multiple supporting sources.

If one source provides a disclosed value while another does not, the disclosed value is retained rather than being overwritten by an "undisclosed" record.

---

## Refresh Now vs Reset Deal Store

### Refresh Now

**Refresh Now** is the normal operating action.

It:

1. Retrieves the latest public articles.
2. Identifies articles that have not previously been processed.
3. Scores and filters new articles.
4. Removes near-duplicate coverage.
5. Matches new evidence to existing deals.
6. Creates genuinely new deal records when appropriate.
7. Updates existing deals when additional evidence is found.
8. Regenerates the newsletter.

If no new articles are available:

- New articles = 0
- New deals = 0
- Existing tracked deals remain visible

### Reset Deal Store

**Reset Deal Store** is a testing/demo control rather than a normal operating action.

It clears the locally persisted article and deal state so the current source universe can be treated as a fresh first run.

Recommended clean-demo flow:

**Reset Deal Store → Refresh Now**

---

## User Interface

### Newsletter

The newsletter is structured as a short investment intelligence brief containing:

- Screen snapshot
- Executive Take
- Key Themes
- Key Developments
- Deal type
- Status
- Disclosed value
- Confidence
- Evidence/source information
- What to Watch
- Method Note

### Deal Monitor

Shows the persistent tracked deal records, including:

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

Shows the counts from the latest refresh:

**Retrieved → new articles → FMCG/relevance/credibility matches → duplicates → evidence-only articles → new deals → updated deals → newsletter**

---

## Methodology and Limitations

- Public-source discovery is not guaranteed to be exhaustive.
- The system depends on the configured public news/RSS sources.
- Deal status is based on the wording and evidence available in cited public sources.
- Undisclosed transaction consideration is not estimated.
- Source credibility is a heuristic rather than independent fact verification.
- Relevance thresholds are configurable and can affect the number of articles that pass.
- Near-duplicate detection uses a similarity threshold and may not catch every semantically equivalent article.
- The application is an intelligence-screening tool, not investment advice or a replacement for primary-source diligence.

---

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Repository Structure

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

## Final Demo Flow

1. Open the Streamlit application.
2. Set the look-back window and screening thresholds.
3. Click **Refresh Now**.
4. Review **Newsletter → Deal Monitor → Article Evidence → Agent Trace**.
5. Use **Reset Deal Store** only when demonstrating a clean first run.
6. Provide the structured newsletter Excel and raw CSV as separate submission artifacts.

---

