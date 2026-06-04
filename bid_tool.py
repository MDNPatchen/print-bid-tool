import streamlit as st, pandas as pd, math, re, os, csv

def round_cents(val): return round(val + 1e-9, 2)

# Restored Minot and Madelia logic
AUTH = {
    "bob patchen":["Madelia (HOP)", "Minot"], 
    "boat hen":["Madelia (HOP)", "Minot"], 
    "mike christman":["Madelia (HOP)", "Minot"], 
    "brenda ahern":["Madelia (HOP)", "Minot"], 
    "terry saar":["Madelia (HOP)", "Minot"]
}

LOCS = {
    "Madelia (HOP)": {"profit_margin":0.25,"overhead_pct":0.26,"newsprint_cost_per_lb":0.35,"black_ink_cost_per_impression":0.0006,"press_leader_rate":30.0,"press_helper_rate":25.0,"camera_plate_rate":30.0,"make_ready_rate":30.0,"press_overhead_maint_pct":0.10,"plate_cost":5.25,"plate_overhead_maint":0.75,"color_ink_cost_per_plate_m":0.95,"mailroom_leader_rate":30.0,"mailroom_helper_rate":25.0},
    "Minot": {"profit_margin":0.25,"overhead_pct":0.26,"newsprint_cost_per_lb":0.35,"black_ink_cost_per_impression":0.0006,"press_leader_rate":31.34,"press_helper_rate":22.43,"camera_plate_rate":30.0,"make_ready_rate":31.34,"press_overhead_maint_pct":0.10,"plate_cost":5.25,"plate_overhead_maint":0.75,"color_ink_cost_per_plate_m":0.95,"mailroom_leader_rate":24.11,"mailroom_helper_rate":16.15}
}

def load_inv():
    # Robust loader that finds columns by keywords
    files = [f for f in os.listdir('.') if 'inventory' in f.lower() and f.endswith('.csv')]
    if not files: return pd.DataFrame(), "No inventory CSV found."
    dfs = []
    for f_name in files:
        with open(f_name, 'r', encoding='latin1', errors='replace') as f:
            data = list(csv.reader(f))
            h_idx = next((i for i, r in enumerate(data) if r and 'Ownership' in str(r[0])), -1)
            if h_idx == -1: continue
            df = pd.DataFrame(data[h_idx+1:], columns=[str(h).strip() for h in data[h_idx]])
            dfs.append(df)
    if not dfs: return pd.DataFrame(), "No valid data."
    df = pd.concat(dfs, ignore_index=True)
    
    def find_col(k): return next((c for c in df.columns if k.lower() in c.lower()), None)
    
    def ext(v):
        m = re.search(r'[\d\.]+', str(v))
        return float(m.group()) if m and not pd.isna(v) else None
        
    df['Price'] = df[find_col('Price/mt')].apply(ext)
    df['Net'] = df[find_col('Net Price/mt')].apply(ext)
    df['Width'] = df[find_col('Roll Width')].apply(ext)
    df['Gram'] = df[find_col('Grammage')].apply(ext)
    
    df['P_Final'] = df['Net'].apply(lambda x: x if x and x > 0 else None).fillna(df['Price'])
    df = df.dropna(subset=['P_Final','Width','Gram'])
    df['Price/lb'] = (df['P_Final']/2204.62).apply(lambda x: round(x+1e-9, 2))
    df['W_in'] = (df['Width']/25.4).round(1)
    df['Wt'] = (df['Gram']*0.61386).round(1)
    return df.dropna(subset=['W_in','Wt','Price/lb']), "Success"

st.set_page_config(page_title="Bid Tool", layout="wide")
user = st.sidebar.text_input("User Name:").strip().lower()
st.sidebar.button("Unlock")
if not user or user not in AUTH: st.stop()

loc = st.sidebar.selectbox("Facility", AUTH[user])
rates = LOCS[loc]

inv, msg = load_inv()
if inv.empty: st.error(msg); st.stop()

