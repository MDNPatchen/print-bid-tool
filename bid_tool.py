import streamlit as st, pandas as pd, math, re, os, csv

def round_cents(val): return round(val + 1e-9, 2)

AUTH = {"bob patchen":["Minot","Madelia (HOP)"], "boat hen":["Minot","Madelia (HOP)"], "mike christman":["Minot","Madelia (HOP)"], "brenda ahern":["Madelia (HOP)"], "terry saar":["Madelia (HOP)"]}

LOCS = {
    "Madelia (HOP)": {"profit_margin":0.25,"overhead_pct":0.26,"newsprint_cost_per_lb":0.35,"black_ink_cost_per_impression":0.0006,"press_leader_rate":30.0,"press_helper_rate":25.0,"camera_plate_rate":30.0,"make_ready_rate":30.0,"press_overhead_maint_pct":0.10,"plate_cost":5.25,"plate_overhead_maint":0.75,"color_ink_cost_per_plate_m":0.95,"mailroom_leader_rate":30.0,"mailroom_helper_rate":25.0},
    "Minot": {"profit_margin":0.25,"overhead_pct":0.26,"newsprint_cost_per_lb":0.35,"black_ink_cost_per_impression":0.0006,"press_leader_rate":31.34,"press_helper_rate":22.43,"camera_plate_rate":30.0,"make_ready_rate":31.34,"press_overhead_maint_pct":0.10,"plate_cost":5.25,"plate_overhead_maint":0.75,"color_ink_cost_per_plate_m":0.95,"mailroom_leader_rate":24.11,"mailroom_helper_rate":16.15}
}

def load_inv(loc):
    base = loc.split(" ")[0].lower()
    target = next((f for f in os.listdir('.') if base in f.lower() and f.endswith('.csv')), None)
    if not target: return pd.DataFrame(), f"No CSV for {base}"
    try:
        with open(target, 'r', encoding='latin1', errors='replace') as f: data = list(csv.reader(f))
        h_idx = next((i for i, r in enumerate(data) if r and 'Ownership' in str(r[0])), -1)
        if h_idx == -1: return pd.DataFrame(), "No header."
        df = pd.DataFrame(data[h_idx+1:], columns=[str(h).strip() for h in data[h_idx]])
        cmap = {}
        for c in df.columns:
            cl = str(c).lower()
            if 'grammage' in cl and 'T_Gram' not in cmap.values(): cmap[c] = 'T_Gram'
            elif 'width' in cl and 'T_Wid' not in cmap.values(): cmap[c] = 'T_Wid'
            elif ('price/mt' in cl or 'price / mt' in cl) and 'net' not in cl and 'T_Pri' not in cmap.values(): cmap[c] = 'T_Pri'
        df = df.rename(columns=cmap)
        if not all(x in df.columns for x in ['T_Pri','T_Gram','T_Wid']): return pd.DataFrame(), "Missing columns."
        def ext(v):
            m = re.search(r'[\d\.]+', str(v))
            return float(m.group()) if m and not pd.isna(v) else None
        df['P'] = df['T_Pri'].apply(ext); df['W'] = df['T_Wid'].apply(ext); df['G'] = df['T_Gram'].apply(ext)
        df = df.dropna(subset=['P','W','G'])
        df['P/lb'] = (df['P']/2204.62).apply(lambda x: round(x+1e-9, 2))
        df['Width'] = (df['W']/25.4).round(1)
        df['Weight'] = (df['G']*0.61386).round(1)
        return df.dropna(subset=['Width','Weight','P/lb']), "Success"
    except Exception as e: return pd.DataFrame(), str(e)

st.set_page_config(page_title="Bid Tool", layout="wide")
user = st.sidebar.text_input("User Name:").strip().lower()
st.sidebar.button("Unlock")
if not user or user not in AUTH: st.stop()

loc = st.sidebar.selectbox("Facility", AUTH[user])
rates = LOCS[loc]
cust, desc = st.sidebar.text_input("Customer", "Mantako"), st.sidebar.text_input("Job", "Free Press")
run, waste = st.sidebar.number_input("Run", 5890, step=100), st.sidebar.number_input("Waste", 589, step=50)
fmt, rtype = st.sidebar.selectbox("Format", ["Broadsheet", "Tabloid", "Book"]), st.sidebar.selectbox("Run Type", ["Collect", "Straight"])
t_pgs, c_pgs = st.sidebar.number_input("Pages", 20), st.sidebar.number_input("Color", 4)

