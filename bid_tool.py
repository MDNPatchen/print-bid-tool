import streamlit as st, pandas as pd, math, re, os, csv, datetime

def round_cents(val): return round(val + 1e-9, 2)

# Logic: 0 stays 0. Anything between 0.01 and 0.99 gets floored to 1.0. 1.0+ stays as is.
def apply_floor(val): 
    v = float(val)
    return 1.0 if 0 < v < 1.0 else v

AUTH = {
    "bob patchen": {"role": "admin", "facs": ["Madelia (HOP)", "Minot", "Webster City"]},
    "boat hen": {"role": "admin", "facs": ["Madelia (HOP)", "Minot", "Webster City"]},
    "mike christman": {"role": "admin", "facs": ["Madelia (HOP)", "Minot", "Webster City"]},
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

# --- 1. TRUE SESSION LOGIN TO PREVENT HANG-UPS ---
if 'auth_user' not in st.session_state:
    st.session_state.auth_user = None

if st.session_state.auth_user is None:
    st.sidebar.header("System Login")
    u_in = st.sidebar.text_input("User Name:").strip().lower()
    if st.sidebar.button("Unlock"):
        if u_in in AUTH:
            st.session_state.auth_user = u_in
            st.rerun()
        else:
            st.sidebar.error("User not found. Please check spelling.")
    st.stop()

# Load User Context securely
user_input = st.session_state.auth_user
user_data = AUTH[user_input]

# --- 2. HARD RESET LOGIC FOR NEW BID ---
def start_new_bid():
    # Force memory state back to strict defaults
    st.session_state.cust = ""
    st.session_state.job = ""
    st.session_state.fmt = "Broadsheet"
    st.session_state.rtype = "Collect"
    st.session_state.run = 0
    st.session_state.waste = 0
    st.session_state.t_pgs = 0
    st.session_state.c_pgs = 0
    st.session_state.cut = 21.25
    st.session_state.cp = 0.0
    st.session_state.r_hrs = 0.0
    st.session_state.mr = 0.0
    st.session_state.p_ldrs = 0
    st.session_state.p_hlps = 0
    st.session_state.ml_ldr = 0
    st.session_state.ml_lhrs = 0.0
    st.session_state.ml_hlp = 0
    st.session_state.ml_hhrs = 0.0

c1_side, c2_side = st.sidebar.columns(2)
c1_side.button("Start New Bid", on_click=start_new_bid, type="primary")
if c2_side.button("Lock / Logout"):
    st.session_state.auth_user = None
    st.rerun()

st.sidebar.divider()

loc = st.sidebar.selectbox("Facility", user_data["facs"])
rates = LOCS[loc]

inv, msg = load_inv()
if inv.empty: 
    st.error(msg)
    st.stop()

# --- 3. SIDEBAR INPUTS (Tied to Session State Keys) ---
st.sidebar.header("Job Specs")
cust = st.sidebar.text_input("Customer", key="cust")
job = st.sidebar.text_input("Job Name", key="job")

# Safeguards to initialize session state properly if they don't exist yet
if 'fmt' not in st.session_state: st.session_state.fmt = "Broadsheet"
if 'rtype' not in st.session_state: st.session_state.rtype = "Collect"

fmt = st.sidebar.selectbox("Format", ["Broadsheet", "Tabloid", "Book"], key="fmt")
rtype = st.sidebar.selectbox("Run Type", ["Collect", "Straight"], key="rtype")
run = st.sidebar.number_input("Press Run", step=100, key="run")
waste = st.sidebar.number_input("Waste Copies", step=50, key="waste")
t_pgs = st.sidebar.number_input("Total Pages", key="t_pgs")
c_pgs = st.sidebar.number_input("Color Pages", key="c_pgs")

st.sidebar.header("Paper")
sz = st.sidebar.selectbox("Web Width", sorted(inv['Width'].unique()), key="sz")
wt = st.sidebar.selectbox("Basis Weight", sorted(inv[inv['Width']==sz]['Weight'].unique()), key="wt")
p_cost = inv[(inv['Width']==sz)&(inv['Weight']==wt)]['Price/lb'].mean() * 1.10

st.sidebar.header("Labor")
if 'cut' not in st.session_state: st.session_state.cut = 21.25
cut = st.sidebar.number_input("Press Cut-Off", key="cut")

cp = apply_floor(st.sidebar.number_input("Pre-Press Plate Hours", key="cp"))
r_hrs = apply_floor(st.sidebar.number_input("Press Run Hours", key="r_hrs"))
mr = apply_floor(st.sidebar.number_input("Make-Ready Hours", key="mr"))
p_ldrs = st.sidebar.number_input("Press Leaders", key="p_ldrs")
p_hlps = st.sidebar.number_input("Press Helpers", key="p_hlps")

st.sidebar.subheader("Mailroom")
ml_ldr = st.sidebar.number_input("Mailroom Leaders", key="ml_ldr")
ml_lhrs = apply_floor(st.sidebar.number_input("Mailroom Leader Hours", key="ml_lhrs"))
ml_hlp = st.sidebar.number_input("Mailroom Helpers", key="ml_hlp")
ml_hhrs = apply_floor(st.sidebar.number_input("Mailroom Helper Hours", key="ml_hhrs"))

if user_input == "boat hen": 
    st.sidebar.markdown("<div style='text-align:center;margin-top:70px;opacity:0.35;'><div style='font-family:Georgia,serif;font-size:34px;'>B <i>&</i> H</div><div style='font-size:9px;letter-spacing:6px;border-top:1px solid #bdc3c7;display:inline-block;'>PRINT WORKS</div></div>", unsafe_allow_html=True)

# --- Math Engine ---
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

# --- Dashboard Display ---
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

# --- Save & View Logic ---
st.divider()
if st.button("Save Quote"):
    if not cust or not job:
        st.error("Please enter a Customer and Job Name in the sidebar to save this quote.")
    else:
        new_q = {
            "Date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "User": user_input.title(),
            "Customer": cust,
            "Job": job,
            "Facility": loc,
            "Total Cost": f"${t_cost:.2f}",
            "Total Charge": f"${t_chg:.2f}"
        }
        f_exists = os.path.isfile("quotes.csv")
        pd.DataFrame([new_q]).to_csv("quotes.csv", mode='a', header=not f_exists, index=False)
        st.success(f"Quote for {cust} saved successfully! Click 'Start New Bid' in the sidebar to clear the board.")

st.subheader("Saved Quotes")
if os.path.exists("quotes.csv"):
    q_df = pd.read_csv("quotes.csv")
    if user_data["role"] == "user":
        # Regular users only see their own work
        q_df = q_df[q_df["User"].str.lower() == user_input.lower()]
    
    if not q_df.empty:
        st.dataframe(q_df.iloc[::-1], use_container_width=True) # Reverses order so newest is at the top
    else:
        st.info("No saved quotes found for your account.")
else:
    st.info("No quotes have been saved in the system yet.")