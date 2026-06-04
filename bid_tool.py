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
    "boat hen": ["Minot", "Madelia (HOP)"], # The phantom master key
    "mike christman": ["Minot", "Madelia (HOP)"],         
    "brenda ahern": ["Madelia (HOP)"],
    "terry saar": ["Madelia (HOP)"]
}

LOCATIONS = {
    "Madelia (HOP)": {
        "profit_margin": 0.25,
        "overhead_pct": 0.26,
        "newsprint_cost_per_lb": 0.35, 
        "waste_pct": 0.10,
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
        "waste_pct": 0.10,
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
            
        headers = [str(h).strip() for h in data[header_idx]]
        rows = data[header_idx+1:]
        df = pd.DataFrame(rows, columns=headers)
        
        col_map = {}
        for col in df.columns:
            cl = str(col).lower()
            if 'grammage' in cl and 'Target_Grammage' not in col_map.values(): 
                col_map[col] = 'Target_Grammage'
            elif 'width' in cl and 'Target_Width' not in col_map.values(): 
                col_map[col] = 'Target_Width'
            elif ('price/mt' in cl or 'price / mt' in cl) and 'net' not in cl and 'Target_Price' not in col_map.values(): 
                col_map[col] = 'Target_Price'
            
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

# Flexible Waste Calculation Input
waste_copies = st.sidebar.number_input("Waste Copies", value=589, step=50)
calculated_waste_pct = (waste_copies / press_run) * 100 if press_run > 0 else 100.0
st.sidebar.info(f"**Calculated Waste:** {calculated_waste_pct:.1f}% of press run")

st.sidebar.subheader("Format & Pagination")
page_format = st.sidebar.selectbox("Page Format", ["Broadsheet", "Tabloid", "Book"])
run_type = st.sidebar.selectbox("Run Type", ["Collect", "Straight"])
total_pages = st.sidebar.number_input("Total Pages", value=20)
color_pages = st.sidebar.number_input("Color Pages", value=4)

st.sidebar.subheader("Web Specifications & Paper Stock")

# The invisible 10% markup multiplier for paper handling
markup_multiplier = 1.10 

# Dynamic Inventory Integration
inventory_df, debug_message = load_inventory_data(selected_location)
inventory_loaded_successfully = False

if not inventory_df.empty:
    sizes = sorted(inventory_df['Paper Size (Inches)'].unique().tolist())
    
    if len(sizes) > 0:
        inventory_loaded_successfully = True
        selected_size = st.sidebar.selectbox("Paper Size (Web Width in inches)", sizes)
        
        filtered_by_size = inventory_df[inventory_df['Paper Size (Inches)'] == selected_size]
        weights = sorted(filtered_by_size['Paper Weight (#)'].unique().tolist())
        
        if len(weights) > 0:
            selected_weight = st.sidebar.selectbox("Paper Weight (Basis lbs)", weights)
            
            filtered_final = filtered_by_size[filtered_by_size['Paper Weight (#)'] == selected_weight]
            calculated_avg_price = filtered_final['Price/lb'].mean()
            
            # Apply the markup directly to the cost
            dynamic_paper_cost = round_cents(calculated_avg_price * markup_multiplier)
            
            web_width = selected_size
            basis_weight = selected_weight
            
            st.sidebar.success(f"Inventory Link Active: ${dynamic_paper_cost:.2f}/lb")
        else:
            inventory_loaded_successfully = False
    else:
        inventory_loaded_successfully = False

if not inventory_loaded_successfully:
    st.sidebar.warning("Using manual inputs. See error below:")
    st.sidebar.error(f"Diagnostic: {debug_message}")
    
    web_width = st.sidebar.number_input("Web Width (inches)", value=22.0)
    basis_weight = st.sidebar.number_input("Basis Weight (lbs)", value=27.7)