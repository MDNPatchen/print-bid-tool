import streamlit as st, pandas as pd, math, re, os, csv, datetime

def round_cents(val): return round(val + 1e-9, 2)

AUTH = {
    "bob patchen": ["Madelia (HOP)", "Minot", "Webster City"],
    "boat hen": ["Madelia (HOP)", "Minot", "Webster City"],
    "mike christman": ["Madelia (HOP)", "Minot", "Webster City"],
    "brenda ahern": ["Madelia (HOP)", "Minot"],
    "terry saar": ["Madelia (HOP)", "Minot"],
    "grant gibbons": ["Webster City"]
}

LOCS = {
    "Madelia (HOP)": {"profit_margin":0.25,"overhead_pct":0.26,"newsprint_cost_per_lb":0.35,"black_ink_cost_per_impression":0.0006,"press_leader_rate":30.0,"press_helper_rate":25.0,"camera_plate_rate":30.0,"make_ready_rate":30.0,"press_overhead_maint_pct":0.10,"plate_cost":5.25,"plate_overhead_maint":0.75,"color_ink_cost_per_plate_m":0.95,"mailroom_leader_rate":30.0,"mailroom_helper_rate":25.0},
    "Minot": {"profit_margin":0.25,"overhead_pct":0.26,"newsprint_cost_per_lb":0.35,"black_ink_cost_per_impression":0.0006,"press_leader_rate":31.34,"press_helper_rate":22.43,"camera_plate_rate":30.0,"make_ready_rate":31.34,"press_overhead_maint_pct":0.10,"plate_cost":5.25,"plate_overhead_maint":0.75,"color_ink_cost_per_plate_m":0.95,"mailroom_leader_rate":24.11,"mailroom_helper_rate":16.15},
    "Webster City": {"profit_margin":0.25,"overhead_pct":0.26,"newsprint_cost_per_lb":0.35,"black_ink_cost_per_impression":0.0006,"press_leader_rate":38.95,"press_helper_rate":29.26,"camera_plate_rate":21.45,"make_ready_rate":38.95,"press_overhead_maint_pct":0.16,"plate_cost":5.25,"plate_overhead_maint":0.75,"color_ink_cost_per_plate_m":0.95,"mailroom_leader_rate":36.63,"mailroom_helper_rate":20.89}
}

def load_inv():
    files = [f for f in os.listdir('.') if 'inventory' in f.lower() and f.endswith('.csv')]
    if not files: return pd.DataFrame(), "No inventory CSV found."
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

    if df.empty: return df, "Inventory loaded but could not find valid prices or widths in the data."

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

facs = AUTH[user]
loc = st.sidebar.selectbox("Facility", facs)
rates = LOCS[loc]

inv, msg = load_inv()
if inv.empty:
    st.error(f"Inventory System Offline: {msg}")
    st.stop()

# --- SIDEBAR INPUTS ---
cust = st.sidebar.text_input("Customer", "Mantako")
desc = st.sidebar.text_input("Job", "Free Press")
run = st.sidebar.number_input("Press Run", 5890, step=100)
waste = st.sidebar.number_input("Waste Copies", 589, step=50)
fmt = st.sidebar.selectbox("Format", ["Broadsheet", "Tabloid", "Book"])
rtype = st.sidebar.selectbox("Run Type", ["Collect", "Straight"])
t_pgs = st.sidebar.number_input("Total Pages", 20)
c_pgs = st.sidebar.number_input("Color Pages", 4)

sz = st.sidebar.selectbox("Web Width", sorted(inv['Width'].unique()))
wt = st.sidebar.selectbox("Basis Weight", sorted(inv[inv['Width']==sz]['Weight'].unique()))
p_cost = round_cents(inv[(inv['Width']==sz)&(inv['Weight']==wt)]['Price/lb'].mean() * 1.10)
st.sidebar.success(f"Inventory Active: Billed at ${p_cost:.3f}/lb")

cut = st.sidebar.number_input("Press Cut-Off", 21.25)
cp = st.sidebar.number_input("Pre-Press Plate Hrs", 0.5)
r_hrs = st.sidebar.number_input("Press Run Hrs", 1.0)
p_ldrs = st.sidebar.number_input("Press Leaders", 1)
p_hlps = st.sidebar.number_input("Press Helpers", 2)
mr = st.sidebar.number_input("Make-Ready Hrs", 0.5)

ml_ldr = st.sidebar.number_input("Mailroom Leaders", 1)
ml_lhrs = st.sidebar.number_input("Mailroom L-Hrs", 0.0)
ml_hlp = st.sidebar.number_input("Mailroom Helpers", 3)
ml_hhrs = st.sidebar.number_input("Mailroom H-Hrs", 0.0)

