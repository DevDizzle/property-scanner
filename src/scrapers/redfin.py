"""Redfin listing scraper via ScrapingBee."""
import json
import re
import logging
from datetime import datetime
from typing import Optional

from scrapingbee import ScrapingBeeClient
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_config

logger = logging.getLogger(__name__)


def get_client() -> ScrapingBeeClient:
    config = get_config()
    return ScrapingBeeClient(api_key=config["apis"]["scrapingbee"]["api_key"])


def build_redfin_url(zip_code: str, min_price: int = 100000, max_price: int = 1000000) -> str:
    """Build Redfin search URL for a zip code with filters."""
    # Redfin filter URL format for SFR + multi-family in price range
    return (
        f"https://www.redfin.com/zipcode/{zip_code}"
        f"/filter/property-type=house+multifamily,"
        f"min-price={min_price},max-price={max_price},"
        f"include=sold-3mo"
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def scrape_listings_page(client: ScrapingBeeClient, url: str) -> str:
    """Scrape a single Redfin page via ScrapingBee."""
    response = client.get(
        url,
        params={
            "render_js": "true",
            "wait": 3000,
            "premium_proxy": "true",
            "country_code": "us",
        }
    )
    if response.status_code != 200:
        raise Exception(f"ScrapingBee returned {response.status_code}")
    return response.text


def parse_redfin_download_url(zip_code: str) -> str:
    """Build Redfin CSV download URL — more reliable than HTML parsing."""
    # Redfin offers a CSV download endpoint for search results
    return (
        f"https://www.redfin.com/stingray/api/gis-csv?"
        f"al=1&has_deal=false&has_dishwasher=false&has_laundry_facility=false"
        f"&has_laundry_hookups=false&has_parking=false&has_pool=false"
        f"&has_short_term_rental=false&include_pending_homes=false"
        f"&isRentals=false&is_senior_living=false"
        f"&num_homes=350&ord=redfin-recommended-asc"
        f"&page_number=1&pool=false&region_id={zip_code}&region_type=2"
        f"&sf=1,2,3,5,6,7&status=9&uipt=1,2&v=8"
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def scrape_csv_download(client: ScrapingBeeClient, zip_code: str) -> str:
    """Try Redfin's CSV download endpoint — structured data, no HTML parsing."""
    url = parse_redfin_download_url(zip_code)
    response = client.get(
        url,
        params={
            "render_js": "false",
            "premium_proxy": "true",
            "country_code": "us",
        }
    )
    if response.status_code != 200:
        raise Exception(f"Redfin CSV download returned {response.status_code}")
    return response.text


def parse_redfin_html(html: str) -> list[dict]:
    """Parse Redfin search results HTML into listing dicts.
    
    Fallback if CSV download doesn't work. Extracts from Redfin's
    data attributes and structured elements.
    """
    listings = []
    
    # Redfin embeds listing data in script tags as JSON
    # Look for the __reactServerState or similar data blob
    json_pattern = r'window\.__reactServerState\s*=\s*({.*?});'
    match = re.search(json_pattern, html, re.DOTALL)
    
    if match:
        try:
            data = json.loads(match.group(1))
            # Navigate Redfin's data structure to extract listings
            # This structure changes — adapt as needed
            homes = _extract_homes_from_state(data)
            for home in homes:
                listing = _normalize_redfin_home(home)
                if listing:
                    listings.append(listing)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse Redfin JSON state: {e}")
    
    if not listings:
        logger.warning("JSON parsing failed, falling back to regex extraction")
        listings = _regex_fallback_parse(html)
    
    return listings


def parse_redfin_csv(csv_text: str) -> list[dict]:
    """Parse Redfin CSV download into listing dicts."""
    import csv
    from io import StringIO
    
    listings = []
    reader = csv.DictReader(StringIO(csv_text))
    
    for row in reader:
        try:
            listing = {
                "source": "redfin",
                "address": row.get("ADDRESS", "").strip(),
                "city": row.get("CITY", "").strip(),
                "state": row.get("STATE OR PROVINCE", "FL"),
                "zip_code": row.get("ZIP OR POSTAL CODE", "").strip(),
                "price": _safe_float(row.get("PRICE")),
                "beds": _safe_int(row.get("BEDS")),
                "baths": _safe_float(row.get("BATHS")),
                "sqft": _safe_float(row.get("SQUARE FEET")),
                "lot_sqft": _safe_float(row.get("LOT SIZE")),
                "year_built": _safe_int(row.get("YEAR BUILT")),
                "dom": _safe_int(row.get("DAYS ON MARKET")),
                "property_type": row.get("PROPERTY TYPE", "").strip(),
                "url": row.get("URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)", "").strip(),
                "latitude": _safe_float(row.get("LATITUDE")),
                "longitude": _safe_float(row.get("LONGITUDE")),
                "status": row.get("STATUS", "").strip(),
                "listing_id": row.get("MLS#", "").strip(),
                "price_per_sqft": None,
                "scraped_at": datetime.utcnow().isoformat(),
            }
            
            # Calculate price per sqft
            if listing["price"] and listing["sqft"] and listing["sqft"] > 0:
                listing["price_per_sqft"] = round(listing["price"] / listing["sqft"], 2)
            
            # Only include if we have minimum viable data
            if listing["price"] and listing["address"]:
                listings.append(listing)
                
        except Exception as e:
            logger.warning(f"Failed to parse CSV row: {e}")
            continue
    
    logger.info(f"Parsed {len(listings)} listings from Redfin CSV")
    return listings


def _safe_float(val) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", "").replace("$", ""))
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> Optional[int]:
    f = _safe_float(val)
    return int(f) if f is not None else None


def _extract_homes_from_state(data: dict) -> list:
    """Navigate Redfin's server state to find home listings."""
    # Redfin nests data differently across versions
    # Common paths to try
    paths = [
        lambda d: d.get("ReactServerAgent", {}).get("dataCache", {}),
        lambda d: d.get("pageData", {}).get("homes", []),
    ]
    for path_fn in paths:
        try:
            result = path_fn(data)
            if result:
                return result if isinstance(result, list) else [result]
        except (KeyError, TypeError):
            continue
    return []


def _normalize_redfin_home(home: dict) -> Optional[dict]:
    """Normalize a Redfin home object to our standard schema."""
    try:
        return {
            "source": "redfin",
            "address": home.get("streetLine", {}).get("value", ""),
            "city": home.get("city", ""),
            "state": home.get("state", "FL"),
            "zip_code": home.get("zip", ""),
            "price": home.get("price", {}).get("value"),
            "beds": home.get("beds"),
            "baths": home.get("baths"),
            "sqft": home.get("sqFt", {}).get("value"),
            "lot_sqft": home.get("lotSize", {}).get("value"),
            "year_built": home.get("yearBuilt", {}).get("value"),
            "dom": home.get("dom", {}).get("value"),
            "property_type": home.get("propertyType"),
            "url": f"https://www.redfin.com{home.get('url', '')}",
            "latitude": home.get("latLong", {}).get("latitude"),
            "longitude": home.get("latLong", {}).get("longitude"),
            "status": home.get("listingType", "active"),
            "listing_id": home.get("mlsId", {}).get("value", ""),
            "price_per_sqft": None,
            "scraped_at": datetime.utcnow().isoformat(),
        }
    except Exception:
        return None


def _regex_fallback_parse(html: str) -> list[dict]:
    """Last resort: regex patterns for Redfin listing cards."""
    # This is fragile but serves as a fallback
    listings = []
    # Redfin listing cards have data-url attributes
    card_pattern = r'class="[^"]*HomeCard[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>'
    # Simplified — in production we'd use BeautifulSoup
    logger.warning("Regex fallback parse — results may be incomplete")
    return listings


async def scrape_zip_code(zip_code: str, limit: int = 200) -> list[dict]:
    """Main entry: scrape all active listings for a zip code.
    
    Strategy:
    1. Try CSV download (structured, reliable)
    2. Fall back to HTML scraping if CSV fails
    """
    config = get_config()
    client = get_client()
    price_range = config["targets"]["price_range"]
    
    logger.info(f"Scraping zip {zip_code} (${price_range['min']:,}-${price_range['max']:,})")
    
    # Try CSV first
    try:
        csv_text = scrape_csv_download(client, zip_code)
        listings = parse_redfin_csv(csv_text)
        if listings:
            logger.info(f"CSV download success: {len(listings)} listings for {zip_code}")
            return listings[:limit]
    except Exception as e:
        logger.warning(f"CSV download failed for {zip_code}: {e}")
    
    # Fall back to HTML
    try:
        url = build_redfin_url(zip_code, price_range["min"], price_range["max"])
        html = scrape_listings_page(client, url)
        listings = parse_redfin_html(html)
        logger.info(f"HTML scrape: {len(listings)} listings for {zip_code}")
        return listings[:limit]
    except Exception as e:
        logger.error(f"All scraping methods failed for {zip_code}: {e}")
        return []