inv, msg = load_inv(loc)
p_cost, w_in, b_wt = 0.0, 22.0, 27.7
if not inv.empty:
    szs = sorted(inv['Width'].unique())
    sz = st.sidebar.selectbox("Web Width", szs)
    wts = sorted(inv[inv['Width']==sz]['Weight'].unique())
    wt = st.sidebar.selectbox("Basis Weight", wts)
    p_cost = round_cents(inv[(inv['Width']==sz)&(inv['Weight']==wt)]['P/lb'].mean() * 1.10)
    w_in, b_wt = sz, wt
    st.sidebar.success(f"Billed at ${p_cost:.2f}/lb")
else:
    w_in = st.sidebar.number_input("Web Width", 22.0)
    b_wt = st.sidebar.number_input("Basis Weight", 27.7)
    p_cost = round_cents(rates["newsprint_cost_per_lb"] * 1.10)
    st.sidebar.info(f"Billed at ${p_cost:.2f}/lb")

cut = st.sidebar.number_input("Cut-Off", 21.25)
cp, r_hrs, p_ldrs, p_hlps, mr = st.sidebar.number_input("Plate Hrs", 0.5), st.sidebar.number_input("Run Hrs", 1.0), st.sidebar.number_input("Leaders", 1), st.sidebar.number_input("Helpers", 2), st.sidebar.number_input("MR Hrs", 0.5)
ml_ldr, ml_lhrs, ml_hlp, ml_hhrs = st.sidebar.number_input("ML Leaders", 1), st.sidebar.number_input("ML L-Hrs", 3.0), st.sidebar.number_input("ML Helpers", 3), st.sidebar.number_input("ML H-Hrs", 1.0)

if user == "boat hen": st.sidebar.markdown("<div style='text-align:center;margin-top:70px;opacity:0.35;'><div style='font-family:Georgia,serif;font-size:34px;'>B <i>&</i> H</div><div style='font-size:9px;letter-spacing:6px;border-top:1px solid #bdc3c7;display:inline-block;'>PRINT WORKS</div></div>", unsafe_allow_html=True)

f_div = 2 if fmt=="Broadsheet" else (4 if fmt=="Tabloid" else 8)
tot_imps = (run + waste) * t_pgs
tot_lbs = tot_imps / (1900000 / (w_in * cut * b_wt))
c_news = round_cents(tot_lbs * p_cost)
c_ink = round_cents(tot_imps * rates["black_ink_cost_per_impression"])
c_pl = math.ceil(t_pgs/f_div) * (2 if rtype=="Straight" else 1)
c_col = math.ceil(c_pgs/f_div) * 3 * (2 if rtype=="Straight" else 1)
sub = round_cents(sum([c_news, c_ink, (p_ldrs*rates["press_leader_rate"]*r_hrs), (p_hlps*rates["press_helper_rate"]*r_hrs), (mr*rates["make_ready_rate"]), (c_news*0.1), ((c_pl+c_col)*5.25), ((c_pl+c_col)*0.75), (cp*rates["camera_plate_rate"]), (c_col*(run/1000)*0.95), (ml_ldr*ml_lhrs*rates["mailroom_leader_rate"] + ml_hlp*ml_hhrs*rates["mailroom_helper_rate"])]))
ovr = round_cents(sub * rates["overhead_pct"])
t_chg = round_cents((sub + ovr) * (1 + rates["profit_margin"]))

st.header(f"Bid Summary: {cust} - {desc}")
c1, c2, c3 = st.columns(3)
c1.metric("Paper", f"${c_news:.2f}"); c2.metric("Labor", f"${(sub-c_news-c_ink):.2f}"); c3.metric("Ink/Plates", f"${(c_ink+(c_pl+c_col)*5.25+ (c_pl+c_col)*0.75+cp*rates['camera_plate_rate']+c_col*(run/1000)*0.95):.2f}")
st.divider()
b1, b2 = st.columns(2)
b1.metric("Total Cost", f"${round_cents(sub+ovr):.2f}"); b2.metric("Total Charge", f"${t_chg:.2f}")