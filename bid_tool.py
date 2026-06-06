import streamlit as st
import pandas as pd
import math
import re
import os
import csv
import datetime

def round_cents(val): 
    return round(val + 1e-9, 2)

def apply_floor(val): 
    v = float(val)
    if 0 < v < 1.0:
        return 1.0
    return v

AUTH = {
    "bob patchen": {"role": "admin", "facs": ["Madelia (HOP)", "Minot", "Webster City"]},
    "mike christman": {"role": "admin", "facs": ["Madelia (HOP)", "Minot", "Webster City"]},
    "boat hen": {"role": "admin", "facs": ["Madelia (HOP)", "Minot", "Webster City"]},
    "brenda ahern": {"role": "user", "facs": ["Madelia (HOP)", "Minot"]},
    "terry saar": {"role": "user", "facs": ["Madelia (HOP)", "Minot"]},
    "grant gibbons": {"role": "user", "facs": ["Webster City"]}
}

LOCS = {
    "Madelia (HOP)": {
        "profit_margin": 0.25, "overhead_pct": 0.26, "newsprint_cost_per_lb": 0.35, 
        "black_ink_cost_per_impression": 0.0006, "press_leader_rate": 30.0, 
        "press_helper_rate": 25.0, "camera_plate_rate": 30.0, "make_ready_rate": 30.0, 
        "plate_cost": 5.25, "plate_overhead_maint": 0.75, "color_ink_cost_per_plate_m": 0.95, 
        "mailroom_leader_rate": 30.0, "mailroom_helper_rate": 25.0
    },
    "Minot": {
        "profit_margin": 0.25, "overhead_pct": 0.26, "newsprint_cost_per_lb": 0.35, 
        "black_ink_cost_per_impression": 0.0006, "press_leader_rate": 31.34, 
        "press_helper_rate": 22.43, "camera_plate_rate": 30.0, "make_ready_rate": 31.34, 
        "plate_cost": 5.25, "plate_overhead_maint": 0.75, "color_ink_cost_per_plate_m": 0.95, 
        "mailroom_leader_rate": 24.11, "mailroom_helper_rate": 16.15
    },
    "Webster City": {
        "profit_margin": 0.25, "overhead_pct": 0.26, "newsprint_cost_per_lb": 0.35, 
        "black_ink_cost_per_impression": 0.0006, "press_leader_rate": 38.95, 
        "press_helper_rate": 29.26, "camera_plate_rate": 21.45, "make_ready_rate": 38.95, 
        "plate_cost": 5.25, "plate_overhead_maint": 0.75, "color_ink_cost_per_plate_m": 0.95, 
        "mailroom_leader_rate": 36.63, "mailroom_helper_rate": 20.89
    }
}

def load_inv():
    files = [f for f in os.listdir('.') if 'inventory' in f.lower() and f.endswith('.csv')]
    if not files: 
        return pd.DataFrame(), "No inventory CSV found in folder."
    
    dfs = []
    for target in files:
        try:
            with open(target, 'r', encoding='latin1', errors='replace') as f: 
                data = list(csv.reader(f))
            h_idx = next((i for i, r in enumerate(data) if r and 'Ownership' in str(r[0])), -1)
            if h_idx == -1: 
                continue
            df = pd.DataFrame(data[h_idx+1:], columns=[str(h).strip() for h in data[h_idx]])
            dfs.append(df)
        except: 
            continue

    if not dfs: 
        return pd.DataFrame(), "Could not parse inventory files."
    
    df = pd.concat(dfs, ignore_index=True)
    df.columns = [re.sub(r'[^a-zA-Z0-9_]', '', c) for c in df.columns]

    def find_col(k): 
        return next((c for c in df.columns if k.lower() in c.lower()), None)
    
    p_col = find_col('price')
    n_col = find_col('net')
    w_col = find_col('width')
    g_col = find_col('grammage')

    def ext(v):
        m = re.search(r'[\d\.]+', str(v))
        return float(m.group()) if m and not pd.isna(v) else None

    df['P'] = df[p_col].apply(ext) if p_col else None
    df['Net'] = df[n_col].apply(ext) if n_col else None
    df['W_mm'] = df[w_col].apply(ext) if w_col else None
    df['G'] = df[g_col].apply(ext) if g_col else None

    df['Price_Final'] = df['Net'].apply(lambda x: x if x and x > 0 else None).fillna(df['P'])
    df = df.dropna(subset=['Price_Final','W_mm','G'])

    if df.empty: 
        return df, "No valid prices or widths found."

    df['Price/lb'] = (df['Price_Final']/2204.62).apply(lambda x: round(x+1e-9, 2))
    df['Width'] = (df['W_mm']/25.4).round(1)
    df['Weight'] = (df['G']*0.61386).round(1)
    return df.dropna(subset=['Width','Weight','Price/lb']), "Success"

