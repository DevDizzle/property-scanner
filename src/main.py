"""Property Scanner MVP — Main Pipeline.

Usage:
    python -m src.main --zip 33301 --limit 50
    python -m src.main --zip 33301,33304,33316 --limit 200
    python -m src.main --zip 33301 --skip-enrich  # scrape + filter only (no API costs)
"""
import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from src.config import get_config
from src.scrapers.redfin import scrape_zip_code
from src.scrapers.demo_data import generate_demo_listings, mock_enrich_listing
from src.scoring.heuristic import preliminary_filter, calculate_score
from src.enrichment.rentcast import enrich_listing
from src.enrichment.tax_reset import calculate_post_sale_tax, estimate_net_cash_flow
from src.ai.deal_summary import generate_deal_summary
from src.storage.bigquery import (
    init_tables,
    write_raw_listings,
    write_enriched_listings,
    write_scored_listings,
    write_daily_report,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("scanner")

OUTPUT_DIR = Path(__file__).parent.parent / "data"


def run_pipeline(
    zip_codes: list[str],
    limit: int = 200,
    skip_enrich: bool = False,
    skip_ai: bool = False,
    ai_top_n: int = 5,
    is_demo: bool = False,
    skip_bq: bool = False,
) -> list[dict]:
    """Run the full property scanning pipeline.
    
    Steps:
    1. Scrape listings from Redfin
    2. Preliminary filter (free — no API calls)
    3. Enrich with RentCast (paid — top 20% only)
    4. Calculate post-sale tax reset
    5. Score with full heuristic
    6. AI deal summaries (top N)
    7. Output results
    """
    config = get_config()
    all_listings = []
    
    if not skip_bq:
        try:
            init_tables()
        except Exception as e:
            logger.error(f"BQ init failed: {e}")
            skip_bq = True

    
    # Step 1: Scrape
    logger.info(f"=== STEP 1: Scraping {len(zip_codes)} zip codes ===")
    for zip_code in zip_codes:
        if is_demo:
            listings = generate_demo_listings(zip_code, count=limit)
        else:
            listings = asyncio.run(scrape_zip_code(zip_code, limit=limit))
        logger.info(f"  {zip_code}: {len(listings)} listings")
        all_listings.extend(listings)
    
    if not all_listings:
        logger.error("No listings found. Check ScrapingBee key and zip codes.")
        return []
    
    logger.info(f"Total raw listings: {len(all_listings)}")
    
    # Save raw scrape
    _save_output(all_listings, "raw_listings")
    if not skip_bq:
        try:
            write_raw_listings(all_listings)
        except Exception as e:
            logger.error(f"BQ write_raw_listings failed: {e}")
    
    # Step 2: Preliminary filter
    logger.info("=== STEP 2: Preliminary filter (top 20%) ===")
    filter_pct = config["pipeline"]["filter_top_pct"]
    filtered = preliminary_filter(all_listings, top_pct=filter_pct)
    logger.info(f"Passed filter: {len(filtered)} listings")
    
    _save_output(filtered, "filtered_listings")
    
    if skip_enrich:
        logger.info("Skipping enrichment (--skip-enrich). Done.")
        return filtered
    
    # Step 3: Enrich with RentCast
    logger.info(f"=== STEP 3: Enriching {len(filtered)} listings via RentCast ===")
    enriched = []
    for i, listing in enumerate(filtered):
        logger.info(f"  Enriching {i+1}/{len(filtered)}: {listing['address']}")
        try:
            if is_demo:
                listing = mock_enrich_listing(listing)
            else:
                listing = enrich_listing(listing)
            enriched.append(listing)
        except Exception as e:
            logger.warning(f"  Enrichment failed for {listing['address']}: {e}")
            enriched.append(listing)  # Keep with partial data
    
    # Step 4: Post-sale tax reset
    logger.info("=== STEP 4: Calculating post-sale tax reset ===")
    for listing in enriched:
        if listing.get("price") and listing.get("zip_code"):
            tax_data = calculate_post_sale_tax(
                listing_price=listing["price"],
                zip_code=listing["zip_code"],
                current_tax_bill=listing.get("current_tax"),  # From county data if available
            )
            listing["tax_reset"] = tax_data
            
            # Calculate net cash flow with real tax numbers
            if listing.get("rent_estimate"):
                cash_flow = estimate_net_cash_flow(listing, tax_data)
                listing.update(cash_flow)
    
    # Step 5: Score
    logger.info("=== STEP 5: Scoring ===")
    for listing in enriched:
        calculate_score(
            listing,
            tax_data=listing.get("tax_reset"),
        )
    
    # Sort by score
    enriched.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    _save_output(enriched, "scored_listings")
    if not skip_bq:
        try:
            write_enriched_listings(enriched)
            write_scored_listings(enriched)
        except Exception as e:
            logger.error(f"BQ write_scored_listings failed: {e}")
    
    # Step 6: AI summaries for top N
    if not skip_ai:
        top_n = config["pipeline"].get("ai_summary_top_n", ai_top_n)
        logger.info(f"=== STEP 6: AI summaries for top {top_n} ===")
        for listing in enriched[:top_n]:
            summary = generate_deal_summary(listing, listing.get("tax_reset"))
            listing["ai_summary"] = summary
            logger.info(f"  {listing['address']}: Score {listing['score']}")
    
    # Final output
    _save_output(enriched, "final_results")
    
    if not skip_bq:
        try:
            avg_score = sum(l.get("score", 0) for l in enriched) / len(enriched) if enriched else 0
            passed_filter = len(filtered)
            
            report_meta = {
                "report_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "zip_codes": zip_codes,
                "total_scanned": len(all_listings),
                "total_passed_filter": passed_filter,
                "avg_score": round(avg_score, 2),
                "is_demo": is_demo,
            }
            write_daily_report(report_meta)
        except Exception as e:
            logger.error(f"BQ write_daily_report failed: {e}")
    
    # Print top 10
    logger.info("\n" + "="*80)
    logger.info("TOP 10 DEALS")
    logger.info("="*80)
    for i, listing in enumerate(enriched[:10]):
        logger.info(
            f"\n#{i+1} | Score: {listing.get('score', 'N/A')}/10 | "
            f"{listing['address']}, {listing['city']} {listing['zip_code']}\n"
            f"  Price: ${listing.get('price', 0):,.0f} | "
            f"Rent: ${listing.get('rent_estimate', 0):,.0f}/mo | "
            f"Yield: {listing.get('gross_yield_pct', 0):.1f}% | "
            f"DOM: {listing.get('dom', 'N/A')}\n"
            f"  Post-Tax: ${listing.get('tax_reset', {}).get('post_sale_tax_annual', 0):,.0f}/yr | "
            f"Net CF: ${listing.get('net_monthly', 0):,.0f}/mo | "
            f"CoC: {listing.get('cash_on_cash_pct', 0):.1f}%"
        )
        if listing.get("ai_summary"):
            logger.info(f"  AI: {listing['ai_summary'][:200]}...")
    
    return enriched


def _save_output(data: list[dict], name: str):
    """Save pipeline output to JSON."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filepath = OUTPUT_DIR / f"{name}_{date_str}.json"
    
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    
    logger.info(f"Saved {len(data)} records to {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Property Scanner MVP")
    parser.add_argument("--zip", required=True, help="Zip codes (comma-separated)")
    parser.add_argument("--limit", type=int, default=200, help="Max listings per zip")
    parser.add_argument("--skip-enrich", action="store_true", help="Skip RentCast enrichment")
    parser.add_argument("--skip-ai", action="store_true", help="Skip AI summaries")
    parser.add_argument("--ai-top-n", type=int, default=5, help="AI summaries for top N")
    parser.add_argument("--demo", action="store_true", help="Run with mock data (no API costs)")
    parser.add_argument("--skip-bq", action="store_true", help="Skip BigQuery writes")
    
    args = parser.parse_args()
    zip_codes = [z.strip() for z in args.zip.split(",")]
    
    results = run_pipeline(
        zip_codes=zip_codes,
        limit=args.limit,
        skip_enrich=args.skip_enrich,
        skip_ai=args.skip_ai,
        ai_top_n=args.ai_top_n,
        is_demo=args.demo,
        skip_bq=args.skip_bq,
    )
    
    logger.info(f"\nPipeline complete. {len(results)} properties scored.")


if __name__ == "__main__":
    main()
