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
    page_title="BPM Deal Scanner",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for light premium institutional theme
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #1E293B;
        }
        
        /* Snapshot Cards */
        .snapshot-container {
            display: flex;
            gap: 15px;
            margin-bottom: 25px;
            flex-wrap: wrap;
        }
        .snapshot-card {
            flex: 1;
            min-width: 150px;
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .snapshot-label { color: #1E3A5F; font-size: 14px; font-weight: 600; text-transform: uppercase; margin-bottom: 5px; }
        .snapshot-value { font-size: 24px; font-weight: 700; color: #1E293B; }
        .snapshot-value-small { font-size: 16px; font-weight: 700; color: #1E293B; line-height: 1.3; }

        /* Deal Cards */
        .deal-card {
            display: flex;
            flex-direction: row;
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            gap: 20px;
        }
        .deal-left { width: 65%; }
        .deal-right { width: 35%; }
        @media (max-width: 900px) {
            .deal-card { flex-direction: column; }
            .deal-left, .deal-right { width: 100%; }
        }

        .score-badge { padding: 5px 12px; border-radius: 20px; font-weight: 700; color: white; display: inline-block; text-align: center; }
        .score-badge-green { background: #16A34A; }
        .score-badge-amber { background: #D97706; }
        .score-badge-red { background: #DC2626; }

        .address-title { font-size: 20px; font-weight: 700; color: #1E293B; margin-left: 12px; vertical-align: middle;}
        .property-meta { color: #64748B; font-size: 14px; margin-top: 8px; }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .metric-box {
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 12px;
        }
        .metric-box-label { color: #64748B; font-size: 12px; font-weight: 400; text-transform: uppercase; }
        .metric-box-value { font-size: 18px; font-weight: 700; color: #1E293B; margin-top: 4px; }
        .metric-box-value.green { color: #16A34A; }

        .discount-badge { background: #DCFCE7; color: #16A34A; font-size: 11px; padding: 3px 6px; border-radius: 4px; font-weight: 600; margin-left: 6px; vertical-align: middle; }

        .additional-metrics {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-top: 15px;
            border-top: 1px solid #E2E8F0;
            padding-top: 15px;
        }
        .add-metric { font-size: 14px; }
        .add-metric-label { color: #64748B; font-weight: 400; }
        .add-metric-value { font-weight: 700; color: #1E293B; }
        .dom-green { color: #16A34A; font-weight: 700; }
        .dom-amber { color: #D97706; font-weight: 700; }
        .dom-red { color: #DC2626; font-weight: 700; }

        .ai-summary {
            background: #EFF6FF;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
            font-size: 14px;
            color: #1E3A5F;
            line-height: 1.5;
        }

        .redfin-btn {
            display: inline-block;
            background: #1E3A5F;
            color: #FFFFFF !important;
            padding: 10px 20px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
            margin-top: 15px;
            font-size: 14px;
            transition: background 0.2s;
        }
        .redfin-btn:hover { background: #152B47; }

        /* Right Column elements */
        .tax-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-left: 5px solid #E2E8F0;
            border-radius: 8px;
            padding: 18px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }
        .tax-card.increase { border-left-color: #DC2626; }
        .tax-card.decrease { border-left-color: #16A34A; }

        .tax-title { font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }
        .tax-flow { font-size: 15px; font-weight: 600; color: #1E293B; margin-bottom: 8px; }
        .tax-change { font-size: 22px; font-weight: 700; }
        .tax-change.increase { color: #DC2626; }
        .tax-change.decrease { color: #16A34A; }
        .tax-millage { font-size: 12px; color: #64748B; margin-top: 8px; }

        .score-bars-container { margin-top: 15px; }
        .score-bar-row { display: flex; align-items: center; margin-bottom: 10px; font-size: 13px; }
        .score-bar-label { width: 70px; color: #64748B; font-weight: 600; }
        .score-bar-bg { flex-grow: 1; background: #E2E8F0; height: 8px; border-radius: 4px; margin: 0 12px; overflow: hidden; }
        .score-bar-fill { background: #16A34A; height: 100%; border-radius: 4px; }
        .score-bar-value { width: 30px; text-align: right; font-weight: 700; color: #1E293B; }

        .one-pct-badge { margin-top: 15px; font-size: 13px; font-weight: 700; padding: 8px 12px; border-radius: 6px; display: inline-block; width: 100%; text-align: center; box-sizing: border-box; }
        .one-pct-yes { background: #DCFCE7; color: #16A34A; border: 1px solid #BBF7D0; }
        .one-pct-no { background: #F1F5F9; color: #64748B; border: 1px solid #E2E8F0; }

        /* Custom Table */
        .custom-table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; background: white; border: 1px solid #E2E8F0; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .custom-table th { background: #F8FAFC; padding: 12px 15px; text-align: left; font-weight: 600; color: #1E3A5F; border-bottom: 1px solid #E2E8F0; }
        .custom-table td { padding: 12px 15px; border-bottom: 1px solid #E2E8F0; color: #1E293B; }
        .custom-table tr:last-child td { border-bottom: none; }
        .custom-table .td-number { font-weight: 700; }
        .custom-table .td-red { color: #DC2626; font-weight: 700; }
        .custom-table .td-green { color: #16A34A; font-weight: 700; }
        
        /* Hide some default streamlit stuff to look cleaner */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=600)
def load_latest_data() -> pd.DataFrame:
    """Load the most recent scored listings from BigQuery or local fallback."""
    df = pd.DataFrame()
    try:
        from google.cloud import bigquery
        from google.oauth2 import service_account
        
        if "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"]
            )
            client = bigquery.Client(project="profitscout-fida8", credentials=creds)
        else:
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
        
        if data:
            logger.info("Successfully loaded latest scan data from BigQuery.")
            df = pd.DataFrame(data)
    except Exception as e:
        logger.warning(f"BigQuery load failed (falling back to local files): {e}")

    # Fallback to local data directory
    if df.empty and DATA_DIR.exists():
        files = list(DATA_DIR.glob("final_results_*.json"))
        if files:
            latest_file = max(files, key=os.path.getctime)
            try:
                with open(latest_file, "r") as f:
                    data = json.load(f)
                logger.info(f"Loaded data from local file {latest_file}.")
                df = pd.DataFrame(data)
            except Exception as e:
                logger.error(f"Failed to load data from {latest_file}: {e}")

    # Deduplication
    if not df.empty and "listing_id" in df.columns:
        if "scraped_at" in df.columns:
            df["scraped_at_dt"] = pd.to_datetime(df["scraped_at"], errors="coerce")
            df = df.sort_values("scraped_at_dt", ascending=False).drop_duplicates(subset=["listing_id"])
            df = df.drop(columns=["scraped_at_dt"])
        else:
            df = df.drop_duplicates(subset=["listing_id"])
            
    return df


def generate_snapshot_html(filtered_df, total_scanned, zip_codes):
    if filtered_df.empty:
        return ""
        
    zip_display = "Multiple" if len(zip_codes) > 1 else (zip_codes[0] if zip_codes else "All")
    passed_filter = len(filtered_df)
    avg_score = filtered_df["score"].mean() if pd.notna(filtered_df["score"].mean()) else 0
    
    # Best deal
    best_deal = filtered_df.iloc[0]
    best_address = best_deal.get("address", "N/A")
    best_coc = best_deal.get("cash_on_cash_pct")
    best_coc_str = f"{best_coc:.1f}%" if pd.notna(best_coc) else "N/A"
    
    html = f"""
    <div class="snapshot-container">
        <div class="snapshot-card">
            <div class="snapshot-label">Zip</div>
            <div class="snapshot-value">{zip_display}</div>
        </div>
        <div class="snapshot-card">
            <div class="snapshot-label">Scanned</div>
            <div class="snapshot-value">{total_scanned}</div>
        </div>
        <div class="snapshot-card">
            <div class="snapshot-label">Passed Filter</div>
            <div class="snapshot-value">{passed_filter}</div>
        </div>
        <div class="snapshot-card">
            <div class="snapshot-label">Avg Score</div>
            <div class="snapshot-value">{avg_score:.1f}/10</div>
        </div>
        <div class="snapshot-card">
            <div class="snapshot-label">Best Deal</div>
            <div class="snapshot-value-small">{best_address}<br><span style="color:#16A34A;">{best_coc_str} CoC</span></div>
        </div>
    </div>
    """
    return html

def generate_deal_card_html(row):
    address = row.get("address", "Unknown Address")
    score = float(row.get("score", 0)) if pd.notna(row.get("score")) else 0
    
    if score >= 7:
        score_class = "score-badge-green"
    elif score >= 5:
        score_class = "score-badge-amber"
    else:
        score_class = "score-badge-red"
        
    prop_type = row.get("property_type", "N/A")
    sqft = row.get("sqft")
    sqft_str = f"{sqft:,.0f} sqft" if pd.notna(sqft) else "N/A sqft"
    beds = row.get("beds")
    baths = row.get("baths")
    
    beds_str = f"{beds}bd" if pd.notna(beds) else "?bd"
    baths_str = f"{baths}ba" if pd.notna(baths) else "?ba"
    beds_baths = f"{beds_str} / {baths_str}"
    
    price = row.get("price")
    price_str = f"${price:,.0f}" if pd.notna(price) else "N/A"
    
    discount_pct = row.get("discount_to_value_pct")
    discount_html = ""
    if pd.notna(discount_pct) and discount_pct > 15:
        discount_html = f"<span class='discount-badge'>{discount_pct:.0f}% below market</span>"
        
    rent_low = row.get("rent_low")
    rent_high = row.get("rent_high")
    rent_est = row.get("rent_estimate")
    if pd.notna(rent_low) and pd.notna(rent_high) and rent_low > 0:
        rent_str = f"${rent_low:,.0f} - ${rent_high:,.0f}"
    elif pd.notna(rent_est):
        rent_str = f"${rent_est:,.0f}"
    else:
        rent_str = "N/A"
        
    net_cf = row.get("net_monthly")
    net_cf_str = f"${net_cf:,.0f}" if pd.notna(net_cf) else "N/A"
    
    coc = row.get("cash_on_cash_pct")
    coc_str = f"{coc:.1f}%" if pd.notna(coc) else "N/A"
    
    gross_yield = row.get("gross_yield_pct")
    gy_str = f"{gross_yield:.1f}%" if pd.notna(gross_yield) else "N/A"
    
    cap_rate = row.get("cap_rate_pct")
    cap_str = f"{cap_rate:.1f}%" if pd.notna(cap_rate) else "N/A"
    
    price_sqft = row.get("price_per_sqft")
    psqft_str = f"${price_sqft:,.0f}" if pd.notna(price_sqft) else "N/A"
    
    dom = row.get("dom")
    if pd.isna(dom):
        dom_html = "<span class='add-metric-value'>N/A</span>"
    else:
        if dom > 90:
            dom_html = f"<span class='dom-green'>{int(dom)} days (Negotiation Leverage)</span>"
        elif dom >= 30:
            dom_html = f"<span class='dom-amber'>{int(dom)} days</span>"
        else:
            dom_html = f"<span class='dom-red'>{int(dom)} days (Moving Fast)</span>"
            
    ai_summary = row.get("ai_summary")
    if pd.isna(ai_summary) or not str(ai_summary).strip():
        ai_summary = "Analysis not available for this property."
        
    url = row.get("url", "#")
    
    # Right column variables
    tax_data = row.get("tax_reset")
    if isinstance(tax_data, str):
        try:
            tax_data = json.loads(tax_data)
        except:
            tax_data = {}
    elif not isinstance(tax_data, dict):
        tax_data = {}
        
    current_tax = tax_data.get("current_tax_annual")
    post_tax = tax_data.get("post_sale_tax_annual")
    tax_inc_pct = tax_data.get("tax_increase_pct")
    tax_inc_ann = tax_data.get("tax_increase_annual")
    millage = tax_data.get("millage_rate")
    
    tax_card_class = "tax-card"
    if pd.notna(tax_inc_pct):
        if tax_inc_pct > 0:
            tax_card_class += " increase"
        elif tax_inc_pct < 0:
            tax_card_class += " decrease"
            
    if pd.isna(tax_inc_pct) or pd.isna(current_tax) or pd.isna(post_tax):
        tax_content = "<div class='tax-flow' style='color:#64748B;'>Tax data unavailable</div>"
    else:
        ct_str = f"${current_tax:,.0f}"
        pt_str = f"${post_tax:,.0f}"
        
        inc_class = "increase" if tax_inc_pct > 0 else ("decrease" if tax_inc_pct < 0 else "")
        sign = "+" if tax_inc_pct > 0 else ""
        
        tax_content = f"""
            <div class='tax-flow'>{ct_str} &rarr; {pt_str}</div>
            <div class='tax-change {inc_class}'>{sign}${tax_inc_ann:,.0f} ({sign}{tax_inc_pct:.1f}%)</div>
        """
        if pd.notna(millage):
            tax_content += f"<div class='tax-millage'>Millage Rate: {millage:.4f}</div>"

    def score_bar(label, val):
        val = 0 if pd.isna(val) else val
        pct = min(100, max(0, val * 10))
        return f"""
        <div class='score-bar-row'>
            <div class='score-bar-label'>{label}</div>
            <div class='score-bar-bg'><div class='score-bar-fill' style='width: {pct}%'></div></div>
            <div class='score-bar-value'>{val:.1f}</div>
        </div>
        """
        
    score_bars_html = score_bar("Yield", row.get("score_yield")) + \
                      score_bar("Discount", row.get("score_discount")) + \
                      score_bar("Urgency", row.get("score_urgency")) + \
                      score_bar("Risk", row.get("score_risk"))
                      
    meets_1pct = row.get("meets_1pct_rule")
    if pd.notna(meets_1pct) and meets_1pct:
        one_pct_html = "<div class='one-pct-badge one-pct-yes'>✅ MEETS 1% RULE</div>"
    else:
        one_pct_html = "<div class='one-pct-badge one-pct-no'>Does not meet 1% rule</div>"

    html = f"""
    <div class="deal-card">
        <div class="deal-left">
            <div style="margin-bottom: 8px;">
                <span class="score-badge {score_class}">{score:.1f}</span>
                <span class="address-title">{address}</span>
            </div>
            <div class="property-meta">{prop_type} • {sqft_str} • {beds_baths}</div>
            
            <div class="metrics-grid">
                <div class="metric-box">
                    <div class="metric-box-label">Price</div>
                    <div class="metric-box-value">{price_str}{discount_html}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-box-label">Rent Estimate</div>
                    <div class="metric-box-value">{rent_str}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-box-label">Net Cash Flow</div>
                    <div class="metric-box-value green">{net_cf_str}/mo</div>
                </div>
                <div class="metric-box">
                    <div class="metric-box-label">Cash on Cash</div>
                    <div class="metric-box-value green">{coc_str}</div>
                </div>
            </div>
            
            <div class="additional-metrics">
                <div class="add-metric"><span class="add-metric-label">Gross Yield:</span> <span class="add-metric-value">{gy_str}</span></div>
                <div class="add-metric"><span class="add-metric-label">Cap Rate:</span> <span class="add-metric-value">{cap_str}</span></div>
                <div class="add-metric"><span class="add-metric-label">Price/sqft:</span> <span class="add-metric-value">{psqft_str}</span></div>
                <div class="add-metric"><span class="add-metric-label">DOM:</span> {dom_html}</div>
            </div>
            
            <div class="ai-summary">
                <strong>🤖 AI Deal Summary:</strong> {ai_summary}
            </div>
            
            <a href="{url}" target="_blank" class="redfin-btn">View on Redfin &rarr;</a>
        </div>
        
        <div class="deal-right">
            <div class="{tax_card_class}">
                <div class="tax-title">Post-Sale Tax Impact</div>
                {tax_content}
            </div>
            
            <div class="score-bars-container">
                {score_bars_html}
            </div>
            
            {one_pct_html}
        </div>
    </div>
    """
    return html

def generate_tax_table_html(df):
    tax_rows = []
    for _, row in df.iterrows():
        tax_data = row.get("tax_reset")
        if isinstance(tax_data, str):
            try: tax_data = json.loads(tax_data)
            except: tax_data = {}
        elif not isinstance(tax_data, dict):
            tax_data = {}
            
        inc_pct = tax_data.get("tax_increase_pct")
        if pd.notna(inc_pct):
            tax_rows.append({
                "address": row.get("address", "N/A"),
                "price": row.get("price"),
                "current_tax": tax_data.get("current_tax_annual"),
                "post_tax": tax_data.get("post_sale_tax_annual"),
                "inc_ann": tax_data.get("tax_increase_annual"),
                "inc_pct": inc_pct
            })
            
    if not tax_rows:
        return ""
        
    tax_df = pd.DataFrame(tax_rows).sort_values("inc_pct", ascending=False)
    
    html = """
    <div style="margin-top: 50px; margin-bottom: 20px;">
        <h2 style="color: #1E3A5F; font-size: 24px; margin-bottom: 5px;">⚠️ Post-Sale Tax Reset Analysis</h2>
        <p style="color: #64748B; margin-top: 0; font-size: 15px;">Most investors don't calculate this until after closing. Here's what your tax bill actually looks like.</p>
    </div>
    <table class="custom-table">
        <thead>
            <tr>
                <th>Address</th>
                <th>Price</th>
                <th>Current Tax</th>
                <th>Post-Sale Tax</th>
                <th>Annual Change</th>
                <th>Tax Shock %</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for _, row in tax_df.iterrows():
        price_str = f"${row['price']:,.0f}" if pd.notna(row['price']) else "N/A"
        ct_str = f"${row['current_tax']:,.0f}" if pd.notna(row['current_tax']) else "N/A"
        pt_str = f"${row['post_tax']:,.0f}" if pd.notna(row['post_tax']) else "N/A"
        
        inc_ann = row['inc_ann']
        inc_pct = row['inc_pct']
        
        sign = "+" if inc_pct > 0 else ""
        inc_ann_str = f"{sign}${inc_ann:,.0f}" if pd.notna(inc_ann) else "N/A"
        inc_pct_str = f"{sign}{inc_pct:.1f}%" if pd.notna(inc_pct) else "N/A"
        
        color_class = "td-red" if inc_pct > 0 else ("td-green" if inc_pct < 0 else "")
            
        html += f"""
            <tr>
                <td style="font-weight: 600;">{row['address']}</td>
                <td>{price_str}</td>
                <td>{ct_str}</td>
                <td class="td-number">{pt_str}</td>
                <td class="{color_class}">{inc_ann_str}</td>
                <td class="{color_class}">{inc_pct_str}</td>
            </tr>
        """
        
    html += """
        </tbody>
    </table>
    """
    return html

def render_dashboard():
    # Load Data
    df = load_latest_data()

    if df.empty:
        st.warning("No data available. Run the pipeline first.")
        return
        
    total_scanned = len(df)

    # --- Sidebar ---
    st.sidebar.markdown("<h2 style='color:#1E3A5F; margin-bottom:0;'>🏛️ BPM Deal Scanner</h2>", unsafe_allow_html=True)
    st.sidebar.markdown("<p style='color:#64748B; font-size:14px; margin-top:0;'>AI-Powered Deal Sourcing</p>", unsafe_allow_html=True)
    
    st.sidebar.markdown("### Filters")

    # Price Range
    min_price = int(df["price"].min()) if not df["price"].empty and pd.notna(df["price"].min()) else 100000
    max_price = int(df["price"].max()) if not df["price"].empty and pd.notna(df["price"].max()) else 1000000
    if min_price == max_price:
        max_price += 100000
    
    price_range = st.sidebar.slider(
        "Price Range ($)",
        min_value=min_price,
        max_value=max_price,
        value=(min_price, max_price),
        step=10000,
    )

    # Minimum Score
    min_score = st.sidebar.slider(
        "Minimum Score",
        min_value=0.0,
        max_value=10.0,
        value=5.0,
        step=0.5,
    )

    # Beds
    bed_options = sorted([int(b) for b in df["beds"].dropna().unique()])
    selected_beds = st.sidebar.multiselect("Beds", bed_options, default=bed_options)
    
    # Zip Codes
    zip_codes = sorted([str(z) for z in df["zip_code"].dropna().unique()])
    selected_zips = st.sidebar.multiselect("Zip Codes", zip_codes, default=zip_codes)

    meets_1pct_only = st.sidebar.checkbox("Meets 1% Rule Only", value=False)
    tax_decrease_only = st.sidebar.checkbox("Tax Decrease Only", value=False)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("<div style='font-size:12px; color:#64748B;'>Powered by <a href='#' style='color:#2563EB;'>EvanParra.ai</a></div>", unsafe_allow_html=True)

    # --- Apply Filters ---
    filtered_df = df[
        (df["price"] >= price_range[0])
        & (df["price"] <= price_range[1])
        & (df["score"] >= min_score)
    ]
    
    if selected_zips:
        filtered_df = filtered_df[filtered_df["zip_code"].astype(str).isin(selected_zips)]
        
    if selected_beds:
        filtered_df = filtered_df[filtered_df["beds"].isin(selected_beds)]
        
    if meets_1pct_only and "meets_1pct_rule" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["meets_1pct_rule"] == True]
        
    if tax_decrease_only:
        def is_tax_decrease(tax_data):
            if isinstance(tax_data, str):
                try: tax_data = json.loads(tax_data)
                except: return False
            if isinstance(tax_data, dict):
                inc_pct = tax_data.get("tax_increase_pct")
                return pd.notna(inc_pct) and inc_pct < 0
            return False
            
        if "tax_reset" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["tax_reset"].apply(is_tax_decrease)]

    # --- Sort by score ---
    filtered_df = filtered_df.sort_values(by="score", ascending=False)
    
    # --- UI Layout ---
    # Section 1
    st.markdown(generate_snapshot_html(filtered_df, total_scanned, selected_zips), unsafe_allow_html=True)
    
    # Section 2
    if filtered_df.empty:
        st.info("No properties match the current filters.")
        return
        
    showing_count = min(len(filtered_df), 20)
    st.markdown(f"<p style='color:#64748B; font-size:14px; margin-bottom:20px;'>Showing top {showing_count} of {len(filtered_df)} deals matching your criteria</p>", unsafe_allow_html=True)
    
    for i, row in filtered_df.head(20).iterrows():
        card_html = generate_deal_card_html(row)
        st.markdown(card_html, unsafe_allow_html=True)
        
    # Section 3
    tax_table_html = generate_tax_table_html(filtered_df)
    if tax_table_html:
        st.markdown(tax_table_html, unsafe_allow_html=True)


if __name__ == "__main__":
    render_dashboard()