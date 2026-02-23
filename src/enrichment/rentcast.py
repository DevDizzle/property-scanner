"""RentCast API client for rent estimates and property data."""
import logging
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_config

logger = logging.getLogger(__name__)

BASE_URL = "https://api.rentcast.io/v1"


def _headers() -> dict:
    config = get_config()
    return {
        "Accept": "application/json",
        "X-Api-Key": config["apis"]["rentcast"]["api_key"],
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
def get_rent_estimate(
    address: str,
    beds: Optional[int] = None,
    baths: Optional[float] = None,
    sqft: Optional[float] = None,
    property_type: str = "Single Family",
) -> Optional[dict]:
    """Get rent estimate for a property.
    
    Returns:
        {
            "rent": float,          # estimated monthly rent
            "rent_low": float,      # low range
            "rent_high": float,     # high range
            "comp_count": int,      # number of comps used
        }
    """
    params = {"address": address}
    if beds:
        params["bedrooms"] = beds
    if baths:
        params["bathrooms"] = baths
    if sqft:
        params["squareFootage"] = int(sqft)
    if property_type:
        params["propertyType"] = property_type
    
    try:
        resp = requests.get(
            f"{BASE_URL}/avm/rent/long-term",
            headers=_headers(),
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        
        return {
            "rent": data.get("rent"),
            "rent_low": data.get("rentRangeLow"),
            "rent_high": data.get("rentRangeHigh"),
            "comp_count": len(data.get("comparables", [])),
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            logger.warning("RentCast rate limit hit")
            raise  # Let tenacity retry
        logger.error(f"RentCast error for {address}: {e}")
        return None
    except Exception as e:
        logger.error(f"RentCast request failed for {address}: {e}")
        return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
def get_value_estimate(
    address: str,
    beds: Optional[int] = None,
    baths: Optional[float] = None,
    sqft: Optional[float] = None,
    property_type: str = "Single Family",
) -> Optional[dict]:
    """Get property value estimate (AVM).
    
    Returns:
        {
            "value": float,
            "value_low": float,
            "value_high": float,
            "comp_count": int,
        }
    """
    params = {"address": address}
    if beds:
        params["bedrooms"] = beds
    if baths:
        params["bathrooms"] = baths
    if sqft:
        params["squareFootage"] = int(sqft)
    if property_type:
        params["propertyType"] = property_type
    
    try:
        resp = requests.get(
            f"{BASE_URL}/avm/value",
            headers=_headers(),
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        
        return {
            "value": data.get("price"),
            "value_low": data.get("priceRangeLow"),
            "value_high": data.get("priceRangeHigh"),
            "comp_count": len(data.get("comparables", [])),
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            logger.warning("RentCast rate limit hit")
            raise
        logger.error(f"RentCast value error for {address}: {e}")
        return None
    except Exception as e:
        logger.error(f"RentCast value request failed for {address}: {e}")
        return None


def enrich_listing(listing: dict) -> dict:
    """Enrich a single listing with RentCast data.
    
    Adds rent_estimate, value_estimate, and derived metrics.
    """
    address = f"{listing['address']}, {listing['city']}, {listing['state']} {listing['zip_code']}"
    
    # Get rent estimate
    rent_data = get_rent_estimate(
        address=address,
        beds=listing.get("beds"),
        baths=listing.get("baths"),
        sqft=listing.get("sqft"),
        property_type=listing.get("property_type", "Single Family"),
    )
    
    if rent_data:
        listing["rent_estimate"] = rent_data["rent"]
        listing["rent_low"] = rent_data["rent_low"]
        listing["rent_high"] = rent_data["rent_high"]
        listing["rent_comp_count"] = rent_data["comp_count"]
        
        # Derived: price-to-rent ratio and 1% rule
        if listing.get("price") and rent_data["rent"]:
            listing["price_to_rent_ratio"] = round(listing["price"] / (rent_data["rent"] * 12), 2)
            listing["meets_1pct_rule"] = rent_data["rent"] >= (listing["price"] * 0.01)
            listing["gross_yield_pct"] = round((rent_data["rent"] * 12) / listing["price"] * 100, 2)
    
    # Get value estimate (uses 1 API call — budget carefully)
    value_data = get_value_estimate(
        address=address,
        beds=listing.get("beds"),
        baths=listing.get("baths"),
        sqft=listing.get("sqft"),
        property_type=listing.get("property_type", "Single Family"),
    )
    
    if value_data:
        listing["estimated_value"] = value_data["value"]
        listing["value_low"] = value_data["value_low"]
        listing["value_high"] = value_data["value_high"]
        
        # Derived: discount to estimated value
        if listing.get("price") and value_data["value"]:
            listing["discount_to_value_pct"] = round(
                (1 - listing["price"] / value_data["value"]) * 100, 2
            )
    
    return listing
