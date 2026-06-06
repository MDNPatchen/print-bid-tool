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
    "bob patchen": {
        "role": "admin", 
        "facs": ["Madelia (HOP)", "Minot", "Webster City"]
    },
    "mike christman": {
        "role": "admin", 
        "facs": ["Madelia (HOP)", "Minot", "Webster City"]
    },
    "boat hen": {
        "role": "admin", 
        "facs": ["Madelia (HOP)", "Minot", "Webster City"]
    },
    "brenda ahern": {
        "role": "user", 
        "facs": ["Madelia (HOP)", "Minot"]
    },
    "terry saar": {
        "role": "user", 
        "facs": ["Madelia (HOP)", "Minot"]
    },
    "grant gibbons": {
        "role": "user", 
        "facs": ["Webster City"]
    }
}

LOCS = {
    "Madelia (HOP)": {
        "profit_margin": 0.25, 
        "overhead_pct": 0.26, 
        "newsprint_cost_per_lb": 0.35, 
        "black_ink_cost_per_impression": 0.0006, 
        "press_leader_rate": 30.0, 
        "press_helper_rate": 25.0, 
        "camera_plate_rate": 30.0, 
        "make_ready_rate": 30.0, 
        "plate_cost": 5.25, 
        "plate_overhead_maint": 0.75, 
        "color_ink_cost_per_plate_m": 0.95, 
        "mailroom_leader_rate": 30.0, 
        "mailroom_helper_rate": 25.0
    },
    "Minot": {
        "profit_margin": 0.25, 
        "overhead_pct": 0.26, 
        "newsprint_cost_per_lb": 0.35, 
        "black_ink_cost_per_impression": 0.0006, 
        "press_leader_rate": 31.34, 
        "press_helper_rate": 22.43, 
        "camera_plate_rate": 30.0, 
        "make_ready_rate": 31.34, 
        "plate_cost": 5.25, 
        "plate_overhead_maint": 0.75, 
        "color_ink_cost_per_plate_m": 0.95, 
        "mailroom_leader_rate": 24.11, 
        "mailroom_helper_rate": 16.15
    },
    "Webster City": {
        "profit_margin": 0.25, 
        "overhead_pct": 0.26, 
        "newsprint_cost_per_lb": 0.35, 
        "black_ink_cost_per_impression": 0.0006, 
        "press_leader_rate": 38.95, 
        "press_helper_rate": 29.26, 
        "camera_plate_rate": 21.45, 
        "make_ready_rate": 38.95, 
        "plate_cost": 5.25, 
        "plate_overhead_maint": 0.75, 
        "color_ink_cost_per_plate_m": 0.95, 
        "mailroom_leader_rate": 36.63, 
        "mailroom_helper_rate": 20.89
    }
}

def load_inv():
    all_f = os.listdir('.')
    files = []
    for f in all_f:
        if 'inventory' in f.lower() and f.endswith('.csv'):
            files.append(f)
            
    if not files: 
        return pd.DataFrame(), "No inventory CSV found."
    
    dfs = []
    for target in files:
        try:
            with open(target, 'r', encoding='latin1', errors='replace') as f: 
                data = list(csv.reader(f))
            h_idx = -1
            for i, r in enumerate(data):
                if r and 'Ownership' in str(r[0]):
                    h_idx = i
                    break
            if h_idx == -1: 
                continue
            
            cols = [str(h).strip() for h in data[h_idx]]
            df = pd.DataFrame(data[h_idx+1:], columns=cols)
            dfs.append(df)
        except: 
            continue

    if not dfs: 
        return pd.DataFrame(), "Could not parse inventory files."
    
    df = pd.concat(dfs, ignore_index=True)
    
    def clean_col(c):
        return re.sub(r'[^a-zA-Z0-9_]', '', c)
        
    df.columns = [clean_col(c) for c in df.columns]

    def find_col(k):
        for c in df.columns:
            if k.lower() in c.lower():
                return c
        return None
    
    p_col = find_col('price')
    n_col = find_col('net')
    w_col = find_col('width')
    g_col = find_col('grammage')

    def ext(v):
        m = re.search(r'[\d\.]+', str(v))
        if m and not pd.isna(v):
            return float(m.group())
        return None

    df['P'] = df[p_col].apply(ext) if p_col else None
    df['Net'] = df[n_col].apply(ext) if n_col else None
    df['W_mm'] = df[w_col].apply(ext) if w_col else None
    df['G'] = df[g_col].apply(ext) if g_col else None

    def get_final(row):
        if row['Net'] and row['Net'] > 0:
            return row['Net']
        return row['P']

    df['Price_Final'] = df.apply(get_final, axis=1)
    df = df.dropna(subset=['Price_Final','W_mm','G'])

    if df.empty: 
        return df, "No valid prices or widths."

    def calc_lb(x):
        return round(x + 1e-9, 2)

    df['Price/lb'] = (df['Price_Final']/2204.62).apply(calc_lb)
    df['Width'] = (df['W_mm']/25.4).round(1)
    df['Weight'] = (df['G']*0.61386).round(1)
    
    req_cols = ['Width','Weight','Price/lb']
    return df.dropna(subset=req_cols), "Success"

st.set_page_config(page_title="Bid Tool", layout="wide")

u_in = st.sidebar.text_input("User Name:")
user = u_in.strip().lower()
st.sidebar.button("Unlock")

if not user or user not in AUTH: 
    if user: 
        st.sidebar.error("User not found.")
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

fmt_opts = ["Broadsheet", "Tabloid", "Book"]
fmt = st.sidebar.selectbox("Format", fmt_opts)

rtype_opts = ["Collect", "Straight"]
rtype = st.sidebar.selectbox("Run Type", rtype_opts)

run = st.sidebar.number_input("Press Run", value=5890, step=100)
waste = st.sidebar.number_input("Waste Copies", value=589, step=50)
t_pgs = st.sidebar.number_input("Total Pages", value=20)
c_pgs = st.sidebar.number_input("Color Pages", value=4)

st.sidebar.header("Paper")
w_list = sorted(inv['Width'].unique())
sz = st.sidebar.selectbox("Web Width", w_list)

wt_list = sorted(inv[inv['Width']==sz]['Weight'].unique())
wt = st.sidebar.selectbox("Basis Weight", wt_list)

filtered_inv = inv[(inv['Width']==sz) & (inv['Weight']==wt)]
p_cost = filtered_inv['Price/lb'].mean() * 1.10

st.sidebar.header("Labor")
cut = st.sidebar.number_input("Press Cut-Off", value=21.25)

raw_cp = st.sidebar.number_input("Plate Hrs", value=0.5)
cp = apply_floor(raw_cp)

raw