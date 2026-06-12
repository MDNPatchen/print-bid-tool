import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CORE ROBUST PARSING & UTILITIES
# ==========================================

def clean_string_key(val):
    """
    Normalizes strings to prevent lookups from failing due to minor
    formatting discrepancies (e.g., quotes, spaces, trailing units).
    """
    if pd.isna(val):
        return ""
    s = str(val).lower().strip()
    # Remove common characters that cause mismatch heartaches
    for char in ['"', "'", '#', 'lb', 'pound', 'inch', 'ins', '-']:
        s = s.replace(char, '')
    return " ".join(s.split())

def load_and_normalize_inventory(uploaded_file):
    """
    Loads the inventory CSV and creates a normalized lookup key 
    combining the facility, width, and weight to bypass strict string traps.
    """
    try:
        df = pd.read_csv(uploaded_file)
        
        # Ensure critical columns exist, fallback to case-insensitive check
        df.columns = [c.strip() for c in df.columns]
        
        # Creating a bulletproof lookup key
        df['match_key'] = (
            df['facility'].apply(clean_string_key) + "_" +
            df['width'].apply(clean_string_key) + "_" +
            df['weight'].apply(clean_string_key)
        )
        
        # Clean up cost data types (strip currency symbols if any)
        if 'cost' in df.columns:
            if df['cost'].dtype == object:
                df['cost'] = df['cost'].str.replace('$', '').str.replace(',', '').astype(float)
        else:
            df['cost'] = 0.0
            
        return df
    except Exception as e:
        st.error(f"Error parsing inventory CSV: {e}")
        return pd.DataFrame()

# ==========================================
# 2. BIDDING LOGIC ENGINE
# ==========================================

def calculate_print_bid(facility, width, weight, quantity, running_hours, base_labor_rate, inventory_df):
    """
    Computes exact production costs enforcing safety floors and markups.
    """
    # 1. Look up unit cost safely
    target_key = clean_string_key(facility) + "_" + clean_string_key(width) + "_" + clean_string_key(weight)
    
    match = inventory_df[inventory_df['match_key'] == target_key]
    
    if not match.empty:
        # Pull the cost from the first valid match
        unit_paper_cost = float(match.iloc[0]['cost'])
        is_fallback = False
    else:
        # Safe fallback instead of failing silently or crashing
        unit_paper_cost = 0.0
        is_fallback = True

    # 2. Apply explicit 10% paper handling markup
    raw_paper_cost = unit_paper_cost * quantity
    paper_markup_multiplier = 1.10
    final_paper_cost = raw_paper_cost * paper_markup_multiplier
    
    # 3. Enforce dynamic labor hour floor (e.g., minimum 2 hours minimum setup)
    MIN_LABOR_FLOOR = 2.0
    billable_hours = max(float(running_hours), MIN_LABOR_FLOOR)
    labor_cost = billable_hours * base_labor_rate
    
    # Hypothetical flat ink calculation based on volume/quantity for baseline
    ink_cost_estimate = (quantity * 0.015) 
    
    total_job_cost = final_paper_cost + labor_cost + ink_cost_estimate
    
    return {
        "unit_paper_cost": unit_paper_cost,
        "final_paper_cost": final_paper_cost,
        "billable_hours": billable_hours,
        "labor_cost": labor_cost,
        "ink_cost": ink_cost_estimate,
        "total_cost": total_job_cost,
        "is_fallback": is_fallback
    }

# ==========================================
# 3. STREAMLIT UI & STATE MANAGEMENT
# ==========================================

st.set_page_config(page_title="Print Production Bidding System", layout="wide")

st.title("🖨️ Production Bid Estimator Engine")
st.caption("Madelia | Minot | Webster City Core Hub")

# Session state initialization for historical tracking
if 'quote_history' not in st.session_state:
    st.session_state.quote_history = []
if 'inventory_data' not in st.session_state:
    st.session_state.inventory_data = pd.DataFrame()

