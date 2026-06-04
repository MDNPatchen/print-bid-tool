import streamlit as st, pandas as pd, math, re, os, csv

def round_cents(val): return round(val + 1e-9, 2)

AUTH = {"bob patchen":["Minot","Madelia (HOP)"], "boat hen":["Minot","Madelia (HOP)"], "mike christman":["Minot","Madelia (HOP)"], "brenda ahern":["Madelia (HOP)"], "terry saar":["Madelia (HOP)"]}

LOCS = {
    "Madelia (HOP)": {"profit_margin":0.25,"overhead_pct":0.26,"newsprint_cost_per_lb":0.35,"waste_pct":0.10,"black_ink_cost_per_impression":0.0006,"press_leader_rate":30.0,"press_helper_rate":25.0,"camera_plate_rate":30.0,"make_ready_rate":30.0,"press_overhead_maint_pct":0.10,"plate_cost":5.25,"plate_overhead_maint":0.75,"color_ink_cost_per_plate_m":0.95,"mailroom_leader_rate":30.0,"mailroom_helper_rate":25.0},
    "Minot": {"profit_margin":0.25,"overhead_pct":0.26,"newsprint_cost_per_lb":0.35,"waste_pct":0.10,"black_ink_cost_per_impression":0.0006,"press_leader_rate":31.34,"press_helper_rate":22.43,"camera_plate_rate":30.0,"make_ready_rate":31.34,"press_overhead_maint_pct":0.10,"plate_cost":5.25,"plate_overhead_maint":0.75,"color_ink_cost_per_plate_m":0.95,"mailroom_leader_rate":24.11,"mailroom_helper_rate":16.15}
}

def load_inv(loc):
    base = loc.split(" ")[0].lower()
    target = next((f for f in os.listdir('.') if base in f.lower() and f.endswith('.csv')), None)
    if not target: return pd.DataFrame(), f"No CSV for {base}"
    try:
        with open(target, 'r', encoding='latin1', errors='replace') as f: data = list(csv.reader(f))
        h_idx = next((i for i, r in enumerate(data) if r and 'Ownership' in str(r[0])), -1)
        if h_idx == -1: return pd.DataFrame(), "No Ownership header row."
        df = pd.DataFrame(data[h_idx+1:], columns=[str(h).strip() for h in data[h_idx]])
        cmap = {}
        for c in df.columns:
            cl = str(c).lower()
            if 'grammage' in cl and 'T_Gram' not in cmap.values(): cmap[c] = 'T_Gram'
            elif 'width' in cl and 'T_Wid' not in cmap.values(): cmap[c] = 'T_Wid'
            elif ('price/mt' in cl or 'price / mt' in cl) and 'net' not in cl and 'T_Pri' not in cmap.values(): cmap[c] = 'T_Pri'
        df = df.rename(columns=cmap)
        if not all(x in df.columns for x in ['T_Pri','T_Gram','T_Wid']): return pd.DataFrame(), "Couldn't identify required target columns."
        def ext(val):
            m = re.search(r'[\d\.]+', str(val))
            return float(m.group()) if m and not pd.isna(val) else None
        df['P_Num'] = df['T_Pri'].apply(ext)
        df['W_Num'] = df['T_Wid'].apply(ext)
        df['G_Num'] = df['T_Gram'].apply(ext)
        df = df.dropna(subset=['P_Num','W_Num','G_Num'])
        df['Price/lb'] = (df['P_Num']/2204.62).apply(lambda x: round(x+1e-9, 2))
        df['Paper Size (Inches)'] = (df['W_Num']/25.4).round(1)
        df['Paper Weight (#)'] = (df['G_Num']*0.61386).round(1)
        df = df.dropna(subset=['Paper Size (Inches)','Paper Weight (#)','Price/lb'])
        return df, "Success" if not df.empty else "No valid numeric data remained."
    except Exception as e: return pd.DataFrame(), str(e)

