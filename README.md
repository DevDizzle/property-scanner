# 🏠 Property Scanner — AI-Powered Real Estate Deal Sourcing

Scans active listings, enriches with rent estimates and post-sale tax projections, scores every deal on a 10-point scale, and generates AI deal summaries — in under 2 minutes.

Built for real estate investors who want to find deals faster and avoid tax traps.

## What It Does

1. **Scan** — Pulls active listings from Redfin for any US zip code
2. **Enrich** — Gets rent estimates from 15+ comparable properties via RentCast, plus current property tax data
3. **Tax Reset** — Calculates post-sale tax reassessment using county millage rates (Florida focus). Flags properties where taxes jump 50%+ after purchase — or where they actually decrease
4. **Score** — Ranks every deal 1-10 across four pillars: Yield (40%), Discount to Value (30%), Urgency (15%), Risk (15%)
5. **AI Analysis** — Gemini writes a deal verdict for top properties: buy, pass, or dig deeper
6. **Dashboard** — Streamlit app with deal cards, tax shock analysis, and filters

## Key Features

- **Tax Shock Detection** — Most investors calculate cash flow using the seller's old tax bill. This tool projects your REAL post-sale taxes before you make an offer.
- **15+ Rent Comps Per Property** — Not Zillow estimates. Actual comparable rental data with high/low ranges.
- **Cash Flow Modeling** — Net monthly cash flow after taxes, insurance, management, and maintenance.
- **Discount to Value** — Shows how far below market value each listing sits, with estimated value ranges.
- **AI Deal Summaries** — Plain-English analysis of every deal, not just numbers.

## Quick Start

```bash
# Clone and install
git clone https://github.com/DevDizzle/property-scanner.git
cd property-scanner
pip install -r requirements.txt

# Configure
cp config/config.example.yaml config/config.yaml
# Add your API keys: RentCast, ScrapingBee, GCP credentials

# Run the pipeline
python -m src.main --zip 33301 --limit 50

# Launch the dashboard
streamlit run src/dashboard/app.py
```

## Stack

| Component | Technology |
|-----------|-----------|
| Scraping | ScrapingBee + Redfin CSV/HTML |
| Rent Data | RentCast API |
| Tax Calculations | County millage rates (90+ South FL zips) |
| AI Summaries | Gemini (Vertex AI) |
| Scoring | Custom weighted heuristic |
| Storage | BigQuery |
| Dashboard | Streamlit |
| Deployment | Google Cloud Run |

## Pipeline Architecture

```
Redfin (ScrapingBee) → Filter (top 20%) → RentCast Enrichment → Tax Reset Calculator → Scoring Engine → Gemini AI Analysis → BigQuery → Streamlit Dashboard
```

## Scoring Pillars

| Pillar | Weight | What It Measures |
|--------|--------|-----------------|
| **Yield** | 40% | Cash-on-cash return, gross yield, cap rate |
| **Discount** | 30% | How far below estimated market value |
| **Urgency** | 15% | Days on market, price cuts, seller motivation |
| **Risk** | 15% | Tax reset impact, maintenance flags |

## Sample Output

```
#1 | Score: 7.8/10 | 125 Isle Of Venice Dr #10, Fort Lauderdale 33301
   Price: $229,000 | Rent: $2,190/mo | Yield: 11.5% | DOM: 91
   Net CF: +$920/mo | CoC: 17.2% | Discount: 31% below market
   Tax Shock: -7.9% (taxes DECREASE post-sale)
   AI: "BUY. Strong rental demand, motivated seller, taxes decrease post-sale."
```

## Configuration

Copy `config/config.example.yaml` and add your API keys:

- **RentCast** — Rent and value estimates ([rentcast.io](https://rentcast.io))
- **ScrapingBee** — Web scraping proxy ([scrapingbee.com](https://scrapingbee.com))
- **GCP Service Account** — BigQuery access + Gemini (Vertex AI)

## License

MIT

## Author

**Evan Parra** — [evanparra.ai](https://evanparra.ai)
