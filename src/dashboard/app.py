import json
import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = Path(__file__).parent.parent.parent / "data"

st.set_page_config(
    page_title="BPM REIA — AI Deal Sourcing Feed",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for dark institutional theme and clean layout
st.markdown(
    """
    <style>
        .reportview-container {
            background: #0e1117;
            color: #fafafa;
        }
        .metric-card {
            background-color: #1e1e2e;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #333;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
        }
        .metric-label {
            font-size: 14px;
            color: #aaa;
        }
        .tax-shock {
            background-color: #3b1c1c;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #ff4b4b;
            text-align: center;
            margin-bottom: 15px;
        }
        .tax-shock h3 {
            color: #ff4b4b;
            margin-top: 0;
            margin-bottom: 5px;
        }
        .tax-shock .big-numbers {
            font-size: 22px;
            font-weight: bold;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=600)
def load_latest_data() -> pd.DataFrame:
    """Load the most recent scored listings from BigQuery or local fallback."""
    # Attempt BigQuery first (for Streamlit Community Cloud)
    try:
        from google.cloud import bigquery
        from google.oauth2 import service_account
        
        # Check if we have Streamlit secrets configured
        if "gcp_service_account" in st.secrets:
            # Use credentials from Streamlit secrets
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"]
            )
            client = bigquery.Client(project="profitscout-fida8", credentials=creds)
        else:
            # Fallback to local default credentials
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
        data = [json.loads(row.scored_data) for row in rows]
        
        if data:
            logger.info("Successfully loaded latest scan data from BigQuery.")
            return pd.DataFrame(data)
    except Exception as e:
        logger.warning(f"BigQuery load failed (falling back to local files): {e}")

    # Fallback to local data directory
    if not DATA_DIR.exists():
        return pd.DataFrame()

    files = list(DATA_DIR.glob("final_results_*.json"))
    if not files:
        return pd.DataFrame()

    # Get most recent
    latest_file = max(files, key=os.path.getctime)
    try:
        with open(latest_file, "r") as f:
            data = json.load(f)
        logger.info(f"Loaded data from local file {latest_file}.")
        return pd.DataFrame(data)
    except Exception as e:
        logger.error(f"Failed to load data from {latest_file}: {e}")
        return pd.DataFrame()


def render_dashboard():
    st.title("🏛️ BPM REIA — AI Deal Sourcing Feed")
    st.markdown(f"**Latest Scan:** {datetime.now().strftime('%A, %B %d, %Y')}")

    # Load Data
    df = load_latest_data()

    if df.empty:
        st.warning("No data available. Run the pipeline first.")
        return

    # --- Sidebar Filters ---
    st.sidebar.header("Filter Deals")

    # Price Range
    min_price = int(df["price"].min()) if not df["price"].empty else 100000
    max_price = int(df["price"].max()) if not df["price"].empty else 1000000
    price_range = st.sidebar.slider(
        "Price Range ($)",
        min_value=min_price,
        max_value=max_price,
        value=(min_price, max_price),
        step=10000,
    )

    # Zip Codes
    zip_codes = sorted(df["zip_code"].dropna().unique().tolist())
    selected_zips = st.sidebar.multiselect("Zip Codes", zip_codes, default=zip_codes)

    # Minimum Score
    min_score = st.sidebar.slider(
        "Minimum Score",
        min_value=0.0,
        max_value=10.0,
        value=5.0,
        step=0.5,
    )

    # Beds
    bed_options = sorted(df["beds"].dropna().unique().tolist())
    selected_beds = st.sidebar.multiselect("Beds", bed_options, default=bed_options)

    # --- Apply Filters ---
    filtered_df = df[
        (df["price"] >= price_range[0])
        & (df["price"] <= price_range[1])
        & (df["zip_code"].isin(selected_zips))
        & (df["score"] >= min_score)
        & (df["beds"].isin(selected_beds))
    ].copy()

    # --- Top Summary Stats ---
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    total_scanned = len(df)
    avg_score = filtered_df["score"].mean() if not filtered_df.empty else 0
    num_1pct = filtered_df["meets_1pct_rule"].sum() if "meets_1pct_rule" in filtered_df.columns else 0
    
    # Calculate avg tax increase
    tax_increases = []
    for t in filtered_df.get("tax_reset", []):
        if isinstance(t, dict) and t.get("tax_increase_pct") is not None:
            tax_increases.append(t["tax_increase_pct"])
    avg_tax_inc = sum(tax_increases) / len(tax_increases) if tax_increases else 0

    with col1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Total Deals Filtered</div><div class='metric-value'>{len(filtered_df)} / {total_scanned}</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Avg Score</div><div class='metric-value'>{avg_score:.1f}</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Meets 1% Rule</div><div class='metric-value'>{num_1pct}</div></div>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Avg Tax Spike</div><div class='metric-value' style='color:#ff4b4b;'>+{avg_tax_inc:.1f}%</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Main Deals View ---
    if filtered_df.empty:
        st.info("No properties match the current filters.")
        return

    # Sort by score
    filtered_df = filtered_df.sort_values(by="score", ascending=False)

    for i, row in filtered_df.head(20).iterrows():
        # Handle dict fields correctly
        tax_data = row.get("tax_reset", {}) if isinstance(row.get("tax_reset"), dict) else {}
        
        with st.expander(f"⭐ {row.get('score', 0):.1f}/10 | {row.get('address')} — ${row.get('price', 0):,.0f}"):
            col_a, col_b = st.columns([2, 1])
            
            with col_a:
                # Key Metrics Table
                st.markdown("### Deal Metrics")
                metrics_df = pd.DataFrame([
                    {"Metric": "Price", "Value": f"${row.get('price', 0):,.0f}"},
                    {"Metric": "Est. Rent", "Value": f"${row.get('rent_estimate', 0):,.0f}/mo"},
                    {"Metric": "Gross Yield", "Value": f"{row.get('gross_yield_pct', 0):.1f}%"},
                    {"Metric": "Net Cash Flow", "Value": f"${row.get('net_monthly', 0):,.0f}/mo"},
                    {"Metric": "Cash on Cash", "Value": f"{row.get('cash_on_cash_pct', 0):.1f}%"},
                    {"Metric": "DOM", "Value": f"{row.get('dom', 'N/A')}"},
                ])
                st.dataframe(metrics_df, hide_index=True, use_container_width=True)
                
                # AI Summary
                st.markdown("### 🤖 AI Deal Summary")
                ai_sum = row.get('ai_summary', 'No summary available.')
                st.info(ai_sum)
                
            with col_b:
                # TAX RESET SHOCK (The Mic Drop)
                current_tax = tax_data.get('current_tax_annual')
                post_tax = tax_data.get('post_sale_tax_annual', 0)
                increase_pct = tax_data.get('tax_increase_pct')
                
                tax_html = "<div class='tax-shock'><h3>⚠️ Tax Reset Impact</h3>"
                if current_tax and increase_pct:
                    tax_html += f"<div class='big-numbers'>${current_tax:,.0f} ➔ ${post_tax:,.0f}</div>"
                    tax_html += f"<div>Annual Increase: <strong style='color:#ff4b4b;'>+{increase_pct:.1f}%</strong></div>"
                else:
                    tax_html += f"<div class='big-numbers'>Post-Sale Tax: ${post_tax:,.0f}/yr</div>"
                    tax_html += f"<div>(${tax_data.get('post_sale_tax_monthly', 0):,.0f}/mo)</div>"
                tax_html += "</div>"
                
                st.markdown(tax_html, unsafe_allow_html=True)
                
                # Score Breakdown
                st.markdown("### Score Breakdown")
                st.progress(row.get('score_yield', 0) / 10, text=f"Yield: {row.get('score_yield', 0):.1f}")
                st.progress(row.get('score_discount', 0) / 10, text=f"Discount: {row.get('score_discount', 0):.1f}")
                st.progress(row.get('score_urgency', 0) / 10, text=f"Urgency: {row.get('score_urgency', 0):.1f}")
                st.progress(row.get('score_risk', 0) / 10, text=f"Risk: {row.get('score_risk', 0):.1f}")
                
                # Links
                st.markdown(f"[🔗 View on Redfin]({row.get('url', '#')})")


if __name__ == "__main__":
    render_dashboard()
