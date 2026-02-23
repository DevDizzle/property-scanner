"""Demo data generator for Property Scanner MVP."""
import random
from datetime import datetime, timedelta

def generate_demo_listings(zip_code: str, count: int = 50) -> list[dict]:
    """Generate mock real estate listings for testing the pipeline."""
    listings = []
    
    street_names = [
        "Las Olas Blvd", "Sunrise Blvd", "Broward Blvd", "Federal Hwy",
        "A1A", "Andrews Ave", "SE 1st Ave", "SW 2nd St", "NW 3rd Ave",
        "NE 4th St", "Himmarshee St", "Tarpon Dr", "Isle of Venice Dr"
    ]
    
    for i in range(count):
        # Generate realistic data
        price = random.randint(200, 800) * 1000
        sqft = random.randint(1000, 3000)
        beds = random.randint(2, 5)
        baths = random.randint(1, 3) + (0.5 if random.choice([True, False]) else 0)
        year_built = random.randint(1960, 2020)
        dom = random.randint(5, 180)
        
        street = random.choice(street_names)
        address = f"{random.randint(100, 9999)} {street}"
        
        # Mix of good and bad deals
        is_good_deal = random.random() < 0.2  # 20% chance of being an obvious good deal
        if is_good_deal:
            price = int(price * 0.8)  # 20% discount
            dom = random.randint(90, 180)  # high DOM, motivated seller
            price_drop_count = random.randint(1, 3)
        else:
            price_drop_count = 0
            
        price_per_sqft = round(price / sqft, 2)
            
        listing = {
            "source": "demo",
            "address": address,
            "city": "Fort Lauderdale" if zip_code == "33301" else "Anytown",
            "state": "FL",
            "zip_code": zip_code,
            "price": price,
            "beds": beds,
            "baths": baths,
            "sqft": sqft,
            "lot_sqft": sqft * random.uniform(1.2, 3.0),
            "year_built": year_built,
            "dom": dom,
            "property_type": random.choice(["Single Family", "Multi-Family", "Townhouse"]),
            "url": f"https://www.redfin.com/demo/property_{i}",
            "latitude": 26.1224 + random.uniform(-0.05, 0.05),
            "longitude": -80.1373 + random.uniform(-0.05, 0.05),
            "status": "active",
            "listing_id": f"DEMO{random.randint(1000000, 9999999)}",
            "price_per_sqft": price_per_sqft,
            "price_drop_count": price_drop_count,
            "scraped_at": datetime.utcnow().isoformat(),
        }
        
        # Mock rentcast data if this is a "good deal" to ensure some pass the filter and score well
        # We actually don't add rentcast data here, as the pipeline will add it in enrichment step.
        # Wait, if we use demo mode, we might want to mock enrichment too to avoid API costs?
        # The prompt says: "add a mock/demo mode — Since we may not have API keys yet... so we can test the full pipeline without ScrapingBee."
        # It doesn't explicitly say to mock RentCast, but "so we can test the full pipeline without API keys" implies we should mock it too, or provide demo RentCast data.
        # Actually, let's look at `src/main.py`. The enrichment step calls `enrich_listing`.
        # I'll just mock RentCast inside demo data or let the user provide RentCast API key?
        # Let's read the prompt again: "Test the full pipeline end-to-end with demo data: python -m src.main --zip 33301 --demo"
        # Since I am asked to make sure it runs, and RentCast might fail if no key, I should probably patch `enrich_listing` or provide mock rent data in demo mode.
        
        listings.append(listing)
        
    return listings

def mock_enrich_listing(listing: dict) -> dict:
    """Mock RentCast enrichment for demo mode."""
    price = listing.get("price", 400000)
    
    # Generate realistic rent (roughly 0.8% to 1.2% of price per month)
    rent_pct = random.uniform(0.008, 0.012)
    rent = int(price * rent_pct)
    
    # Generate value estimate
    value_discount_pct = random.uniform(-0.05, 0.15)
    estimated_value = int(price / (1 - value_discount_pct))
    
    listing["rent_estimate"] = rent
    listing["rent_low"] = int(rent * 0.9)
    listing["rent_high"] = int(rent * 1.1)
    listing["rent_comp_count"] = random.randint(3, 10)
    
    if listing.get("price") and rent:
        listing["price_to_rent_ratio"] = round(price / (rent * 12), 2)
        listing["meets_1pct_rule"] = rent >= (price * 0.01)
        listing["gross_yield_pct"] = round((rent * 12) / price * 100, 2)
        
    listing["estimated_value"] = estimated_value
    listing["value_low"] = int(estimated_value * 0.9)
    listing["value_high"] = int(estimated_value * 1.1)
    
    if listing.get("price") and estimated_value:
        listing["discount_to_value_pct"] = round((1 - price / estimated_value) * 100, 2)
        
    return listing
