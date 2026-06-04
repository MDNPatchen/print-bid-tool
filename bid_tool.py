import streamlit as st
import pandas as pd
import math
import re
import os
import csv

# Helper to aggressively round up to the nearest cent
def round_cents(val):
    return math.ceil(val * 100) / 100

# --- USER ACCESS DICTIONARY ---
AUTHORIZED_USERS = {
    "bob patchen": ["Minot", "Madelia (HOP)"], 
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
        "make_ready_