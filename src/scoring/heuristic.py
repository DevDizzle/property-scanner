"""Weighted heuristic scoring model for property investment attractiveness.

Score = w1(Yield) + w2(Discount) + w3(Urgency) + w4(Risk)
Each component scores 0-10, final score is 0-10 + bonuses.
"""
import logging
import statistics
from typing import Optional

from src.config import get_config

logger = logging.getLogger(__name__)


def score_yield(listing: dict) -> float:
    """Score based on rental yield potential. 0-10.
    
    Key metric: gross yield % (annual rent / price)
    - 12%+ = 10 (exceptional)
    - 10-12% = 8
    - 8-10% = 6 (solid)
    - 6-8% = 4 (marginal)
    - <6% = 2 (poor for investment)
    
    Bonus: meets 1% rule = +1
    """
    gross_yield = listing.get("gross_yield_pct", 0) or 0
    
    if gross_yield >= 12:
        score = 10
    elif gross_yield >= 10:
        score = 8
    elif gross_yield >= 8:
        score = 6
    elif gross_yield >= 6:
        score = 4
    elif gross_yield >= 4:
        score = 2
    else:
        score = 0
    
    # 1% rule bonus
    if listing.get("meets_1pct_rule"):
        score = min(10, score + 1)
    
    return score


def score_discount(listing: dict, zip_median_ppsf: Optional[float] = None) -> float:
    """Score based on discount to value. 0-10.
    
    Two signals:
    1. Discount to RentCast AVM (if available)
    2. Spread vs zip median price/sqft
    """
    scores = []
    
    # Signal 1: Discount to estimated value
    discount_pct = listing.get("discount_to_value_pct", 0) or 0
    if discount_pct >= 20:
        scores.append(10)
    elif discount_pct >= 15:
        scores.append(8)
    elif discount_pct >= 10:
        scores.append(6)
    elif discount_pct >= 5:
        scores.append(4)
    elif discount_pct > 0:
        scores.append(2)
    else:
        scores.append(0)
    
    # Signal 2: Below zip median price/sqft
    if zip_median_ppsf and listing.get("price_per_sqft"):
        spread = (zip_median_ppsf - listing["price_per_sqft"]) / zip_median_ppsf * 100
        if spread >= 20:
            scores.append(10)
        elif spread >= 10:
            scores.append(7)
        elif spread >= 5:
            scores.append(4)
        else:
            scores.append(1)
    
    return statistics.mean(scores) if scores else 0


def score_urgency(listing: dict, zip_median_dom: Optional[float] = None) -> float:
    """Score based on urgency signals. 0-10.
    
    Signals: DOM percentile, price drops, status
    Higher urgency = more motivated seller = better deal potential
    """
    score = 0
    dom = listing.get("dom", 0) or 0
    
    # DOM scoring — higher DOM = more motivation
    if dom >= 120:
        score += 5  # 4+ months, very motivated
    elif dom >= 90:
        score += 4
    elif dom >= 60:
        score += 3
    elif dom >= 30:
        score += 2
    else:
        score += 1  # Fresh listing, less negotiation room
    
    # DOM vs zip median (if available)
    if zip_median_dom and dom > zip_median_dom * 1.5:
        score += 2  # Significantly above median = extra motivation
    
    # Price drop velocity (if we track it)
    price_drops = listing.get("price_drop_count", 0) or 0
    if price_drops >= 3:
        score += 3
    elif price_drops >= 2:
        score += 2
    elif price_drops >= 1:
        score += 1
    
    return min(10, score)


