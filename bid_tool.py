import streamlit as st, pandas as pd, math, re, os, csv, datetime

# Configuration
AUTH = {
    "bob patchen": {"role": "admin", "facs": ["Madelia (HOP)", "Minot"]},
    "boat hen": {"role": "admin", "facs": ["Madelia (HOP)", "Minot"]},
    "mike christman": {"role": "admin", "facs": ["Madelia (HOP)", "Minot"]},
    "brenda ahern": {"role": "user", "facs": ["Madelia (HOP)"]},
    "terry saar": {"role": "user", "facs": ["Madelia (HOP)"]}
}

LOCS = {
    "Madelia (HOP)": {"profit_margin":0.25,"overhead_pct":0.26,"newsprint_cost_per_lb":0.35,"black_ink_cost_per_impression":0.0006,"press_leader_rate":30.0,"press_helper_rate":25.0,"camera_plate_rate":30.0,"make_ready_rate":30.0,"plate_cost":5.25,"plate_overhead_maint":0.75,"color_ink_cost_per_plate_m":0.95,"mailroom_leader_rate":30.0,"mailroom_helper_rate":25.0},
    "Minot": {"profit_margin":0.25,"overhead_pct":0.26,"newsprint_cost_per_lb":0.35,"black_ink_cost_per_impression":0.0006,"press_leader_rate":31.34,"press_helper_rate":22.43,"camera_plate_rate":30.0,"make_ready_rate":31.34,"plate_cost":5.25,"plate_overhead_maint":0.75,"color_ink_cost_per_plate_m":0.95,"mailroom_leader_rate":24.11,"mailroom_helper_rate":16.15}
}

def load_inv():
    files = [f for f in os.listdir('.') if 'inventory' in f.lower() and f.endswith('.csv')]
    if not files: return pd.DataFrame(), "No inventory CSV found."
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

def floor_to_one(val): return max(1.0, float(val))

# --- UI ---
st.set_page_config(layout="wide")
user = st.sidebar.text_input("User Name:").strip().lower()
if user not in AUTH: st.stop()
user_data = AUTH[user]
loc = st.sidebar.selectbox("Facility", user_data["facs"])
rates = LOCS[loc]
inv, msg = load_inv()
if inv.empty: st.error(msg); st.stop()

# Sidebar Inputs (The beautiful scroll-down menu)
st.sidebar.header("Job Specs")
cust = st.sidebar.text_input("Customer")
job = st.sidebar.text_input("Job Name")
fmt = st.sidebar.selectbox("Format", ["Broadsheet", "Tabloid", "Book"])
run = st.sidebar.number_input("Press Run", value=5000, step=100)
waste = st.sidebar.number_input("Waste", value=500)
t_pgs = st.sidebar.number_input("Total Pages", value=20)
c_pgs = st.sidebar.number_input("Color Pages", value=4)

st.sidebar.header("Paper")
sz = st.sidebar.selectbox("Web Width", sorted(inv['Width'].unique()))
wt = st.sidebar.selectbox("Basis Weight", sorted(inv[inv['Width']==sz]['Weight'].unique()))
p_cost = inv[(inv['Width']==sz)&(inv['Weight']==wt)]['Price/lb'].mean() * 1.10

st.sidebar.header("Labor")
cut = st.sidebar.number_input("Cut-Off", value=21.25)
r_hrs = floor_to_one(st.sidebar.number_input("Press Run Hours", value=1.0))
mr = floor_to_one(st.sidebar.number_input("Make-Ready Hours", value=1.0))
cp = floor_to_one(st.sidebar.number_input("Plate Hours", value=1.0))
p_ldrs = st.sidebar.number_input("Press Leaders", 1)
p_hlps = st.sidebar.number_input("Press Helpers", 2)

st.sidebar.subheader("Mailroom")
ml_ldr = st.sidebar.number_input("Leaders", 1)
ml_lhrs = floor_to_one(st.sidebar.number_input("Leader Hours", 0.0))
ml_hlp = st.sidebar.number_input("Helpers", 3)
ml_hhrs = floor_to_one(st.sidebar.number_input("Helper Hours", 0.0))

# --- Main Page ---
st.title(f"Bid Summary: {cust} - {job}")
# [Insert your core math logic here to calculate c_news, c_ink, c_sub, etc.]
st.success(f"Paper Rate: ${p_cost:.3f}/lb | Job Loaded.")

if st.button("Save Quote"):
    if not os.path.exists("quotes.csv"):
        pd.DataFrame(columns=["Timestamp", "User", "Customer", "Job"]).to_csv("quotes.csv", index=False)
    pd.DataFrame([{"Timestamp": datetime.datetime.now(), "User": user, "Customer": cust, "Job": job}]).to_csv("quotes.csv", mode='a', header=False, index=False)
    st.balloons()