import streamlit as st, pandas as pd, math, re, os, csv

def round_cents(val): return round(val + 1e-9, 2)

AUTH = {"bob patchen":["Madelia (HOP)"], "boat hen":["Madelia (HOP)"], "mike christman":["Madelia (HOP)"], "brenda ahern":["Madelia (HOP)"], "terry saar":["Madelia (HOP)"]}

LOCS = {
    "Madelia (HOP)": {"profit_margin":0.25,"overhead_pct":0.26,"newsprint_cost_per_lb":0.35,"black_ink_cost_per_impression":0.0006,"press_leader_rate":30.0,"press_helper_rate":25.0,"camera_plate_rate":30.0,"make_ready_rate":30.0,"press_overhead_maint_pct":0.10,"plate_cost":5.25,"plate_overhead_maint":0.75,"color_ink_cost_per_plate_m":0.95,"mailroom_leader_rate":30.0,"mailroom_helper_rate":25.0}
}

def load_inv():
    target = next((f for f in os.listdir('.') if 'inventory' in f.lower() and f.endswith('.csv')), None)
    if not target: return pd.DataFrame(), "No inventory CSV found."
    try:
        with open(target, 'r', encoding='latin1', errors='replace') as f: data = list(csv.reader(f))
        h_idx = next((i for i, r in enumerate(data) if r and 'Ownership' in str(r[0])), -1)
        if h_idx == -1: return pd.DataFrame(), "Header not found."
        df = pd.DataFrame(data[h_idx+1:], columns=[str(h).strip() for h in data[h_idx]])
        # Standardize column mapping
        cmap = {'Price/mt':'Price', 'Net Price/mt':'Net_Price', 'Roll Width':'Width', 'Grammage (g/m²)':'Grammage'}
        df = df.rename(columns=cmap)
        def ext(v):
            m = re.search(r'[\d\.]+', str(v))
            return float(m.group()) if m and not pd.isna(v) else None
        df['P'] = df['Price'].apply(ext); df['Net'] = df['Net_Price'].apply(ext); df['W_mm'] = df['Width'].apply(ext); df['G'] = df['Grammage'].apply(ext)
        df['Price_Final'] = df['Net'].apply(lambda x: x if x and x > 0 else None).fillna(df['P'])
        df = df.dropna(subset=['Price_Final','W_mm','G'])
        df['Price/lb'] = (df['Price_Final']/2204.62).apply(lambda x: round(x+1e-9, 2))
        df['Width'] = (df['W_mm']/25.4).round(1); df['Weight'] = (df['G']*0.61386).round(1)
        return df.dropna(subset=['Width','Weight','Price/lb']), "Success"
    except Exception as e: return pd.DataFrame(), str(e)

st.set_page_config(page_title="Bid Tool", layout="wide")
user = st.sidebar.text_input("User Name:").strip().lower()
st.sidebar.button("Unlock")
if not user or user not in AUTH: st.stop()

inv, msg = load_inv()
if inv.empty:
    st.error(f"Inventory Error: {msg}")
    st.stop()

cust, desc = st.sidebar.text_input("Customer", "Mantako"), st.sidebar.text_input("Job", "Free Press")
run, waste = st.sidebar.number_input("Press Run", 5890, step=100), st.sidebar.number_input("Waste Copies", 589, step=50)
fmt, rtype = st.sidebar.selectbox("Format", ["Broadsheet", "Tabloid", "Book"]), st.sidebar.selectbox("Run Type", ["Collect", "Straight"])
t_pgs, c_pgs = st.sidebar.number_input("Total Pages", 20), st.sidebar.number_input("Color Pages", 4)

sz = st.sidebar.selectbox("Web Width", sorted(inv['Width'].unique()))
wt = st.sidebar.selectbox("Basis Weight", sorted(inv[inv['Width']==sz]['Weight'].unique()))
p_cost = round_cents(inv[(inv['Width']==sz)&(inv['Weight']==wt)]['Price/lb'].mean() * 1.10)
st.sidebar.success(f"Inventory Active: Billed at ${p_cost:.3f}/lb")

cut = st.sidebar.number_input("Press Cut-Off", 21.25)
cp, r_hrs, p_ldrs, p_hlps, mr = st.sidebar.number_input("Plate Hrs", 0.5), st.sidebar.number_input("Run Hrs", 1.0), st.sidebar.number_input("Leaders", 1), st.sidebar.number_input("Helpers", 2), st.sidebar.number_input("MR Hrs", 0.5)
ml_ldr, ml_lhrs, ml_hlp, ml_hhrs = st.sidebar.number_input("ML Leaders", 1), st.sidebar.number_input("ML L-Hrs", 0.0), st.sidebar.number_input("ML Helpers", 3), st.sidebar.number_input("ML H-Hrs", 0.0)

f_div = 2 if fmt=="Broadsheet" else (4 if fmt=="Tabloid" else 8)
r_mult = 2 if rtype=="Straight" else 1
tot_pl = (math.ceil(t_pgs/f_div) * r_mult) + (math.ceil(c_pgs/f_div) * 3 * r_mult)
total_pages_printed = (run + waste) * t_pgs
tot_lbs = total_pages_printed / (1900000 / (sz * cut * wt))
c_news = round_cents(tot_lbs * p_cost)
c_ink = round_cents(total_pages_printed * 0.0006)
c_sub = round_cents(c_news + c_ink + (p_ldrs*30.0*r_hrs) + (p_hlps*25.0*r_hrs) + (mr*30.0) + (tot_pl*5.25) + (tot_pl*0.75) + (cp*30.0) + ((math.ceil(c_pgs/f_div)*3*r_mult)*(run/1000)*0.95) + (ml_ldr*ml_lhrs*30.0 + ml_hlp*ml_hhrs*25.0))
t_cost = round_cents(c_sub * 1.26)
t_chg = round_cents(t_cost * 1.25)

st.header(f"Bid Summary: {cust} - {desc}")
c1, c2, c3 = st.columns(3)
c1.metric("Paper", f"${c_news:.2f}"); c2.metric("Labor", f"${(c_sub-c_news-c_ink-(tot_pl*5.25)-(tot_pl*0.75)-((math.ceil(c_pgs/f_div)*3*r_mult)*(run/1000)*0.95)):.2f}"); c3.metric("Ink/Plates", f"${(c_ink+(tot_pl*5.25)+(tot_pl*0.75)+(cp*30.0)+((math.ceil(c_pgs/f_div)*3*r_mult)*(run/1000)*0.95)):.2f}")
st.divider()
b1, b2 = st.columns(2)
b1.metric("Total Cost", f"${t_cost:.2f}"); b2.metric("Total Charge", f"${t_chg:.2f}")