st.set_page_config(page_title="Bid Tool", layout="wide")

user = st.sidebar.text_input("User Name:").strip().lower()
st.sidebar.button("Unlock")

if not user or user not in AUTH: 
    if user: 
        st.sidebar.error("User not found. Please check spelling.")
    st.stop()

user_data = AUTH[user]
loc = st.sidebar.selectbox("Facility", user_data["facs"])
rates = LOCS[loc]

inv, msg = load_inv()
if inv.empty: 
    st.error(msg)
    st.stop()

st.sidebar.header("Job Specs")
cust = st.sidebar.text_input("Customer", value="Mantako")
job = st.sidebar.text_input("Job Name", value="Free Press")
fmt = st.sidebar.selectbox("Format", ["Broadsheet", "Tabloid", "Book"])
rtype = st.sidebar.selectbox("Run Type", ["Collect", "Straight"])
run = st.sidebar.number_input("Press Run", value=5890, step=100)
waste = st.sidebar.number_input("Waste Copies", value=589, step=50)
t_pgs = st.sidebar.number_input("Total Pages", value=20)
c_pgs = st.sidebar.number_input("Color Pages", value=4)

st.sidebar.header("Paper")
sz = st.sidebar.selectbox("Web Width", sorted(inv['Width'].unique()))
wt = st.sidebar.selectbox("Basis Weight", sorted(inv[inv['Width']==sz]['Weight'].unique()))

filtered_inv = inv[(inv['Width']==sz) & (inv['Weight']==wt)]
p_cost = filtered_inv['Price/lb'].mean() * 1.10

st.sidebar.header("Labor")
cut = st.sidebar.number_input("Press Cut-Off", value=21.25)

raw_cp = st.sidebar.number_input("Pre-Press Plate Hours", value=0.5)
cp = apply_floor(raw_cp)

raw_r_hrs = st.sidebar.number_input("Press Run Hours", value=1.0)
r_hrs = apply_floor(raw_r_hrs)

raw_mr = st.sidebar.number_input("Make-Ready Hours", value=0.5)
mr = apply_floor(raw_mr)

p_ldrs = st.sidebar.number_input("Press Leaders", value=1)
p_hlps = st.sidebar.number_input("Press Helpers", value=2)

st.sidebar.subheader("Mailroom")
ml_ldr = st.sidebar.number_input("Mailroom Leaders", value=1)

raw_ml_lhrs = st.sidebar.number_input("Mailroom Leader Hours", value=0.0)
ml_lhrs = apply_floor(raw_ml_lhrs)

ml_hlp = st.sidebar.number_input("Mailroom Helpers", value=3)

raw_ml_hhrs = st.sidebar.number_input("Mailroom Helper Hours", value=0.0)
ml_hhrs = apply_floor(raw_ml_hhrs)

