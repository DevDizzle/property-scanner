import pandas as pd
from google.cloud import bigquery
import json

client = bigquery.Client()

def analyze_table(table_name):
    query = f"SELECT * FROM `profitscout-fida8.property_scanner.{table_name}`"
    df = client.query(query).to_dataframe()
    print(f"\n=========================================")
    print(f"   TABLE: {table_name} ({len(df)} rows)")
    print(f"=========================================")
    
    if len(df) == 0:
        print("Table is empty.")
        return
        
    print("\n--- Summary Statistics ---")
    num_cols = df.select_dtypes(include=['float64', 'int64']).columns
    if not num_cols.empty:
        print(df[num_cols].describe().round(2).to_string())
    
    # Analyze the JSON blob for completeness
    data_col = [c for c in df.columns if c.endswith('_data')]
    if data_col:
        blob_col = data_col[0]
        parsed = df[blob_col].apply(lambda x: json.loads(x) if isinstance(x, str) else x)
        parsed_df = pd.json_normalize(parsed)
        print(f"\n--- JSON Payload Completeness ({blob_col}) ---")
        missing_pct = (parsed_df.isnull().sum() / len(parsed_df) * 100).round(1)
        print("Fields missing data (%):")
        print(missing_pct[missing_pct > 0].sort_values(ascending=False).to_string())
        
        if 'city' in parsed_df.columns and 'state' in parsed_df.columns:
            print("\n--- Locations ---")
            print(parsed_df[['city', 'state', 'zip_code']].value_counts().to_string())

analyze_table('raw_listings')
analyze_table('enriched_listings')
analyze_table('scored_listings')