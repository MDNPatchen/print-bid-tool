import streamlit as st
import pandas as pd
import math
import re
import os
import csv

# Standard Excel-style rounding to perfectly match your spreadsheet 
def round_cents(val):
    return round(val + 1e-9, 2)

# --- USER ACCESS DICTIONARY ---
AUTHORIZED_USERS = {
    "bob patchen": ["Minot", "Madelia (HOP)"], 
    "boat hen": ["Minot", "Madelia (HOP)"], 
    "mike christman": ["Minot", "Madelia (HOP)"],         
    "brenda ahern": ["Madelia (HOP)"],
    "terry saar": ["Madelia (HOP)"]
}

LOCATIONS = {
    "Madelia (HOP)": {
        "profit_margin": 0.25,
        "overhead_pct": 0.26,
        "newsprint_cost_per_lb": 0.35, 
        "waste_pct": 0.10,
        "black_ink_cost_per_impression": 0.0006,
        "press_leader_rate": 30.00,
        "press_helper_rate": 25.00,
        "camera_plate_rate": 30.00,
        "make_ready_rate": 30.00,
        "press_overhead_maint_pct": 0.10,
        "plate_cost": 5.25,
        "plate_overhead_maint": 0.75,
        "color_ink_cost_per_plate_m": 0.95,
        "mailroom_leader_rate": 30.00,
        "mailroom_helper_rate": 25.00,
    },
    "Minot": {
        "profit_margin": 0.25, 
        "overhead_pct": 0.26,
        "newsprint_cost_per_lb": 0.35, 
        "waste_pct": 0.10,
        "black_ink_cost_per_impression": 0.0006,
        "press_leader_rate": 31.34,
        "press_helper_rate": 22.43,
        "camera_plate_rate": 30.00,
        "make_ready_rate": 31.34, 
        "press_overhead_maint_pct": 0.10,
        "plate_cost": 5.25,
        "plate_overhead_maint": 0.75,
        "color_ink_cost_per_plate_m": 0.95,
        "mailroom_leader_rate": 24.11,
        "mailroom_helper_rate": 16.15, 
    }
}

# --- BULLETPROOF RAW TEXT INVENTORY LOADER ---
def load_inventory_data(location_name):
    base_name = location_name.split(" ")[0].lower()
    
    all_files = os.listdir('.')
    target_file = None
    for f in all_files:
        if base_name in f.lower() and f.lower().endswith('.csv'):
            target_file = f
            break
            
    if not target_file:
        return pd.DataFrame(), f"Could not find any CSV file containing '{base_name}' in the vault."
        
    try:
        with open(target_file, 'r', encoding='latin1', errors='replace') as f:
            reader = csv.reader(f)
            data = list(reader)
            
        header_idx = -1
        for i, row in enumerate(data):
            if len(row) > 0 and 'Ownership' in str(row[0]):
                header_idx = i
                break
                
        if header_idx == -1: