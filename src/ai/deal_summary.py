"""Gemini-powered deal summaries for top-scored properties."""
import logging
from typing import Optional

import google.generativeai as genai

from src.config import get_config

logger = logging.getLogger(__name__)


def _get_model():
    config = get_config()
    model_name = config["apis"]["gemini"]["model"]
    return genai.GenerativeModel(model_name)


def generate_deal_summary(listing: dict, tax_data: Optional[dict] = None) -> str:
    """Generate an investment thesis for a scored property.
    
    Returns a concise, actionable summary that a REIA member
    can use to make a go/no-go decision in under 60 seconds.
    """
    model = _get_model()
    
    # Build context
    rent = listing.get("rent_estimate", "N/A")
    rent_low = listing.get("rent_low", "N/A")
    rent_high = listing.get("rent_high", "N/A")
    gross_yield = listing.get("gross_yield_pct", "N/A")
    meets_1pct = "YES" if listing.get("meets_1pct_rule") else "NO"
    discount = listing.get("discount_to_value_pct", "N/A")
    net_monthly = listing.get("net_monthly", "N/A")
    cash_on_cash = listing.get("cash_on_cash_pct", "N/A")
    
    tax_section = ""
    if tax_data:
        current_tax = tax_data.get("current_tax_annual", "Unknown")
        post_tax = tax_data.get("post_sale_tax_annual", "N/A")
        increase = tax_data.get("tax_increase_pct", "N/A")
        tax_section = f"""
POST-SALE TAX RESET:
- Current annual tax: ${current_tax}
- Post-sale annual tax: ${post_tax}
- Tax increase: {increase}%
- Monthly tax impact: ${tax_data.get('post_sale_tax_monthly', 'N/A')}
"""
    
    prompt = f"""You are an investment analyst for a Real Estate Investors Association.
Write a concise deal summary (150 words max) for this property.

PROPERTY:
- Address: {listing.get('address')}, {listing.get('city')}, FL {listing.get('zip_code')}
- Price: ${listing.get('price', 'N/A'):,.0f}
- Beds/Baths: {listing.get('beds', 'N/A')}/{listing.get('baths', 'N/A')}
- SqFt: {listing.get('sqft', 'N/A')}
- Year Built: {listing.get('year_built', 'N/A')}
- Days on Market: {listing.get('dom', 'N/A')}
- Price/SqFt: ${listing.get('price_per_sqft', 'N/A')}

RENTAL ANALYSIS:
- Estimated Rent: ${rent}/mo (range: ${rent_low}-${rent_high})
- Gross Yield: {gross_yield}%
- 1% Rule: {meets_1pct}
- Discount to Value: {discount}%
{tax_section}
CASH FLOW:
- Net Monthly: ${net_monthly}
- Cash-on-Cash Return: {cash_on_cash}%

SCORE: {listing.get('score', 'N/A')}/10
- Yield: {listing.get('score_yield', 'N/A')}/10
- Discount: {listing.get('score_discount', 'N/A')}/10
- Urgency: {listing.get('score_urgency', 'N/A')}/10
- Risk: {listing.get('score_risk', 'N/A')}/10

Write the summary in this format:
1. ONE SENTENCE verdict (Buy/Watch/Pass + why)
2. THE NUMBERS: Key metrics that matter
3. TAX REALITY: Post-sale tax impact on actual ROI (this is critical — most investors miss this)
4. RISK: What could go wrong
5. ACTION: What a buyer should do next

Be direct. No fluff. Write like you're briefing an experienced investor who's seen 100 deals this week."""

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini deal summary failed: {e}")
        return f"[AI summary unavailable: {e}]"
