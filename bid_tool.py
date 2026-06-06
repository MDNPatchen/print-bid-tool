import streamlit as st, pandas as pd, math, re, os, csv, datetime

def round_cents(val): return round(val + 1e-9, 2)

def apply_floor(val): 
    v = float(val)
    return 1.0 if 0 < v < 1.0 else v

AUTH = {
    "bob patchen": {"role": "admin", "facs": ["Madelia (HOP)", "Minot", "Webster City"]},
    "mike christman": {"role": "admin", "facs": ["Madelia (HOP)", "Minot", "Webster City"]},
    "boat hen": {"role": "admin", "facs": ["Madelia (HOP)", "Minot", "Webster City"]},
    "brenda ahern": {"role": "user", "facs": ["Madelia (HOP)", "Minot"]},
    "terry saar": {"role": "user", "facs": ["Madelia (HOP)", "Minot"]},
    "grant gibbons": {"role": "user", "facs": ["Webster City"]}
}

LOCS = {
    "Madelia (HOP)": {"profit_margin":0.25,"overhead_pct":0.26,"newsprint_cost_per_lb":0.35,"black_ink_cost_per_impression":0.0006,"press_leader_rate":30.0,"press_helper_rate":25.0,"camera_plate_rate":30.0,"make_ready_rate":30.0,"plate_cost":5.25,"plate_overhead_maint":0.75,"color_ink_cost_per_plate_m":0.95,"mailroom_leader_rate":30.0,"mailroom_helper_rate":25.0},
    "Minot": {"profit_margin":0.25,"overhead_pct":0.26,"newsprint_cost_per_lb":0.35,"black_ink_cost_per_impression":0.0006,"press_leader_rate":31.34,"press_helper_rate":22.43,"camera_plate_rate":30.0,"make_ready_rate":31.34,"plate_cost":5.25,"plate_overhead_maint":0.75,"color_ink_cost_per_plate_m":0.95,"mailroom_leader_rate":24.11,"mailroom_helper_rate":16.15},
    "Webster City": {"profit_margin":0.25,"overhead_pct":0.26,"newsprint_cost_per_lb":0.35,"black_ink_cost_per_impression":0.0006,"press_leader_rate":38.95,"press_helper_rate":29.26,"camera_plate_rate":21.45,"make_ready_rate":38.95,"plate_cost":5.25,"plate_overhead_maint":0.75,"color_ink_cost_per_plate_m":0.95,"mailroom_leader_rate":36.63,"mailroom_helper_rate":20.89}
}

def load_inv():
    files = [f for f in os.listdir('.') if 'inventory' in f.lower() and f.endswith('.csv')]
    if not files: return pd.DataFrame(), "No inventory CSV found in folder."
    
    dfs = []
    for target in files:
        try:
            with open(target, 'r', encoding='latin1', errors='replace') as f: data = list(csv.reader(f))
            h_idx = next((i for i, r in enumerate(data) if r and 'Ownership' in str(r[0])), -1)
            if h_idx == -1: continue
            df = pd.DataFrame(data[h_idx+1:], columns=[str(h).strip() for h in data[h_idx]])
            dfs.append(df)
        except: continue

    if not dfs: return pd.DataFrame(), "Could not parse inventory files. Check your CSV headers."
    df = pd.concat(dfs, ignore_index=True)
    df.columns = [re.sub(r'[^a-zA-Z0-9_]', '', c) for c in df.columns]

    def find_col(k): return next((c for c in df.columns if k.lower() in c.lower()), None)
    p_col, n_col = find_col('price'), find_col('net')
    w_col, g_col = find_col('width'), find_col('grammage')

    def ext(v):
        m = re.search(r'[\d\.]+', str(v))
        return float(m.group()) if m and not pd.isna(v) else None

    df['P'] = df[p_col].apply(ext) if p_col else None
    df['Net'] = df[n_col].apply(ext) if n_col else None
    df['W_mm'] = df[w_col].apply(ext) if w_col else None
    df['G'] = df[g_col].apply(ext) if g_col else None

    df['Price_Final'] = df['Net'].apply(lambda x: x if x and x > 0 else None).fillna(df['P'])
    df = df.dropna(subset=['Price_Final','W_mm','G'])

    if df.empty: return df, "Inventory loaded but could not find valid prices or widths."

    df['Price/lb'] = (df['Price_Final']/2204.62).apply(lambda x: round(x+1e-9, 2))
    df['Width'] = (df['W_mm']/25.4).round(1)
    df['Weight'] = (df['G']*0.61386).round(1)
    return df.dropna(subset=['Width','Weight','Price/lb']), "Success"

st.set_page_config(page_title="Bid Tool", layout="wide")

user = st.sidebar.text_input("User Name:").strip().lower()
st.sidebar.button("Unlock")

if not user or user not in AUTH: 
    if user: st.sidebar.error("User not found. Please check spelling.")
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
p_cost = inv[(inv['Width']==sz)&(inv['Weight']==wt)]['Price/lb'].mean() * 1.10

st.sidebar.header("Labor")
cut = st.sidebar.number_input("Press Cut-Off", value=21.25)
cp = apply_floor(st.sidebar.number_input("Pre-Press Plate Hours", value=0.5))
r_hrs = apply_floor(st.sidebar.number_input("Press Run Hours", value=1.0))
mr = apply_floor(st.sidebar.number_input("Make-Ready Hours", value=0.5))
p_ldrs = st.sidebar.number_input("Press Leaders", value=1)
p_hlps = st.sidebar.number_input("Press Helpers", value=2)

st.sidebar.subheader("Mailroom")
ml_ldr = st.sidebar.number_input("Mailroom Leaders", value=1)
ml_lhrs = apply_floor(st.sidebar.number_input("Mailroom Leader Hours", value=0.0))
ml_hlp = st.sidebar.number_input("Mailroom Helpers", value=3)
ml_hhrs = apply_floor(st.sidebar.number_input("Mailroom Helper Hours", value=0.0))

if user == "boat hen": 
    st.sidebar.markdown("<div