def score_risk(listing: dict, tax_data: Optional[dict] = None) -> float:
    """Score based on risk factors. 0-10. INVERTED: lower risk = higher score.
    
    Risk factors:
    - Post-sale tax shock (the big one)
    - Flood zone (future feature)
    - Insurance estimate
    - Cash flow after real expenses
    """
    score = 10  # Start at 10, deduct for risks
    
    # Tax reset shock
    if tax_data:
        increase_pct = tax_data.get("tax_increase_pct", 0) or 0
        if increase_pct > 100:
            score -= 4  # Tax more than doubles — major risk
        elif increase_pct > 50:
            score -= 2
        elif increase_pct > 25:
            score -= 1
    
    # Net cash flow check
    net_monthly = listing.get("net_monthly")
    if net_monthly is not None:
        if net_monthly < 0:
            score -= 3  # Negative cash flow
        elif net_monthly < 200:
            score -= 1  # Thin margin
    
    # Year built risk (older = more maintenance)
    year_built = listing.get("year_built")
    if year_built:
        if year_built < 1970:
            score -= 2
        elif year_built < 1990:
            score -= 1
    
    return max(0, score)


def calculate_score(
    listing: dict,
    tax_data: Optional[dict] = None,
    zip_median_ppsf: Optional[float] = None,
    zip_median_dom: Optional[float] = None,
) -> dict:
    """Calculate the full investment attractiveness score.
    
    Returns the listing dict with score fields added.
    """
    config = get_config()
    weights = config["scoring"]["weights"]
    bonuses = config["scoring"]["bonuses"]
    
    # Component scores
    yield_score = score_yield(listing)
    discount_score = score_discount(listing, zip_median_ppsf)
    urgency_score = score_urgency(listing, zip_median_dom)
    risk_score = score_risk(listing, tax_data)
    
    # Weighted composite
    composite = (
        weights["yield"] * yield_score +
        weights["discount"] * discount_score +
        weights["urgency"] * urgency_score +
        weights["risk"] * risk_score
    )
    
    # Bonuses
    bonus = 0
    
    # Below median price for zip
    if zip_median_ppsf and listing.get("price_per_sqft"):
        if listing["price_per_sqft"] < zip_median_ppsf:
            bonus += bonuses["below_median"]
    
    # Distress codes (Broward)
    if listing.get("distress_code"):
        bonus += bonuses["distress_code"]
    
    final_score = round(min(10, composite + bonus), 1)
    
    # Add scores to listing
    listing["score"] = final_score
    listing["score_yield"] = round(yield_score, 1)
    listing["score_discount"] = round(discount_score, 1)
    listing["score_urgency"] = round(urgency_score, 1)
    listing["score_risk"] = round(risk_score, 1)
    listing["score_bonus"] = round(bonus, 1)
    
    return listing


def preliminary_filter(listings: list[dict], top_pct: float = 0.20) -> list[dict]:
    """Quick filter before expensive enrichment.
    
    Uses only FREE data (from scraping) to identify top candidates.
    Saves 80% of API costs.
    """
    if not listings:
        return []
    
    # Calculate zip-level stats
    prices_per_sqft = [
        l["price_per_sqft"] for l in listings
        if l.get("price_per_sqft") and l["price_per_sqft"] > 0
    ]
    doms = [l["dom"] for l in listings if l.get("dom") is not None]
    
    median_ppsf = statistics.median(prices_per_sqft) if prices_per_sqft else None
    median_dom = statistics.median(doms) if doms else None
    
    # Score each listing with available data only
    for listing in listings:
        prelim_score = 0
        
        # Below median price/sqft
        if median_ppsf and listing.get("price_per_sqft"):
            if listing["price_per_sqft"] < median_ppsf:
                spread = (median_ppsf - listing["price_per_sqft"]) / median_ppsf
                prelim_score += spread * 10
        
        # High DOM (motivated seller)
        if listing.get("dom") and listing["dom"] > 30:
            prelim_score += min(5, listing["dom"] / 30)
        
        # Above median DOM
        if median_dom and listing.get("dom") and listing["dom"] > median_dom:
            prelim_score += 2
        
        listing["prelim_score"] = round(prelim_score, 2)
    
    # Sort and take top %
    listings.sort(key=lambda x: x.get("prelim_score", 0), reverse=True)
    cutoff = max(1, int(len(listings) * top_pct))
    
    passed = listings[:cutoff]
    logger.info(
        f"Preliminary filter: {len(passed)}/{len(listings)} passed "
        f"(top {top_pct*100:.0f}%, median ppsf=${median_ppsf:.0f}, median DOM={median_dom:.0f})"
    )
    
    return passed