# The 1-Hour Safety Floor Logic
cp = max(1.0, float(cp)) if cp > 0 else cp
r_hrs = max(1.0, float(r_hrs)) if r_hrs > 0 else r_hrs
mr = max(1.0, float(mr)) if mr > 0 else mr
ml_lhrs = max(1.0, float(ml_lhrs)) if ml_lhrs > 0 else ml_lhrs
ml_hhrs = max(1.0, float(ml_hhrs)) if ml_hhrs > 0 else ml_hhrs

if user == "boat hen": st.sidebar.markdown("<div style='text-align:center;margin-top:70px;opacity:0.35;'><div style='font-family:Georgia,serif;font-size:34px;'>B <i>&</i> H</div><div style='font-size:9px;letter-spacing:6px;border-top:1px solid #bdc3c7;display:inline-block;'>PRINT WORKS</div></div>", unsafe_allow_html=True)

# --- MATH ENGINE ---
f_div = 2 if fmt=="Broadsheet" else (4 if fmt=="Tabloid" else 8)
r_mult = 2 if rtype=="Straight" else 1
tot_pl = (math.ceil(t_pgs/f_div) * r_mult) + (math.ceil(c_pgs/f_div) * 3 * r_mult)
total_pages_printed = (run + waste) * t_pgs
tot_lbs = total_pages_printed / (1900000 / (sz * cut * wt))

c_news = round_cents(tot_lbs * p_cost)
c_ink = round_cents(total_pages_printed * rates["black_ink_cost_per_impression"])
c_color_ink = round_cents(((math.ceil(c_pgs/f_div)*3*r_mult)*(run/1000)*rates["color_ink_cost_per_plate_m"])) if c_pgs > 0 and run > 0 else 0

c_sub = round_cents(
    c_news + c_ink + c_color_ink +
    (p_ldrs * rates["press_leader_rate"] * r_hrs) + 
    (p_hlps * rates["press_helper_rate"] * r_hrs) + 
    (mr * rates["make_ready_rate"]) + 
    (tot_pl * rates["plate_cost"]) + 
    (tot_pl * rates["plate_overhead_maint"]) + 
    (cp * rates["camera_plate_rate"]) + 
    (ml_ldr * ml_lhrs * rates["mailroom_leader_rate"]) + 
    (ml_hlp * ml_hhrs * rates["mailroom_helper_rate"])
)

t_cost = round_cents(c_sub * (1.0 + rates["overhead_pct"]))
t_chg = round_cents(t_cost * (1.0 + rates["profit_margin"]))

# --- MAIN DASHBOARD ---
st.header(f"Bid Summary: {cust} - {desc}")
c1, c2, c3 = st.columns(3)
c1.metric("Paper", f"${c_news:.2f}")
c2.metric("Labor", f"${(c_sub - c_news - c_ink - c_color_ink - (tot_pl * rates['plate_cost']) - (tot_pl * rates['plate_overhead_maint'])):.2f}")
c3.metric("Ink/Plates", f"${(c_ink + c_color_ink + (tot_pl * rates['plate_cost']) + (tot_pl * rates['plate_overhead_maint']) + (cp * rates['camera_plate_rate'])):.2f}")

st.divider()
b1, b2 = st.columns(2)
b1.metric("Total Cost", f"${t_cost:.2f}")
b2.metric("Total Charge", f"${t_chg:.2f}")

# --- QUOTE LEDGER ---
st.divider()
if st.button("Save Quote To Ledger"):
    new_q = {
        "Date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "User": user.title(),
        "Customer": cust,
        "Job": desc,
        "Facility": loc,
        "Total Cost": f"${t_cost:.2f}",
        "Total Charge": f"${t_chg:.2f}"
    }
    f_exists = os.path.isfile("quotes.csv")
    pd.DataFrame([new_q]).to_csv("quotes.csv", mode='a', header=not f_exists, index=False)
    st.success(f"Quote for {cust} nailed down. Hit refresh on your browser when you want to clear the deck for the next run.")

st.subheader("Saved Quotes")
if os.path.exists("quotes.csv"):
    try:
        history = pd.read_csv("quotes.csv")
        # Bouncer Logic: Admins see the whole cabinet. Users just see their own folder.
        if user not in ["bob patchen", "mike christman", "boat hen"]:
            history = history[history["User"].str.lower() == user]
            
        if not history.empty:
            st.dataframe(history.iloc[::-1], use_container_width=True)
        else:
            st.info("Your filing cabinet is empty.")
    except Exception as e:
        pass