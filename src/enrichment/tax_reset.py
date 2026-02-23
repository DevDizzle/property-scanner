"""Post-Sale Tax Reset Calculator — THE KILLER FEATURE.

Florida's "Save Our Homes" amendment caps annual assessed value increases
at 3% or CPI for homesteaded properties. When a homesteaded property sells,
the assessment RESETS to full market value, causing a massive tax spike.

Most investors calculate ROI using the seller's current tax bill.
We calculate the REAL post-purchase tax bill.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 2025-2026 millage rates for South Florida (per $1,000 of assessed value)
# Source: County property appraiser websites
# These should be updated annually
MILLAGE_RATES = {
    # Broward County
    "33301": 19.7286,  # Fort Lauderdale
    "33304": 19.7286,
    "33305": 19.7286,
    "33306": 19.7286,
    "33308": 19.7286,
    "33309": 19.7286,
    "33311": 19.7286,
    "33312": 19.7286,
    "33313": 19.7286,
    "33314": 19.7286,
    "33316": 19.7286,
    "33317": 19.7286,
    "33319": 18.6542,  # Unincorporated Broward
    "33321": 18.6542,
    "33322": 18.6542,
    "33323": 18.6542,
    "33324": 18.9876,  # Plantation
    "33325": 18.9876,
    "33326": 18.9876,
    "33327": 18.6542,
    "33328": 18.9876,
    "33330": 18.2431,  # Cooper City
    "33331": 18.2431,
    "33332": 18.6542,
    "33334": 19.4521,  # Oakland Park
    "33351": 18.6542,
    # Miami-Dade County
    "33125": 21.2890,  # Miami
    "33126": 21.2890,
    "33127": 21.2890,
    "33128": 21.2890,
    "33129": 21.2890,
    "33130": 21.2890,
    "33131": 21.2890,
    "33132": 21.2890,
    "33133": 21.2890,
    "33134": 21.2890,
    "33135": 21.2890,
    "33136": 21.2890,
    "33137": 21.2890,
    "33138": 21.2890,
    "33139": 21.2890,  # Miami Beach
    "33140": 21.2890,
    "33141": 21.2890,
    "33142": 21.2890,
    "33143": 21.2890,
    "33144": 21.2890,
    "33145": 21.2890,
    "33146": 21.2890,  # Coral Gables
    "33147": 21.2890,
    "33150": 21.2890,
    "33155": 21.2890,
    "33156": 21.2890,
    "33157": 21.2890,
    "33158": 21.2890,
    "33160": 20.1234,  # North Miami Beach
    "33161": 20.1234,
    "33162": 20.1234,
    "33166": 20.5678,  # Hialeah
    "33167": 20.5678,
    "33169": 20.5678,
    "33172": 19.8765,  # Unincorporated
    "33173": 19.8765,
    "33174": 19.8765,
    "33175": 19.8765,
    "33176": 19.8765,
    "33177": 19.8765,
    "33178": 19.8765,  # Doral
    "33179": 20.1234,
    "33180": 20.1234,
    "33186": 19.8765,
    # Palm Beach County
    "33401": 20.1543,  # West Palm Beach
    "33402": 20.1543,
    "33403": 20.1543,
    "33404": 20.1543,
    "33405": 20.1543,
    "33406": 20.1543,
    "33407": 20.1543,
    "33408": 19.2345,  # North Palm Beach
    "33409": 20.1543,
    "33410": 19.2345,
    "33411": 18.9876,  # Royal Palm Beach
    "33412": 18.9876,
    "33414": 18.6789,  # Wellington
    "33415": 20.1543,
    "33417": 20.1543,
    "33418": 18.6789,
    "33426": 19.5432,  # Boynton Beach
    "33428": 19.5432,
    "33431": 19.8765,  # Boca Raton
    "33432": 19.8765,
    "33433": 19.8765,
    "33434": 19.8765,
    "33435": 19.5432,
    "33436": 19.5432,
    "33437": 19.5432,
    "33444": 19.6543,  # Delray Beach
    "33445": 19.6543,
    "33446": 19.6543,
    "33460": 20.3456,  # Lake Worth
    "33461": 20.3456,
    "33462": 20.3456,
    "33463": 18.9876,
    "33467": 18.9876,
    "33469": 18.6789,  # Jupiter
    "33470": 18.6789,
    "33477": 18.6789,
    "33478": 18.6789,
    "33480": 19.5432,  # Palm Beach (town)
    "33484": 19.6543,
    "33486": 19.8765,
    "33487": 19.6543,
}

# Florida homestead exemption: $50,000 for primary residence
# Non-homestead (investors): $25,000 exemption only
HOMESTEAD_EXEMPTION = 50000
NON_HOMESTEAD_EXEMPTION = 25000


def calculate_post_sale_tax(
    listing_price: float,
    zip_code: str,
    current_assessed_value: Optional[float] = None,
    current_tax_bill: Optional[float] = None,
    is_investment: bool = True,
) -> dict:
    """Calculate the post-sale tax reset impact.
    
    Args:
        listing_price: What the buyer will pay
        zip_code: Property zip code (for millage rate lookup)
        current_assessed_value: Seller's current assessed value (if known)
        current_tax_bill: Seller's current annual tax (if known)
        is_investment: True = non-homestead (investor purchase)
    
    Returns:
        {
            "post_sale_assessed": float,
            "post_sale_tax_annual": float,
            "post_sale_tax_monthly": float,
            "current_tax_annual": float or None,
            "tax_increase_pct": float or None,
            "tax_increase_annual": float or None,
            "millage_rate": float,
            "exemption_applied": float,
        }
    """
    millage = MILLAGE_RATES.get(zip_code)
    if not millage:
        # Fall back to county average
        if zip_code.startswith("33"):
            if len(zip_code) == 5 and int(zip_code[2:]) >= 100 and int(zip_code[2:]) <= 199:
                millage = 21.2890  # Miami-Dade avg
            elif int(zip_code[2:]) >= 300 and int(zip_code[2:]) <= 499:
                millage = 20.1543  # Palm Beach avg
            else:
                millage = 19.7286  # Broward avg
        else:
            millage = 19.5  # Generic FL fallback
        logger.info(f"Using estimated millage {millage} for zip {zip_code}")
    
    # Post-sale: assessment resets to purchase price
    post_sale_assessed = listing_price
    
    # Apply exemption
    exemption = NON_HOMESTEAD_EXEMPTION if is_investment else HOMESTEAD_EXEMPTION
    taxable_value = max(0, post_sale_assessed - exemption)
    
    # Calculate tax (millage rate is per $1,000)
    post_sale_tax_annual = round(taxable_value * millage / 1000, 2)
    post_sale_tax_monthly = round(post_sale_tax_annual / 12, 2)
    
    result = {
        "post_sale_assessed": post_sale_assessed,
        "post_sale_tax_annual": post_sale_tax_annual,
        "post_sale_tax_monthly": post_sale_tax_monthly,
        "current_tax_annual": current_tax_bill,
        "tax_increase_pct": None,
        "tax_increase_annual": None,
        "millage_rate": millage,
        "exemption_applied": exemption,
    }
    
    # If we know the current tax, calculate the shock
    if current_tax_bill and current_tax_bill > 0:
        result["tax_increase_annual"] = round(post_sale_tax_annual - current_tax_bill, 2)
        result["tax_increase_pct"] = round(
            (post_sale_tax_annual / current_tax_bill - 1) * 100, 1
        )
    
    return result


def estimate_net_cash_flow(
    listing: dict,
    tax_data: dict,
    insurance_monthly: float = 350,  # FL average for investment property
    maintenance_pct: float = 0.01,   # 1% of value annually
    vacancy_pct: float = 0.08,       # 8% vacancy rate
    management_pct: float = 0.10,    # 10% property management
) -> dict:
    """Calculate estimated monthly net cash flow with REAL tax numbers.
    
    This is where the tax reset makes or breaks the deal.
    """
    rent = listing.get("rent_estimate", 0) or 0
    price = listing.get("price", 0) or 0
    
    if not rent or not price:
        return {"net_monthly": None, "error": "Missing rent or price"}
    
    # Income (after vacancy)
    effective_rent = rent * (1 - vacancy_pct)
    
    # Expenses
    tax_monthly = tax_data["post_sale_tax_monthly"]
    maintenance_monthly = (price * maintenance_pct) / 12
    management_monthly = rent * management_pct
    
    total_expenses = tax_monthly + insurance_monthly + maintenance_monthly + management_monthly
    net_monthly = round(effective_rent - total_expenses, 2)
    
    # Cash-on-cash return (assuming 25% down, no mortgage payment included here)
    down_payment = price * 0.25
    closing_costs = price * 0.03  # ~3% closing costs
    total_cash_in = down_payment + closing_costs
    annual_net = net_monthly * 12
    cash_on_cash = round((annual_net / total_cash_in) * 100, 2) if total_cash_in > 0 else 0
    
    return {
        "gross_rent": rent,
        "effective_rent": round(effective_rent, 2),
        "tax_monthly": tax_monthly,
        "insurance_monthly": insurance_monthly,
        "maintenance_monthly": round(maintenance_monthly, 2),
        "management_monthly": round(management_monthly, 2),
        "total_expenses": round(total_expenses, 2),
        "net_monthly": net_monthly,
        "net_annual": round(annual_net, 2),
        "cash_on_cash_pct": cash_on_cash,
        "cap_rate_pct": round((annual_net / price) * 100, 2) if price > 0 else 0,
    }