cust, desc = st.sidebar.text_input("Customer", "Mantako"), st.sidebar.text_input("Job", "Free Press")
run, waste = st.sidebar.number_input("Press Run", 5890, step=100), st.sidebar.number_input("Waste Copies", 589, step=50)
fmt, rtype = st.sidebar.selectbox("Format", ["Broadsheet", "Tabloid", "Book"]), st.sidebar.selectbox("Run Type", ["Collect", "Straight"])
t_pgs, c_pgs = st.sidebar.number_input("Total Pages", 20), st.sidebar.number_input("Color Pages", 4)

sz = st.sidebar.selectbox("Web Width", sorted(inv['W_in'].unique()))
wt = st.sidebar.selectbox("Basis Weight", sorted(inv[inv['W_in']==sz]['Wt'].unique()))
p_cost = round_cents(inv[(inv['W_in']==sz)&(inv['Wt']==wt)]['Price/lb'].mean() * 1.10)
st.sidebar.success(f"Inventory Active: ${p_cost:.3f}/lb")

cut = st.sidebar.number_input("Press Cut-Off", 21.25)
cp, r_hrs, p_ldrs, p_hlps, mr = st.sidebar.number_input("Plate Hrs", 0.5), st.sidebar.number_input("Run Hrs", 1.0), st.sidebar.number_input("Leaders", 1), st.sidebar.number_input("Helpers", 2), st.sidebar.number_input("MR Hrs", 0.5)
ml_ldr, ml_lhrs, ml_hlp, ml_hhrs = st.sidebar.number_input("ML Leaders", 1), st.sidebar.number_input("ML L-Hrs", 0.0), st.sidebar.number_input("ML Helpers", 3), st.sidebar.number_input("ML H-Hrs", 0.0)

if user == "boat hen": st.sidebar.markdown("<div style='text-align:center;margin-top:70px;opacity:0.35;'><div style='font-family:Georgia,serif;font-size:34px;'>B <i>&</i> H</div><div style='font-size:9px;letter-spacing:6px;border-top:1px solid #bdc3c7;display:inline-block;'>PRINT WORKS</div></div>", unsafe_allow_html=True)

f_div = 2 if fmt=="Broadsheet" else (4 if fmt=="Tabloid" else 8)
r_mult = 2 if rtype=="Straight" else 1
tot_pl = (math.ceil(t_pgs/f_div) * r_mult) + (math.ceil(c_pgs/f_div) * 3 * r_mult)
total_pages_printed = (run + waste) * t_pgs
tot_lbs = total_pages_printed / (1900000 / (sz * cut * wt))
c_news = round_cents(tot_lbs * p_cost)
c_ink = round_cents(total_pages_printed * 0.0006)
c_sub = round_cents(c_news + c_ink + (p_ldrs*rates["press_leader_rate"]*r_hrs) + (p_hlps*rates["press_helper_rate"]*r_hrs) + (mr*rates["make_ready_rate"]) + (tot_pl*5.25) + (tot_pl*0.75) + (cp*rates["camera_plate_rate"]) + ((math.ceil(c_pgs/f_div)*3*r_mult)*(run/1000)*0.95) + (ml_ldr*ml_lhrs*rates["mailroom_leader_rate"] + ml_hlp*ml_hhrs*rates["mailroom_helper_rate"]))
t_cost = round_cents(c_sub * 1.26)
t_chg = round_cents(t_cost * 1.25)

st.header(f"Bid Summary: {cust} - {desc}")
c1, c2, c3 = st.columns(3)
c1.metric("Paper", f"${c_news:.2f}"); c2.metric("Labor", f"${(c_sub-c_news-c_ink-(tot_pl*5.25)-(tot_pl*0.75)-((math.ceil(c_pgs/f_div)*3*r_mult)*(run/1000)*0.95)):.2f}"); c3.metric("Ink/Plates", f"${(c_ink+(tot_pl*5.25)+(tot_pl*0.75)+(cp*rates['camera_plate_rate'])+((math.ceil(c_pgs/f_div)*3*r_mult)*(run/1000)*0.95)):.2f}")
st.divider()
b1, b2 = st.columns(2)
b1.metric("Total Cost", f"${t_cost:.2f}"); b2.metric("Total Charge", f"${t_chg:.2f}")