# FMCG Deal Intelligence Newsletter Agent

A lightweight Streamlit application that screens public news for recent FMCG M&A and investment activity, tracks confirmed deal records, preserves evidence, and turns the results into a concise investment-style newsletter.

## What the app does

**Ingestion → cleaning → relevance scoring → credibility → filtering → de-duplication → deal matching → newsletter → exports**

### 1. Ingestion
The application uses public RSS/news sources through the existing ingestion layer. A look-back window controls the screening period.

### 2. FMCG classification
Articles are checked for FMCG/consumer signals such as food, beverages, beauty, personal care, wellness, D2C and packaged foods. Clear non-FMCG categories can override generic consumer language.

### 3. Relevance + credibility
Each new article receives a relevance score and a source-credibility score. Only articles above the user-selected thresholds continue through the main screening path.

The credibility score is a source-quality heuristic, not independent fact verification.

### 4. Near-duplicate removal
Relevant articles are compared using headline similarity. A similarity of **≥ 0.86** is treated as a near duplicate, retaining the stronger-ranked article.

### 5. Deal extraction and tracking
The pipeline extracts buyer/investor, target, deal type, value and status from clear deal-language patterns. Existing deals are matched using a deal fingerprint so additional evidence can update an existing record instead of creating a duplicate deal.

Reported/potential processes are kept distinct from announced or completed transactions.

## UI

### Newsletter
The newsletter is structured like a short investment intelligence brief:

- Screen snapshot
- Executive Take
- Key Developments
- Deal metadata: type, status, value and confidence
- Evidence/source links
- What to Watch
- Method note

### Deal Monitor
Shows the persistent deal store, including buyer/investor, target, type, status, value, confidence, source count and last update.

### Article Evidence
Shows the screened article evidence and scoring fields.

### Agent Trace
Shows the pipeline steps and counts from the latest refresh.

## Refresh Now vs Reset Deal Store

**Refresh Now** runs the live public-news screen. It does not intentionally erase existing tracked deals; unseen articles are processed and matching deals can be updated.

**Reset Deal Store** clears the locally persisted article/deal state and starts a clean store. Use it only when you want a fresh first-run demonstration or intentionally want to discard the current state.

## Exports

The application can export the current screen as:

- `FMCG_Deal_Intelligence_Newsletter.md` — readable newsletter
- `fmcg_deal_tracker.csv` — structured deal tracker
- `fmcg_article_evidence.csv` — article-level evidence
- `FMCG_Deal_Intelligence.xlsx` — workbook containing Deal Tracker, Article Evidence and Newsletter sheets
- `state.json` — persistent application state remains locally managed by the pipeline

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Repository structure

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

## Methodology and limitations

- Public-source discovery is not guaranteed to be exhaustive.
- Deal status is based on wording available in the cited source.
- Undisclosed consideration is not estimated.
- Source credibility is a heuristic rather than a fact-checking system.
- The application is an intelligence-screening tool, not investment advice or a replacement for primary-source diligence.

## Submission checklist

- [x] Live Streamlit UI
- [x] Public-source ingestion
- [x] FMCG relevance filtering
- [x] Source credibility scoring
- [x] Near-duplicate removal
- [x] Persistent deal tracking
- [x] Evidence view
- [x] Agent trace
- [x] Professional newsletter structure
- [x] CSV / Excel / Markdown exports
- [x] README documenting architecture, methodology and limitations

## Final demo flow

1. Start the Streamlit app.
2. Set the look-back and thresholds.
3. Click **Refresh Now**.
4. Review **Newsletter → Deal Monitor → Article Evidence → Agent Trace**.
5. Download the CSV/Excel/Newsletter outputs.
6. For a completely clean demonstration, use **Reset Deal Store** first and then run **Refresh Now**.
