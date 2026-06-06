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
    
    dfs = []
    for target in files:
        try:
            # This is the crucial part I accidentally deleted earlier. It skips the mill's junk header.
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

    # Safety catch so the math engine doesn't crash on empty cells
    df['Price_Final'] = df['Net'].apply(lambda x: x if x and x > 0 else None).fillna(df['P'])
    df = df.dropna(subset=['Price_Final','W_mm','G'])

    if df.empty: return df, "Inventory loaded but could not find valid prices or widths."

    df['Price/lb'] = (df['Price_Final']/2204.62).apply(lambda x: round(x+1e-9, 2))
    df['Width'] = (df['W_mm']/25.4).round(1)
    df['Weight'] = (df