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
    return df, "Success"

def floor_to_one(val): return max(1.0, float(val))

# --- Main App ---
st.set_page_config(layout="wide")
user = st.sidebar.text_input("User Name:").strip().lower()
if user not in AUTH: st.stop()
user_data = AUTH[user]
loc = st.sidebar.selectbox("Facility", user_data["facs"])
rates = LOCS[loc]

# Logic for Quotes
if not os.path.exists("quotes.csv"):
    pd.DataFrame(columns=["Timestamp", "User", "Customer", "Job", "Charge"]).to_csv("quotes.csv", index=False)

inv, msg = load_inv()
if inv.empty: st.error(msg); st.stop()

# --- Bid Form ---
with st.form("bid_form", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    cust = c1.text_input("Customer")
    job = c2.text_input("Job")
    submit = st.form_submit_button("Save Quote")

    # Paper Selectors (3 slots)
    st.subheader("Paper Selection")
    p1, p2, p3 = st.columns(3)
    # Simplified Paper Selection Logic (assuming common width/wt filtering)
    def get_p_cost(w, wt): return inv[(inv['RollWidth']==w)&(inv['Grammage']==wt)]['NetPricemt'].mean()/2204.62
    
    # ... [Insert calculation logic here, keeping it compact] ...
    
    if submit:
        # Saving Logic
        new_row = {"Timestamp": datetime.datetime.now(), "User": user, "Customer": cust, "Job": job, "Charge": 0.0}
        pd.DataFrame([new_row]).to_csv("quotes.csv", mode='a', header=False, index=False)
        st.success("Quote Saved!")

# --- Viewing Quotes ---
st.header("Quote History")
quotes = pd.read_csv("quotes.csv")
if user_data["role"] == "user":
    quotes = quotes[quotes["User"] == user]
st.dataframe(quotes)