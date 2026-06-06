import streamlit as st, pandas as pd, math, re, os, csv, datetime

def round_cents(val): return round(val + 1e-9, 2)

# Floor logic: If they leave it at 0, it stays 0. If it's 0.1 to 0.99, it bumps to 1.0.
def apply_floor(val): 
    v = float(val)
    return 1.0 if 0 < v < 1.0 else v

# Dictionary with RBAC (Role-Based Access Control)
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
    dfs = [pd.read_csv(f, encoding='latin1') for f in files]
    df = pd.concat(dfs, ignore_index=True)
    df.columns = [re.sub(r'[^a-zA-Z0-9_]', '', c) for c in df.columns]
    
    def ext(v):
        m = re.search(r'[\d\.]+', str(v))
        return float(m.group()) if m and not pd.isna(v) else None
    
    p_c = next((c for c in df.columns if 'Price' in c and 'Net' not in c), df.columns[0])
    n_c = next((c for c in df.columns if 'Net' in c), df.columns[0])
    w_c = next((c for c in df.columns if 'Width' in c), df.columns[0])
    g_c = next((c for c in df.columns if 'Grammage' in c), df.columns[0])

    df['P'] = df[p_c].apply(ext); df['Net'] = df[n_c].apply(ext); df['W_mm'] = df[w_c].apply(ext); df['G'] = df[g_c].apply(ext)
    df['P_Final'] = df['Net'].apply(lambda x: x if x and x > 0 else None).fillna(df['P'])
    df['Price/lb'] = (df['P_Final']/2204.62).apply(lambda x: round(x+1e-9, 2))
    df['Width'] = (df['W_mm']/25.4).round(1); df['Weight'] = (df['G']*0.61386).round(1)
    return df.dropna(subset=['Width','Weight','Price/lb']), "Success"

st.set_page_config(page_title="Bid Tool", layout="wide")

# --- ORIGINAL, STABLE LOGIN ---
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

# --- SIDEBAR INPUTS ---
st.sidebar.header("Job Specs")
cust = st.sidebar.text_input("Customer", value="")
job = st.sidebar.text_input("Job Name", value="")
fmt = st.sidebar.selectbox("Format", ["Broadsheet", "Tabloid", "Book"])
rtype = st.sidebar.selectbox("Run Type", ["Collect", "Straight"])
run = st.sidebar.number_input("Press Run", value=0, step=100)
waste = st.sidebar.number_input("Waste Copies", value=0, step=50)
t_pgs = st.sidebar.number_input("Total Pages", value=0)
c_pgs = st.sidebar.number_input("Color Pages", value=0)

st.sidebar.header("Paper")
sz = st.sidebar.selectbox("Web Width", sorted(inv['Width'].unique()))
wt = st.sidebar.selectbox("Basis Weight", sorted(inv[inv['Width']==sz]['Weight'].unique()))
p_cost = inv[(inv['Width']==sz)&(inv['Weight']==wt)]['Price/lb'].mean() * 1.10

st.sidebar.header("Labor")
cut = st.sidebar.number_input("Press Cut-Off", value=21.25)
cp = apply_floor(st.sidebar.number_input("Pre-Press Plate Hours", value=0.0))
r_hrs = apply_floor(st.sidebar.number_input("Press Run Hours", value=0.0))
mr = apply_floor(st.sidebar.number_input("Make-Ready Hours", value=0.0))
p_ldrs = st.sidebar.number_input("Press Leaders", value=0)
p_hlps = st.sidebar.number_input("Press Helpers", value=0)

st.sidebar.subheader("Mailroom")
ml_ldr = st.sidebar.number_input("Mailroom Leaders", value=0)
ml_lhrs = apply_floor(st.sidebar.number_input("Mailroom Leader Hours", value=0.0))
ml_hlp = st.sidebar.number_input("Mailroom Helpers", value=0)
ml_hhrs = apply_floor(st.sidebar.number_input("Mailroom Helper Hours", value=0.0))

if user == "boat hen": 
    st.sidebar.markdown("<div style='text-align:center;margin-top:70px;opacity:0.35;'><div style='font-family:Georgia,serif;font-size:34px;'>B <i>&</i> H</div><div style='font-size:9px;letter-spacing:6px;border-top:1px solid #bdc3c7;display:inline-block;'>PRINT WORKS</div></div>", unsafe_allow_html=True)

# --- MATH ENGINE ---
f_div = 2 if fmt=="Broadsheet" else (4 if fmt=="Tabloid" else 8)
r_mult = 2 if rtype=="Straight" else 1

tot_pl = 0
total_pages_printed = 0
tot_lbs = 0

if t_pgs > 0 and (run + waste) > 0:
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

# --- DASHBOARD ---
if cust == "" and job == "":
    st.header("Bid Summary: New Job")
else:
    st.header(f"Bid Summary: {cust} - {job}")

c1, c2, c3 = st.columns(3)
c1.metric("Paper", f"${c_news:.2f}")
c2.metric("Labor", f"${(c_sub - c_news - c_ink - c_color_ink - (tot_pl * rates['plate_cost']) - (tot_pl * rates['plate_overhead_maint'])):.2f}")
c3.metric("Ink/Plates", f"${(c_ink + c_color_ink + (tot_pl * rates['plate_cost']) + (tot_pl * rates['plate_overhead_maint']) + (cp * rates['camera_plate_rate'])):.2f}")

st.divider()
b1, b2 = st.columns(2)
b1.metric("Total Cost", f"${t_cost:.2f}")
b2.metric("Total Charge", f"${t_chg:.2f}")

st.success(f"Inventory Linked: Web/Wt billed at ${p_cost:.3f}/lb")

# --- SAVE QUOTE TO LEDGER ---
st.divider()
if st.button("Save Quote To Ledger"):
    if cust and job:
        new_quote = {
            "Date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 
            "User": user.title(), 
            "Customer": cust, 
            "Job": job, 
            "Facility": loc,
            "Total Cost": f"${t_cost:.2f}", 
            "Total Charge": f"${t_chg:.2f}"
        }
        file_exists = os.path.exists("quotes.csv")
        pd.DataFrame([new_quote]).to_csv("quotes.csv", mode='a', header=not file_exists, index=False)
        st.success(f"Quote for {cust} nailed down. Just hit refresh (F5 or CMD+R) on your browser to clear the board for the next job.")
    else:
        st.error("Need a Customer and Job Name to save.")

st.subheader("Saved Quotes")
if os.path.exists("quotes.csv"):
    try:
        history = pd.read_csv("quotes.csv")
        # Bouncer logic: Admins see all, Users see their own
        if user_data["role"] == "user":
            history = history[history["User"].str.lower() == user.lower()]
        
        if not history.empty:
            st.dataframe(history.iloc[::-1], use_container_width=True) # Flipped so newest is on top
        else:
            st.info("Your filing cabinet is empty.")
    except Exception as e:
        st.info("No quotes have been saved yet.")
else:
    st.info("No quotes have been saved in the system yet.")