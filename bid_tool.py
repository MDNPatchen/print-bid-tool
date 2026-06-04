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
        
        # Smarter column mapping to avoid the "ambiguous Series" error (grabbing duplicates)
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
            
            dynamic_paper_cost = round_cents(calculated_avg_price)
            web_width = selected_size
            basis_weight = selected_weight
            
            st.sidebar.success(f"Inventory Link Active: Average Cost is ${dynamic_paper_cost:.2f}/lb")
        else:
            inventory_loaded_successfully = False
    else:
        inventory_loaded_successfully = False

if not inventory_loaded_successfully:
    st.sidebar.warning("Using manual inputs. See error below:")
    st.sidebar.error(f"Diagnostic: {debug_message}")
    
    web_width = st.sidebar.number_input("Web Width (inches)", value=22.0)
    basis_weight = st.sidebar.number_input("Basis Weight (lbs)", value=27.7)
    dynamic_paper_cost = rates["newsprint_cost_per_lb"]

press_cutoff = st.sidebar.number_input("Press Cut-Off", value=21.25)

st.sidebar.header("Pre-Press & Press Room")
camera_plate_hours = st.sidebar.number_input("Camera/Plate hours", value=0.5)
run_hours = st.sidebar.number_input("Time for run (hours)", value=1.0)
num_leaders = st.sidebar.number_input("Number of press leaders", value=1)
num_helpers = st.sidebar.number_input("Number of press helpers", value=2)
make_ready_hours = st.sidebar.number_input("Make-ready/clean-up hours", value=0.5)

st.sidebar.header("Mailroom")
mailroom_leaders = st.sidebar.number_input("Mailroom Leaders", value=1)
mailroom_leader_hours = st.sidebar.number_input("Mailroom Leader Hours", value=3.0)
mailroom_helpers = st.sidebar.number_input("Mailroom Helpers", value=3)
mailroom_helper_hours = st.sidebar.number_input("Mailroom Helper Hours", value=1.0)

# ----- INVISIBLE MATH ENGINE -----
format_divisor = 2 if page_format == "Broadsheet" else (4 if page_format == "Tabloid" else 8)
run_multiplier = 2 if run_type == "Straight" else 1

black_plates = math.ceil(total_pages / format_divisor) * run_multiplier
color_plates = math.ceil(color_pages / format_divisor) * 3 * run_multiplier
total_plates = black_plates + color_plates

# Calculate total paper needed including the 750 waste copies
total_impressions_needed = (press_run + waste_copies) * total_pages
pages_per_pound = 1900000 / (web_width * press_cutoff * basis_weight)

total_pounds = total_impressions_needed / pages_per_pound

newsprint_cost = round_cents(total_pounds * dynamic_paper_cost)
black_ink_cost = round_cents(total_impressions_needed * rates["black_ink_cost_per_impression"])

leader_cost = round_cents(num_leaders * rates["press_leader_rate"] * run_hours)
helper_cost = round_cents(num_helpers * rates["press_helper_rate"] * run_hours)
make_ready_cost = round_cents(make_ready_hours * rates["make_ready_rate"])

press_maint_cost = round_cents(newsprint_cost * rates["press_overhead_maint_pct"])

plate_material_cost = round_cents(total_plates * rates["plate_cost"])
plate_maint_cost = round_cents(total_plates * rates["plate_overhead_maint"])
camera_plate_labor = round_cents(camera_plate_hours * rates["camera_plate_rate"])

color_ink_cost = round_cents(color_plates * (press_run / 1000) * rates["color_ink_cost_per_plate_m"])

mailroom_leader_cost = round_cents(mailroom_leaders * mailroom_leader_hours * rates["mailroom_leader_rate"])
mailroom_helper_cost = round_cents(mailroom_helpers * mailroom_helper_hours * rates["mailroom_helper_rate"])
total_mailroom_cost = round_cents(mailroom_leader_cost + mailroom_helper_cost)

subtotal = round_cents(sum([
    newsprint_cost, black_ink_cost, leader_cost, helper_cost, 
    make_ready_cost, press_maint_cost, plate_material_cost, 
    plate_maint_cost, camera_plate_labor, color_ink_cost, 
    total_mailroom_cost
]))

overhead_cost = round_cents(subtotal * rates["overhead_pct"])
total_cost = round_cents(subtotal + overhead_cost)
profit = round_cents(total_cost * rates["profit_margin"])
total_charge = round_cents(total_cost + profit)

# ----- DASHBOARD DISPLAY -----
st.header(f"Bid Summary: {customer_name} - {job_desc}")

st.caption(f"Calculated Plates: {black_plates} Black | {color_plates} Color (Total: {total_plates}) based on {page_format} / {run_type}")

col1, col2, col3 = st.columns(3)
col1.metric("Total Paper Cost", f"${newsprint_cost:.2f}")
col2.metric("Labor & Press", f"${(leader_cost + helper_cost + make_ready_cost + press_maint_cost + total_mailroom_cost):.2f}")
col3.metric("Pre-Press & Ink", f"${(plate_material_cost + plate_maint_cost + camera_plate_labor + black_ink_cost + color_ink_cost):.2f}")

st.divider()

st.subheader("Bottom Line")
b_col1, b_col2, b_col3, b_col4 = st.columns(4)
b_col1.metric("Subtotal", f"${subtotal:.2f}")
b_col2.metric("Overhead", f"${overhead_cost:.2f}")
b_col3.metric("Total Cost", f"${total_cost:.2f}")
b_col4.metric("Total Charge", f"${total_charge:.2f}")