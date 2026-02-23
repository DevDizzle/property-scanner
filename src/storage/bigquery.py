"""BigQuery integration for Property Scanner MVP."""
import json
import logging
from typing import Any

from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from src.config import get_config

logger = logging.getLogger(__name__)

PROJECT_ID = "profitscout-fida8"
DATASET_ID = "property_scanner"
LOCATION = "us-central1"

def get_bq_client() -> bigquery.Client:
    """Get authenticated BQ client using default credentials."""
    return bigquery.Client(project=PROJECT_ID, location=LOCATION)


def _ensure_dataset(client: bigquery.Client):
    """Ensure the dataset exists."""
    dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"
    try:
        client.get_dataset(dataset_ref)
    except NotFound:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = LOCATION
        client.create_dataset(dataset, timeout=30)
        logger.info(f"Created dataset {dataset_ref}")


def init_tables():
    """Create BigQuery table schemas if they don't exist."""
    client = get_bq_client()
    _ensure_dataset(client)
    
    # Define schemas (using JSON to handle nested/dynamic fields easily for MVP)
    tables = {
        "raw_listings": [
            bigquery.SchemaField("listing_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("scraped_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("zip_code", "STRING"),
            bigquery.SchemaField("price", "FLOAT"),
            bigquery.SchemaField("raw_data", "JSON"),
        ],
        "enriched_listings": [
            bigquery.SchemaField("listing_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("scraped_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("zip_code", "STRING"),
            bigquery.SchemaField("price", "FLOAT"),
            bigquery.SchemaField("rent_estimate", "FLOAT"),
            bigquery.SchemaField("tax_reset_annual", "FLOAT"),
            bigquery.SchemaField("enriched_data", "JSON"),
        ],
        "scored_listings": [
            bigquery.SchemaField("listing_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("scraped_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("zip_code", "STRING"),
            bigquery.SchemaField("score", "FLOAT"),
            bigquery.SchemaField("net_monthly", "FLOAT"),
            bigquery.SchemaField("cash_on_cash_pct", "FLOAT"),
            bigquery.SchemaField("scored_data", "JSON"),
        ],
        "daily_reports": [
            bigquery.SchemaField("report_date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("zip_codes_scanned", "STRING", mode="REPEATED"),
            bigquery.SchemaField("total_scanned", "INTEGER"),
            bigquery.SchemaField("total_passed_filter", "INTEGER"),
            bigquery.SchemaField("avg_score", "FLOAT"),
            bigquery.SchemaField("report_metadata", "JSON"),
        ]
    }
    
    for table_name, schema in tables.items():
        table_ref = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
        try:
            client.get_table(table_ref)
        except NotFound:
            table = bigquery.Table(table_ref, schema=schema)
            # Time partitioning on scraped_at/report_date for efficiency
            if table_name == "daily_reports":
                table.time_partitioning = bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.DAY,
                    field="report_date",
                )
            else:
                table.time_partitioning = bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.DAY,
                    field="scraped_at",
                )
            client.create_table(table, timeout=30)
            logger.info(f"Created table {table_ref}")


def _clean_dict(d: dict) -> dict:
    """Ensure all dict values are JSON serializable for BQ."""
    # Convert sets/datetimes or custom objects if any. 
    # For MVP, mostly standard types, but standard python json.dumps is safe.
    try:
        return json.loads(json.dumps(d, default=str))
    except Exception as e:
        logger.warning(f"JSON serialization issue in _clean_dict: {e}")
        return {}


def write_raw_listings(listings: list[dict]):
    """Write raw scrape results to BQ."""
    if not listings:
        return
        
    client = get_bq_client()
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.raw_listings"
    
    rows = []
    for l in listings:
        clean_l = _clean_dict(l)
        rows.append({
            "listing_id": clean_l.get("listing_id", "UNKNOWN"),
            "scraped_at": clean_l.get("scraped_at"),
            "zip_code": clean_l.get("zip_code"),
            "price": clean_l.get("price"),
            "raw_data": json.dumps(clean_l),
        })
    
    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        logger.error(f"BQ insert errors for raw_listings: {errors}")
    else:
        logger.info(f"Wrote {len(rows)} rows to {table_ref}")


def write_enriched_listings(listings: list[dict]):
    """Write enriched results to BQ."""
    if not listings:
        return
        
    client = get_bq_client()
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.enriched_listings"
    
    rows = []
    for l in listings:
        clean_l = _clean_dict(l)
        tax_data = clean_l.get("tax_reset", {})
        rows.append({
            "listing_id": clean_l.get("listing_id", "UNKNOWN"),
            "scraped_at": clean_l.get("scraped_at"),
            "zip_code": clean_l.get("zip_code"),
            "price": clean_l.get("price"),
            "rent_estimate": clean_l.get("rent_estimate"),
            "tax_reset_annual": tax_data.get("post_sale_tax_annual") if isinstance(tax_data, dict) else None,
            "enriched_data": json.dumps(clean_l),
        })
    
    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        logger.error(f"BQ insert errors for enriched_listings: {errors}")
    else:
        logger.info(f"Wrote {len(rows)} rows to {table_ref}")


def write_scored_listings(listings: list[dict]):
    """Write final scored results to BQ."""
    if not listings:
        return
        
    client = get_bq_client()
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.scored_listings"
    
    rows = []
    for l in listings:
        clean_l = _clean_dict(l)
        rows.append({
            "listing_id": clean_l.get("listing_id", "UNKNOWN"),
            "scraped_at": clean_l.get("scraped_at"),
            "zip_code": clean_l.get("zip_code"),
            "score": clean_l.get("score"),
            "net_monthly": clean_l.get("net_monthly"),
            "cash_on_cash_pct": clean_l.get("cash_on_cash_pct"),
            "scored_data": json.dumps(clean_l),
        })
    
    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        logger.error(f"BQ insert errors for scored_listings: {errors}")
    else:
        logger.info(f"Wrote {len(rows)} rows to {table_ref}")


def write_daily_report(report_metadata: dict):
    """Write daily run summary to BQ."""
    client = get_bq_client()
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.daily_reports"
    
    clean_meta = _clean_dict(report_metadata)
    row = {
        "report_date": clean_meta.get("report_date"),
        "zip_codes_scanned": clean_meta.get("zip_codes", []),
        "total_scanned": clean_meta.get("total_scanned", 0),
        "total_passed_filter": clean_meta.get("total_passed_filter", 0),
        "avg_score": clean_meta.get("avg_score"),
        "report_metadata": json.dumps(clean_meta),
    }
    
    errors = client.insert_rows_json(table_ref, [row])
    if errors:
        logger.error(f"BQ insert errors for daily_reports: {errors}")
    else:
        logger.info(f"Wrote 1 row to {table_ref}")
