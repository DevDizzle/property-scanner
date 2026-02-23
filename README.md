# Property Scanner MVP — BPM REIA Deal Sourcing Tool

**The GammaRips playbook applied to real estate.**

Scans South Florida listings daily → scores by investment attractiveness → surfaces top deals with post-sale tax reset calculations.

## Stack
- Python 3.11+
- BigQuery (dataset: property_scanner)
- RentCast API (rent/value estimates)
- ScrapingBee + Redfin (listing data)
- Gemini (AI deal summaries)
- Cloud Run (daily pipeline)
- Firebase (dashboard) / SendGrid (email digest)

## Quick Start
```bash
pip install -r requirements.txt
cp config/config.example.yaml config/config.yaml  # Add API keys
python -m src.main --zip 33301 --limit 50
```

## Pipeline
1. **Scrape** — Redfin listings via ScrapingBee
2. **Filter** — Preliminary heuristic (top 20% pass)
3. **Enrich** — RentCast rent/value estimates + county tax data
4. **Score** — Weighted heuristic (yield, discount, urgency, risk)
5. **Analyze** — Gemini deal summaries for top properties
6. **Deliver** — Dashboard + email digest

## Project: profitscout-fida8
## BQ Dataset: property_scanner
