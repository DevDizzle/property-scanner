from google.cloud import bigquery
import json
client = bigquery.Client()
queries = {
    'raw_listings': '''
        SELECT 
            COUNT(*) as total_rows,
            COUNTIF(price IS NOT NULL) as non_null_prices,
            AVG(price) as avg_price,
            MIN(price) as min_price,
            MAX(price) as max_price
        FROM `profitscout-fida8.property_scanner.raw_listings`
    ''',
    'enriched_listings': '''
        SELECT 
            COUNT(*) as total_rows,
            COUNTIF(rent_estimate IS NOT NULL) as non_null_rents,
            AVG(rent_estimate) as avg_rent,
            AVG(tax_reset_annual) as avg_tax_reset
        FROM `profitscout-fida8.property_scanner.enriched_listings`
    '''
}
for name, query in queries.items():
    print(f'\n--- {name} ---')
    job = client.query(query)
    for row in job:
        print(dict(row))