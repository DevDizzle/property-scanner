# PROMPT: Build Property Scanner MVP

## Context
You are building a property scanner MVP for BPM REIA (Real Estate Investors Association). This is a deal-sourcing tool that scans South Florida listings daily, scores them by investment attractiveness, and surfaces the best deals with post-sale tax reset calculations.

**Think of it as GammaRips (options flow scanner) applied to real estate.**

The project scaffold already exists at `/home/user/property-scanner/`. Read ALL existing files before writing any code. The architecture, schemas, and patterns are already defined.

## Existing Files (READ THESE FIRST)
- `README.md` — Project overview and pipeline
- `config/config.example.yaml` — Configuration structure
- `requirements.txt` — Dependencies
- `src/config.py` — Config loader (done)
- `src/scrapers/redfin.py` — Redfin scraper via ScrapingBee (done, needs testing)
- `src/enrichment/rentcast.py` — RentCast API client (done, needs testing)
- `src/enrichment/tax_reset.py` — Post-sale tax reset calculator with FL millage rates (done)
- `src/scoring/heuristic.py` — Weighted scoring model (done)
- `src/ai/deal_summary.py` — Gemini deal summaries (done)
- `src/main.py` — Pipeline orchestrator (done, needs testing)

## Full Spec
Read the full spec at: `/home/user/.openclaw/workspace/property-scanner/SPEC-PROPERTY-SCANNER-MVP.md`

This has everything: data sources, feature engineering, scoring model, architecture, cost estimates, competitive landscape, and the 7-day sprint plan.

## What Needs To Be Built / Fixed

### Priority 1: Make the Pipeline Actually Run
1. **Install dependencies**: `pip install -r requirements.txt`
2. **Create config.yaml** from config.example.yaml (API keys will be added by Evan)
3. **Test the Redfin scraper** — The CSV download endpoint may need URL tweaking. Redfin changes their URLs. If CSV fails, make the HTML parser work with BeautifulSoup. Add `beautifulsoup4` and `lxml` to requirements if needed.
4. **Add a mock/demo mode** — Since we may not have API keys yet, create `src/scrapers/demo_data.py` that generates 50 realistic Fort Lauderdale (33301) listings so we can test the full pipeline without ScrapingBee. Use realistic South FL prices ($200K-$800K), sqft (1000-3000), beds (2-5), DOM (5-180), etc.
5. **Test the full pipeline end-to-end** with demo data: `python -m src.main --zip 33301 --demo`

### Priority 2: BigQuery Integration
1. **Create BQ table schemas** in `src/storage/bigquery.py`:
   - `property_scanner.raw_listings` — all scraped listings
   - `property_scanner.enriched_listings` — after RentCast + tax reset
   - `property_scanner.scored_listings` — final scored output
   - `property_scanner.daily_reports` — report metadata
2. **Add BQ write functions** — write pipeline outputs to BQ at each stage
3. **GCP project**: `profitscout-fida8`, region: `us-central1`
4. Use `google.cloud.bigquery` client with default credentials

### Priority 3: Streamlit Dashboard (THE DEMO)
This is what Anish will see Thursday. Build `src/dashboard/app.py` using Streamlit.

**Layout:**
- Header: "BPM REIA — AI Deal Sourcing Feed" with date
- Filters sidebar: price range, beds, min score, zip code
- Main area: sortable table of top 20 deals with key metrics
- Expandable cards for each property showing:
  - Score breakdown (yield/discount/urgency/risk as a radar chart or bar)
  - Tax Reset Impact: current tax vs post-sale tax (BIG, BOLD, this is the mic drop)
  - Cash Flow Analysis: gross rent, expenses breakdown, net monthly, cash-on-cash %
  - AI Deal Summary (from Gemini)
  - Link to Redfin listing
- Summary stats at top: total scanned, avg score, # meeting 1% rule, avg tax increase %

**Styling:**
- Dark theme preferred
- Clean, institutional look — this is for investors not consumers
- BPM REIA branding can be added later

**Run with:** `streamlit run src/dashboard/app.py`

### Priority 4: Email Digest Template
Build `src/delivery/email_digest.py`:
- Jinja2 HTML template at `templates/daily_digest.html`
- "BPM Daily Deal Feed" header
- Date + summary stats
- Top 10 properties with score, price, rent estimate, net cash flow, tax reset impact
- Each property links to Redfin
- Professional email design (dark or clean white)
- SendGrid integration for delivery
- Function: `send_daily_digest(listings, recipients)`

### Priority 5: Cloud Run Deployment
Build `Dockerfile` and `cloudbuild.yaml`:
- Same pattern as GammaRips overnight-scanner
- Cloud Run service name: `property-scanner`
- Triggered daily at 6 AM EST
- POST to `/scan` with optional `{"zip_codes": ["33301"], "limit": 200}`
- Health check at `/health`
- Use `src/server.py` with Flask or FastAPI

## Technical Requirements
- Python 3.11+
- All GCP auth via default credentials (already configured on this machine)
- Error handling: don't crash the pipeline if one listing fails enrichment
- Logging: use Python logging, structured output
- The pipeline should be idempotent — running twice on same day overwrites, doesn't duplicate

## Demo Data Spec (for mock mode)
Generate 50 listings in 33301 (Fort Lauderdale) with realistic data:
- Mix of SFR and multi-family
- Prices: $200K-$800K (weighted toward $300-500K)
- SqFt: 1000-3000
- Beds: 2-5, Baths: 1-3
- Year built: 1960-2020
- DOM: 5-180 (some fresh, some stale)
- Some with price drops (1-3 drops)
- Realistic addresses (use real Fort Lauderdale street names)
- Include some obviously good deals (high yield, long DOM, price drops) and some obviously bad deals (overpriced, new listing, no margin)

## Key Business Logic
- **Post-sale tax reset** is THE differentiator. Every property card must show: "Listed Tax: $X/yr → Your Tax: $Y/yr (↑Z%)" prominently. Most investors get burned by this.
- **1% Rule**: Monthly rent ≥ 1% of purchase price = good rental
- **Gross Yield**: (Annual rent / Price) × 100. Above 8% = solid.
- **Preliminary filter** saves 80% of API costs by only enriching top 20%
- **Scoring weights**: Yield 25%, Discount 25%, Urgency 25%, Risk 25%

## DO NOT
- Do not change the existing file structure or rename modules
- Do not remove any existing code — extend it
- Do not hardcode API keys — use config.yaml or env vars
- Do not use frameworks we don't need — keep it simple

## RUN ORDER
1. Read all existing files
2. Fix/enhance scraper if needed
3. Build demo data generator
4. Test pipeline with demo data
5. Build Streamlit dashboard
6. Build BQ integration
7. Build email digest
8. Build Cloud Run deployment files
9. Test everything end-to-end

## Success Criteria
Running `python -m src.main --zip 33301 --demo` should:
1. Generate 50 mock listings
2. Filter to top 10 (20%)
3. Calculate tax reset for all 10
4. Score all 10
5. Generate AI summaries for top 5
6. Save JSON outputs to data/
7. Print top 10 leaderboard to console

Running `streamlit run src/dashboard/app.py` should:
1. Load latest scored data from data/
2. Display interactive dashboard with filters
3. Show tax reset impact prominently on every card
4. Look professional enough to demo to a REIA president on Thursday
