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
    # Sanitization
    def ext(v):
        m = re.search(r'[\d\.]+', str(v))
        return float(m.group()) if m and not pd.isna(v) else None
    
    # Try finding columns dynamically
    p_c = next((c for c in df.columns if 'Price' in c and 'Net' not in c), df.columns[0])
    n_c = next((c for c in df.columns if 'Net' in c), df.columns[0])
    w_c = next((c for c in df.columns if 'Width' in c), df.columns[0])
    g_c = next((c for c in df.columns if 'Grammage' in c), df.columns[0])

    df['P'] = df[p_c].apply(ext)
    df['Net'] = df[n_c].apply(ext)
    df['W_mm'] = df[w_c].apply(ext)
    df['G'] = df[g_c].apply(ext)
    df['P_Final'] = df['Net'].apply(lambda x: x if x and x > 0 else None).fillna(df['P'])
    df['Price/lb'] = (df['P_Final']/2204.62).apply(lambda x: round(x+1e-9, 2))
    df['Width'] = (df['W_mm']/25.4).round(1)
    df['Weight'] = (df['G']*0.61386).round(1)
    return df.dropna(subset=['Width','Weight','Price/lb']), "Success"

# --- UI Setup ---
st.set_page_config(layout="wide")
user = st.sidebar.text_input("User Name:").strip().lower()
if user not in AUTH: st.stop()
user_data = AUTH[user]
loc = st.sidebar.selectbox("Facility", user_data["facs"])
rates = LOCS[loc]
inv, msg = load_inv()

# --- Main Form ---
st.title("Bid Tool")
with st.form("bid_form", clear_on_submit=True):
    # Setup Section
    st.header("1. Job Setup")
    c1, c2, c3, c4 = st.columns(4)
    cust = c1.text_input("Customer")
    job = c2.text_input("Job Name")
    fmt = c3.selectbox("Format", ["Broadsheet", "Tabloid", "Book"])
    run = c4.number_input("Press Run", value=5000, step=100)
    
    # Paper Section
    st.header("2. Paper Selection (3 Slots)")
    p_cols = st.columns(3)
    papers = []
    for i, col in enumerate(p_cols):
        with col:
            st.subheader(f"Paper {i+1}")
            sz = st.selectbox(f"Width {i+1}", sorted(inv['Width'].unique()), key=f"w{i}")
            wt = st.selectbox(f"Basis Wt {i+1}", sorted(inv[inv['Width']==sz]['Weight'].unique()), key=f"wt{i}")
            pct = st.slider(f"Job % {i+1}", 0, 100, 100 if i==0 else 0, key=f"pct{i}")
            papers.append({'cost': inv[(inv['Width']==sz)&(inv['Weight']==wt)]['Price/lb'].mean(), 'pct': pct/100})
            
    # Production Section
    st.header("3. Production Specs")
    cols = st.columns(4)
    cut = cols[0].number_input("Press Cut-Off", value=21.25)
    r_hrs = max(1.0, cols[1].number_input("Press Run Hours", value=1.0))
    mr = max(1.0, cols[2].number_input("Make-Ready Hours", value=1.0))
    cp = max(1.0, cols[3].number_input("Pre-Press Plate Hours", value=1.0))
    
    submit = st.form_submit_button("Save Quote")

    if submit:
        # Weighted paper cost
        avg_p_cost = sum(p['cost'] * p['pct'] for p in papers) * 1.10
        # Placeholder for calc logic (add your full math here)
        st.success(f"Quote Saved for {cust}! Avg Paper Cost: ${avg_p_cost:.3f}/lb")
        
        # Save to CSV
        if not os.path.exists("quotes.csv"):
            pd.DataFrame(columns=["Timestamp", "User", "Customer", "Job"]).to_csv("quotes.csv", index=False)
        pd.DataFrame([{"Timestamp": datetime.datetime.now(), "User": user, "Customer": cust, "Job": job}]).to_csv("quotes.csv", mode='a', header=False, index=False)