boat_hen_logo = """
<div style='text-align:center;margin-top:70px;opacity:0.35;'>
    <div style='font-family:Georgia,serif;font-size:34px;'>B <i>&</i> H</div>
    <div style='font-size:9px;letter-spacing:6px;border-top:1px solid #bdc3c7;display:inline-block;'>PRINT WORKS</div>
</div>
"""

if user == "boat hen": 
    st.sidebar.markdown(boat_hen_logo, unsafe_allow_html=True)

# Short-line math blocks to prevent truncation
f_div = 2 if fmt=="Broadsheet" else (4 if fmt=="Tabloid" else 8)
r_mult = 2 if rtype=="Straight" else 1

bw_plates = math.ceil(t_pgs / f_div) * r_mult
color_plates = math.ceil(c_pgs / f_div) * 3 * r_mult
tot_pl = bw_plates + color_plates

total_pages_printed = (run + waste) * t_pgs

tot_lbs = 0
if sz > 0 and cut > 0 and wt > 0:
    yield_factor = 1900000 / (sz * cut * wt)
    tot_lbs = total_pages_printed / yield_factor

c_news = round_cents(tot_lbs * p_cost)
c_ink = round_cents(total_pages_printed * rates["black_ink_cost_per_impression"])

c_color_ink = 0.0
if c_pgs > 0 and run > 0:
    ink_rate = rates["color_ink_cost_per_plate_m"]
    c_color_ink = round_cents(color_plates * (run / 1000) * ink_rate)

labor_press_ldr = p_ldrs * rates["press_leader_rate"] * r_hrs
labor_press_hlp = p_hlps * rates["press_helper_rate"] * r_hrs
labor_mr = mr * rates["make_ready_rate"]
cost_plates = tot_pl * rates["plate_cost"]
cost_plates_maint = tot_pl * rates["plate_overhead_maint"]
labor_camera = cp * rates["camera_plate_rate"]
labor_mail_ldr = ml_ldr * ml_lhrs * rates["mailroom_leader_rate"]
labor_mail_hlp = ml_hlp * ml_hhrs * rates["mailroom_helper_rate"]

c_sub_raw = c_news + c_ink + c_color_ink + labor_press_ldr + labor_press_hlp
c_sub_raw += labor_mr + cost_plates + cost_plates_maint + labor_camera
c_sub_raw += labor_mail_ldr + labor_mail_hlp

c_sub = round_cents(c_sub_raw)
t_cost = round_cents(c_sub * (1.0 + rates["overhead_pct"]))
t_chg = round_cents(t_cost * (1.0 + rates["profit_margin"]))

# Dashboard Rendering
st.header(f"Bid Summary: {cust} - {job}")

labor_calc = c_sub - c_news - c_ink - c_color_ink - cost_plates - cost_plates_maint
ink_plates_calc = c_ink + c_color_ink + cost_plates + cost_plates_maint + labor_camera

c1, c2, c3 = st.columns(3)
c1.metric("Paper", f"${c_news:.2f}")
c2.metric("Labor", f"${labor_calc:.2f}")
c3.metric("Ink/Plates", f"${ink_plates_calc:.2f}")

st.divider()
b1, b2 = st.columns(2)
b1.metric("Total Cost", f"${t_cost:.2f}")
b2.metric("Total Charge", f"${t_chg:.2f}")

st.success(f"Inventory Linked: Web/Wt billed at ${p_cost:.3f}/lb")

st.write("") 
if st.button("Save Quote To Ledger", type="primary", use_container_width=True):
    if cust and job:
        time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        new_quote = {
            "Date": time_str, 
            "User": user.title(), 
            "Customer": cust, 
            "Job": job, 
            "Facility": loc,
            "Total Cost": f"${t_cost:.2f}", 
            "Total Charge": f"${t_chg:.2f}"
        }
        file_exists = os.path.exists("quotes.csv")
        df_new = pd.DataFrame([new_quote])
        df_new.to_csv("quotes.csv", mode='a', header=not file_exists, index=False)
        st.success(f"Quote for {cust} nailed down. Hit refresh on