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
        return pd.DataFrame(), "Could not parse inventory."
    
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
    
    pl_col = find_col('plant')
    if not pl_col: 
        pl_col = find_col('location')

    # THE FIX: This aggressively strips out commas so $1,414.26 parses correctly.
    def ext(v):
        v_s = str(v)
        v_c = re.sub(r'[^\d\.]', '', v_s)
        if v_c:
            try:
                return float(v_c)
            except:
                return None
        return None

    df['P'] = df[p_col].apply(ext) if p_col else None
    df['Net'] = df[n_col].apply(ext) if n_col else None
    df['W_mm'] = df[w_col].apply(ext) if w_col else None
    df['G'] = df[g_col].apply(ext) if g_col else None
    
    df['Plant'] = df[pl_col].astype(str) if pl_col else "All"
    df['Plant'] = df['Plant'].fillna("All")

    def get_final(row):
        if row['Net'] and row['Net'] > 0:
            return row['Net']
        return row['P']

    df['P_Fin'] = df.apply(get_final, axis=1)
    df = df.dropna(subset=['P_Fin','W_mm','G'])

    if df.empty: 
        return df, "No valid prices."

    def calc_lb(x):
        return round(x + 1e-9, 2)

    df['Price/lb'] = (df['P_Fin']/2204.62).apply(calc_lb)
    df['Width'] = (df['W_mm']/25.4).round(1)
    df['Weight'] = (df['G']*0.61386).round(1)
    
    req_cols = ['Width','Weight','Price/lb','Plant']
    return df.dropna(subset=['Width','Weight','Price/lb'])[req_cols], "Success"

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

l_str = loc.lower()
is_mad = "madelia" in l_str or "hop" in l_str

def chk_p(x):
    p_val = str(x).lower()
    if is_mad:
        return "madelia" in p_val or "hop" in p_val
    return l_str in p_val or p_val in l_str

mask = inv['Plant'].apply(chk_p)
loc_inv = inv[mask]

active_inv = inv if loc_inv.empty else loc_inv

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
w_list = sorted(active_inv['Width'].unique())
sz = st.sidebar.selectbox("Web Width", w_list)

wt_list = sorted(active_inv[active_inv['Width']==sz]['Weight'].unique())
wt = st.sidebar.selectbox("Basis Weight", wt_list)

filt_inv = active_inv[(active_inv['Width']==sz) & (active_inv['Weight']==wt)]
p_cost = filt_inv['Price/lb'].mean() * 1.10

str_rate = "{:.3f}".format(p_cost)
msg_inv = "Inventory Active: Billed at $" + str_rate + "/lb"
st.sidebar.success(msg_inv)

st.sidebar.header("Labor")
cut = st.sidebar.number_input("Press Cut-Off", value=21.25)

cp_in = st.sidebar.number_input("Pre-Press Plate Hours", value=0.5)
cp = apply_floor(cp_in)

r_in = st.sidebar.number_input("Press Run Hours", value=1.0)
r_hrs = apply_floor(r_in)

mr_in = st.sidebar.number_input("Make-Ready Hours", value=0.5)
mr = apply_floor(mr_in)

p_ldrs = st.sidebar.number_input("Press Leaders", value=1)
p_hlps = st.sidebar.number_input("Press Helpers", value=2)

st.sidebar.subheader("Mailroom")
ml_ldr = st.sidebar.number_input("Mailroom Leaders", value=1)

ml_l_in = st.sidebar.number_input("Mailroom Leader Hours", value=0.0)
ml_lhrs = apply_floor(ml_l_in)

ml_hlp = st.sidebar.number_input("Mailroom Helpers", value=3)

ml_h_in = st.sidebar.number_input("Mailroom Helper Hours", value=0.0)
ml_hhrs = apply_floor(ml_h_in)

f_div = 2 if fmt=="Broadsheet" else (4 if fmt=="Tabloid" else 8)
r_mult = 2 if rtype=="Straight" else 1

bw_pl = math.ceil(t_pgs / f_div) * r_mult
col_pl = math.ceil(c_pgs / f_div) * 3 * r_mult
tot_pl = bw_pl + col_pl

