import streamlit as st
import pandas as pd
import math
import re
import os
import csv

# Helper to aggressively round up to the nearest cent
def round_cents(val):
    return math.ceil(val * 100) / 100

# --- USER ACCESS DICTIONARY ---
AUTHORIZED_USERS = {
    "bob patchen": ["Minot", "Madelia (HOP)"], 
    "mike christman": ["Minot", "Madelia (HOP)"],         
    "brenda ahern": ["Madelia (HOP)"],
    "terry saar": ["Madelia (HOP)"]
}

LOCATIONS = {
    "Madelia (HOP)": {
        "profit_margin": 0.25,
        "overhead_pct": 0.26,
        "newsprint_cost_per_lb": 0.35, 
        "black_ink_cost_per_impression": 0.0006,
        "press_leader_rate": 30.00,
        "press_helper_rate": 25.00,
        "camera_plate_rate": 30.00,
        "make_ready_rate": 30.00,
        "press_overhead_maint_pct": 0.10,
        "plate_cost": 5.25,
        "plate_overhead_maint": 0.75,
        "color_ink_cost_per_plate_m": 0.95,
        "mailroom_leader_rate": 30.00,
        "mailroom_helper_rate": 25.00,
    },
    "Minot": {
        "profit_margin": 0.25, 
        "overhead_pct": 0.26,
        "newsprint_cost_per_lb": 0.35, 
        "black_ink_cost_per_impression": 0.0006,
        "press_leader_rate": 31.34,
        "press_helper_rate": 22.43,
        "camera_plate_rate": 30.00,
        "make_ready_rate": 31.34, 
        "press_overhead_maint_pct": 0.10,
        "plate_cost": 5.25,
        "plate_overhead_maint": 0.75,
        "color_ink_cost_per_plate_m": 0.95,
        "mailroom_leader_rate": 24.11,
        "mailroom_helper_rate": 16.15, 
    }
}

# --- BULLETPROOF RAW TEXT INVENTORY LOADER ---
def load_inventory_data(location_name):
    base_name = location_name.split(" ")[0].lower()
    
    all_files = os.listdir('.')
    target_file = None
    for f in all_files:
        if base_name in f.lower() and f.lower().endswith('.csv'):
            target_file = f
            break
            
    if not target_file:
        return pd.DataFrame(), f"Could not find any CSV file containing '{base_name}' in the vault."
        
    try:
        # Bypassing Pandas for the initial read to avoid comma-mismatch errors
        with open(target_file, 'r', encoding='latin1', errors='replace') as f:
            reader = csv.reader(f)
            data = list(reader)
            
        header_idx = -1
        for i, row in enumerate(data):
            if len(row) > 0 and 'Ownership' in str(row[0]):
                header_idx = i
                break
                
        if header_idx == -1:
            return pd.DataFrame(), f"Found '{target_file}', but couldn't locate the 'Ownership' header row."
            
        # Manually construct the clean dataframe
        headers = [str(h).strip() for h in data[header_idx]]
        rows = data[header_idx+1:]
        df = pd.DataFrame(rows, columns=headers)
        
        col_map = {}
        for col in df.columns:
            cl = str(col).lower()
            if 'grammage' in cl: col_map[col] = 'Target_Grammage'
            if 'width' in cl: col_map[col] = 'Target_Width'
            if 'price/mt' in cl or 'price / mt' in cl: col_map[col] = 'Target_Price'
            
        df = df.rename(columns=col_map)
        
        if 'Target_Price' not in df.columns or 'Target_Grammage' not in df.columns or 'Target_Width' not in df.columns:
            return pd.DataFrame(), f"Loaded file, but couldn't identify the Grammage, Width, or Price/mt columns."
            
        def extract_num(val):
            if pd.isna(val) or val is None or val == '': return None
            match = re.search(r'[\d\.]+', str(val))
            return float(match.group()) if match else None
            
        df['Target_Price_Num'] = df['Target_Price'].apply(extract_num)
        df['Target_Width_Num'] = df['Target_Width'].apply(extract_num)
        df['Target_Grammage_Num'] = df['Target_Grammage'].apply(extract_num)
        
        df = df.dropna(subset=['Target_Price_Num', 'Target_Width_Num', 'Target_Grammage_Num'])
        
        df['Price/lb'] = (df['Target_Price_Num'] / 2204.62).apply(lambda x: round_cents(x))
        df['Paper Size (Inches)'] = (df['Target_Width_Num'] / 25.4).round(2)
        df['Paper Weight (#)'] = (df['Target_Grammage_Num'] * 0.61386).round(1)
        
        df = df.dropna(subset=['Paper Size (Inches)', 'Paper Weight (#)', 'Price/lb'])
        
        if df.empty:
            return df, "File loaded, but no valid numeric data remained after cleaning."
            
        return df, "Success"
    except Exception as e:
        return pd.DataFrame(), f"System error reading file: {str(e)}"

st.set_page_config(page_title="Print Production Bid Tool", layout="wide")
st.title("📰 Newspaper Job Bid Worksheet")

# ----- THE GATEKEEPER -----
st.sidebar.header("System Access")
entered_name = st.sidebar.text_input("Enter User Name:").strip().lower()

if not entered_name:
    st.info("Please enter your assigned name in the sidebar to unlock the tool.")
    st.stop()

if entered_name not in AUTHORIZED_USERS:
    st.error("Name not recognized by the system. Check your spelling.")
    st.stop()

# ----- SIDEBAR INPUTS -----
st.sidebar.header("Job Specs & Location")

allowed_facilities = AUTHORIZED_USERS[entered_name]
selected_location = st.sidebar.selectbox("Select Production Facility", allowed_facilities)
rates = LOCATIONS[selected_location]

customer_name = st.sidebar.text_input("Customer", "Mantako")
job_desc = st.sidebar.text_input("Job Description", "Free Press")
press_run = st.sidebar.number_input("Press Run", value=5890, step=100)

# Static Waste Calculation Display
waste_copies = 750
calculated_waste_pct = min(100.0, (waste_copies / press_run) * 100) if press_run > 0 else 100.0
st.sidebar.info(f"**Press Waste:** {waste_copies} copies ({calculated_waste_pct:.1f}%)")

st.sidebar.subheader("Format & Pagination")
page_format = st.sidebar.selectbox("Page Format", ["Broadsheet", "Tabloid", "Book"])
run_type = st.sidebar.selectbox("Run Type", ["Collect", "Straight"])
total_pages = st.sidebar.number_input("Total Pages", value=16)
color_pages = st.sidebar.number_input("Color Pages", value=4)

st.sidebar.subheader("Web Specifications & Paper Stock")

# Dynamic Inventory Integration
inventory_df, debug_message = load_inventory_data(selected_location)
inventory_loaded_successfully = False

if not inventory_df