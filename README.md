# FMCG Deal Intelligence Agent — V2

**Pipeline:** Refresh Now → ingestion → cleaning → relevance scoring → credibility → article de-duplication → deal matching → persistent deal store → newsletter.

## What makes it incremental?
The app remembers previously seen article URLs and deal records. On each refresh it processes new articles, filters them, removes near-duplicates, then matches the surviving article to an existing transaction using **Buyer + Target + Deal Type**. Matching articles update the existing deal rather than creating a new newsletter item.

## Relevance
Weighted deal terms (acquisition, merger, stake, investment, funding, etc.) are combined with FMCG terms (FMCG, consumer goods, personal care, beauty, packaged food, D2C, wellness, etc.) and reduced for noise terms such as share price, earnings and commodity prices.

## Credibility
Primary company/investor/government sources receive the highest score; established financial publications receive high scores; unknown sources receive a lower default score. This is a source-quality heuristic, not independent fact verification.

## De-duplication
Cleaned headlines are compared with `SequenceMatcher`; similarity >= 0.86 is treated as a near-duplicate. Deal-level matching then groups articles around the same transaction using Buyer + Target + Deal Type.

## UI
- **Newsletter:** business-ready executive output
- **Deal Monitor:** structured transaction tracker
- **Article Evidence:** source-level scores and links
- **Agent Trace:** visible steps executed by Refresh Now

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

The app is designed for Streamlit Community Cloud. The final GitHub and deployed Streamlit URLs must be added after publishing/deployment; they should not be fabricated.
