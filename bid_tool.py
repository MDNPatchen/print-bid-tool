import streamlit as st, pandas as pd, math, re, os, csv

def round_cents(val): return round(val + 1e-9, 2)

def apply_floor(val): 
    v = float(val)
    return 1.0 if 0 < v < 1.0 else v

AUTH = {
    "bob patchen": ["Madelia (HOP)", "Minot", "Webster City"],
    "boat hen": ["Madelia (HOP)", "Minot", "Webster City"],
    "mike christman": ["Madelia (HOP)", "Minot", "Webster City"],
    "brenda ahern": ["Madelia (HOP)", "Minot"],
    "terry saar": ["Madelia (HOP)", "Minot"],
    "grant gibbons": ["Webster City"]
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

user = st.sidebar.text_input("User Name:").strip().lower()
st.sidebar.button("Unlock")

if not user or user not in AUTH: 
    if user: st.sidebar.error("User not found. Please check spelling.")
    st.stop()

facs = AUTH[user]
loc = st.sidebar.selectbox("Facility", facs)
rates = LOCS[loc]

inv