st.set_page_config(page_title="Print Production Bid Tool", layout="wide")
st.title("📰 Newspaper Job Bid Worksheet")

st.sidebar.header("System Access")
user = st.sidebar.text_input("Enter User Name:").strip().lower()
st.sidebar.button("Unlock Dashboard")
if not user:
    st.info("👋 Welcome! Please type your name in the sidebar and click the **Unlock Dashboard** button.")
    st.stop()
if user not in AUTH:
    st.error("❌ Name not recognized by the system. Check your spelling.")
    st.stop()
st.sidebar.success("🔓 Access Granted")

st.sidebar.header("Job Specs & Location")
loc = st.sidebar.selectbox("Select Production Facility", AUTH[user])
rates = LOCS[loc]

cust = st.sidebar.text_input("Customer", "Mantako")
desc = st.sidebar.text_input("Job Description", "Free Press")
run = st.sidebar.number_input("Press Run", 5890, step=100)
waste = st.sidebar.number_input("Waste Copies", 589, step=50)
wpct = (waste/run)*100 if run>0 else 100.0
st.sidebar.info(f"**Calculated Waste:** {wpct:.1f}% of press run")

st.sidebar.subheader("Format & Pagination")
fmt = st.sidebar.selectbox("Page Format", ["Broadsheet", "Tabloid", "Book"])
rtype = st.sidebar.selectbox("Run Type", ["Collect", "Straight"])
t_pages = st.sidebar.number_input("Total Pages", 20)
c_pages = st.sidebar.number_input("Color Pages", 4)

st.sidebar.subheader("Web Specifications & Paper Stock")
inv_df, msg = load_inv(loc)
inv_ok = False
p_cost = 0.0
w_in = 22.0
b_wt = 27.7

if not inv_df.empty:
    sizes = sorted(inv_df['Paper Size (Inches)'].unique().tolist())
    if sizes:
        inv_ok = True
        sz = st.sidebar.selectbox("Paper Size (Web Width in inches)", sizes)
        f_sz = inv_df[inv_df['Paper Size (Inches)']==sz]
        wts = sorted(f_sz['Paper Weight (#)'].unique().tolist())
        if wts:
            wt = st.sidebar.selectbox("Paper Weight (Basis lbs)", wts)
            avg_p = f_sz[f_sz['Paper Weight (#)']==wt]['Price/lb'].mean()
            p_cost = round_cents(avg_p * 1.10)
            w_in = sz
            b_wt = wt
            st.sidebar.success(f"Inventory Link Active: Billed at ${p_cost:.3f}/lb")
        else: inv_ok = False
    else: inv_ok = False

if not inv_ok:
    st.sidebar.warning(f"Using manual inputs. Diagnostic: {msg}")
    w_in = st.sidebar.number_input("Web Width (inches)", 22.0)
    b_wt = st.sidebar.number_input("Basis Weight (lbs)", 27.7)
    p_cost = round_cents(rates["newsprint_cost_per_lb"] * 1.10)
    st.sidebar.info(f"Manual Rate: Billed at ${p_cost:.3f}/lb")

cut = st.sidebar.number_input("Press Cut-Off", 21.25)

st.sidebar.header("Pre-Press & Press Room")
cp_hrs = st.sidebar.number_input("Camera/Plate hours", 0.5)
r_hrs = st.sidebar.number_input("Time for run (hours)", 1.0)
p_ldrs = st.sidebar.number_input("Number of press leaders", 1)
p_hlps = st.sidebar.number_input("Number of press helpers", 2)
mr_hrs = st.sidebar.number_input("Make-ready/clean-up hours", 0.5)

st.sidebar.header("Mailroom")
m_ldrs = st.sidebar.number_input("Mailroom Leaders", 1)
ml_hrs = st.sidebar.number_input("Mailroom Leader Hours", 3.0)
m_hlps = st.sidebar.number_input("Mailroom Helpers", 3)
mh_hrs = st.sidebar.number_input("Mailroom Helper Hours", 1.0)

if user == "boat hen":
    st