total_pgs = (run + waste) * t_pgs

tot_lbs = 0
if sz > 0 and cut > 0 and wt > 0:
    y_factor = 1900000 / (sz * cut * wt)
    tot_lbs = total_pgs / y_factor

c_news = round_cents(tot_lbs * p_cost)
ink_rate = rates["black_ink_cost_per_impression"]
c_ink = round_cents(total_pgs * ink_rate)

c_col_ink = 0.0
if c_pgs > 0 and run > 0:
    c_rate = rates["color_ink_cost_per_plate_m"]
    c_col_ink = round_cents(col_pl * (run / 1000) * c_rate)

lab_p_ldr = p_ldrs * rates["press_leader_rate"] * r_hrs
lab_p_hlp = p_hlps * rates["press_helper_rate"] * r_hrs
lab_mr = mr * rates["make_ready_rate"]

pl_cost = tot_pl * rates["plate_cost"]
pl_maint = tot_pl * rates["plate_overhead_maint"]

lab_cam = cp * rates["camera_plate_rate"]

lab_m_ldr = ml_ldr * ml_lhrs * rates["mailroom_leader_rate"]
lab_m_hlp = ml_hlp * ml_hhrs * rates["mailroom_helper_rate"]

c_sub_r = c_news + c_ink + c_col_ink + lab_p_ldr + lab_p_hlp
c_sub_r += lab_mr + pl_cost + pl_maint + lab_cam
c_sub_r += lab_m_ldr + lab_m_hlp

c_sub = round_cents(c_sub_r)

cost_mult = 1.0 + rates["overhead_pct"]
t_cost = round_cents(c_sub * cost_mult)

chg_mult = 1.0 + rates["profit_margin"]
t_chg = round_cents(t_cost * chg_mult)

head_txt = "Bid Summary: " + str(cust) + " - " + str(job)
st.header(head_txt)

lab_tot = c_sub - c_news - c_ink - c_col_ink - pl_cost - pl_maint
ink_pl_tot = c_ink + c_col_ink + pl_cost + pl_maint + lab_cam

c1, c2, c3 = st.columns(3)

pap_str = "$" + "{:.2f}".format(c_news)
c1.metric("Paper", pap_str)

lab_str = "$" + "{:.2f}".format(lab_tot)
c2.metric("Labor", lab_str)

ink_str = "$" + "{:.2f}".format(ink_pl_tot)
c3.metric("Ink/Plates", ink_str)

st.divider()
b1, b2 = st.columns(2)

t_c_str = "$" + "{:.2f}".format(t_cost)
b1.metric("Total Cost", t_c_str)

t_ch_str = "$" + "{:.2f}".format(t_chg)
b2.metric("Total Charge", t_ch_str)

st.write("") 
btn_save = st.button("Save Quote", type="primary")

if btn_save:
    if cust and job:
        time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        new_q = {
            "Date": time_str, 
            "User": user.title(), 
            "Customer": cust, 
            "Job": job, 
            "Facility": loc,
            "Total Cost": t_c_str, 
            "Total Charge": t_ch_str
        }
        f_exists = os.path.exists("quotes.csv")
        df_new = pd.DataFrame([new_q])
        df_new.to_csv("quotes.csv", mode='a', header=not f_exists, index=False)
        
        s_msg1 = "Quote for " + str(cust) + " saved. "
        s_msg2 = "Hit refresh to clear the board."
        st.success(s_msg1 + s_msg2)
    else:
        st.error("Need a Customer and Job Name.")

st.divider()
st.subheader("Saved Quotes")
if os.path.exists("quotes.csv"):
    try:
        history = pd.read_csv("quotes.csv")
        if user_data["role"] == "user":
            is_user = history["User"].str.lower() == user.lower()
            history = history[is_user]
        
        if not history.empty:
            st.dataframe(history.iloc[::-1], use_container_width=True)
        else:
            st.info("Your filing cabinet is empty.")
    except:
        st.info("No quotes have been saved yet.")
else:
    st.info("No quotes have been saved in the system yet.")