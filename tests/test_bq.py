import json
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

try:
    creds = service_account.Credentials.from_service_account_file('sa_key_fixed.json')
    client = bigquery.Client(project="profitscout-fida8", credentials=creds)
except Exception as e:
    print("No creds:", e)
    client = bigquery.Client(project="profitscout-fida8")

query = """
    SELECT scored_data
    FROM `profitscout-fida8.property_scanner.scored_listings`
    WHERE DATE(scraped_at) = (
        SELECT MAX(DATE(scraped_at)) 
        FROM `profitscout-fida8.property_scanner.scored_listings`
    )
"""
query_job = client.query(query)
rows = query_job.result()
data = []
for row in rows:
    if isinstance(row.scored_data, str):
        data.append(json.loads(row.scored_data))
    else:
        data.append(row.scored_data)

df = pd.DataFrame(data)
print(f"Loaded {len(df)} rows.")
if not df.empty:
    print(df.columns.tolist()[:10])