# Sidebar: CSV Inventory Ingestion
st.sidebar.header("Data Sync Options")
uploaded_file = st.sidebar.file_uploader("Upload Master Stock CSV", type=["csv"])

if uploaded_file is not None:
    st.session_state.inventory_data = load_and_normalize_inventory(uploaded_file)
    st.sidebar.success(f"Loaded {len(st.session_state.inventory_data)} stock rows successfully!")

# Main Layout split into Input parameters and Live Costing Readout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Job Specification Configuration")
    
    selected_facility = st.selectbox("Production Facility", ["Madelia", "Minot", "Webster City"])
    
    # Text fields instead of rigid drop-downs allows flexible typing without breaking
    paper_width = st.text_input("Paper Roll Width (e.g., 34\")", value="34\"")
    paper_weight = st.text_input("Paper Weight Basis (e.g., 45.4#)", value="45.4#")
    
    job_quantity = st.number_input("Total Roll Run/Quantity", min_value=1, value=10, step=1)
    estimated_hours = st.number_input("Estimated Run Time (Hours)", min_value=0.0, value=1.5, step=0.5)
    hourly_labor_rate = st.number_input("Standard Labor Rate ($/Hr)", min_value=0.0, value=45.0, step=2.50)
    
    calculate_trigger = st.button("Generate Bid Assessment", type="primary")

with col2:
    st.subheader("Costing Breakout Engine")
    
    if calculate_trigger:
        if st.session_state.inventory_data.empty:
            st.warning("⚠️ No active inventory sheet detected. Using $0.00 base rate defaults for paper mock calculations.")
        
        # Execute calculation mapping
        results = calculate_print_bid(
            facility=selected_facility,
            width=paper_width,
            weight=paper_weight,
            quantity=job_quantity,
            running_hours=estimated_hours,
            base_labor_rate=hourly_labor_rate,
            inventory_df=st.session_state.inventory_data
        )
        
        # Display breakdown alerts for anomalies
        if results['is_fallback']:
            st.error(f"🔴 Spec Warning: No exact pricing found for {paper_width} width, {paper_weight} paper at {selected_facility}. Costs defaulting to 0.")
        else:
            st.success("🟢 Verified Lookup Match Found in Database Grid.")

        # Metric Presentation Layout
        m1, m2 = st.columns(2)
        m1.metric("Base Unit Cost (per item/cwt)", f"${results['unit_paper_cost']:.4f}")
        m2.metric("Total Billable Job Cost", f"${results['total_cost']:.2f}")
        
        st.markdown("---")
        st.markdown("#### Itemized Ledger Details")
        
        # Summary Dataframe formatting
        breakdown_table = pd.DataFrame({
            "Cost Factor Category": ["Paper Supply Expense (Incl. 10% Handling)", "Operational Labor Cost Floor Applied", "Estimated Fluid Ink Spend", "Aggregated Estimate Gross"],
            "Calculated Amount": [results['final_paper_cost'], results['labor_cost'], results['ink_cost'], results['total_cost']],
            "Formula Elements Utilized": [f"Quantity {job_quantity} x Base Rate x 1.10", f"Hours Billed: {results['billable_hours']} hr Floor (Target: {estimated_hours} hr)", "Fixed volumetric standard projection markup", "Gross production margin target value"]
        })
        st.table(breakdown_table)
        
        # Retain history stamp
        new_record = {
            "Facility": selected_facility,
            "Specs": f"{paper_width} / {paper_weight}",
            "Billed Hours": results['billable_hours'],
            "Total Valuation Quote": f"${results['total_cost']:.2f}"
        }
        st.session_state.quote_history.append(new_record)

# Historical tracking ledger window at footer of app
st.markdown("---")
st.subheader("Historical Application Running Bids Ledger")
if st.session_state.quote_history:
    st.dataframe(pd.DataFrame(st.session_state.quote_history))
else:
    st.info("No run logs captured in active session layout state memory yet.")