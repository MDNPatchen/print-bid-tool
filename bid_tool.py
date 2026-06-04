import streamlit as st
import pandas as pd

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

st.set_page_config(page_title="Print Production Bid Tool", layout="wide")
st.title("📰 Newspaper Job Bid Worksheet")

st.sidebar.header("Job Specs & Location")
selected_location = st.sidebar.selectbox("Select Production Facility", list(LOCATIONS.keys()))
rates = LOCATIONS[selected_location]

customer_name = st.sidebar.text_input("Customer", "Mantako")
job_desc = st.sidebar.text_input("Job Description", "Free Press")

press_run = st.sidebar.number_input("Press Run", value=5890, step=100)
broadsheet_pages = st.sidebar.number_input("Broadsheet Pages", value=20)
web_width = st.sidebar.number_input("Web Width (inches)", value=22.0)
basis_weight = st.sidebar.number_input("Basis Weight (lbs)", value=27.7)
press_cutoff = st.sidebar.number_input("Press Cut-Off", value=21.25)

run_hours = st.sidebar.number_input("Time for run (hours)", value=1.0)
num_leaders = st.sidebar.number_input("Number of leaders on crew", value=1)
num_helpers = st.sidebar.number_input("Number of helpers on crew", value=2)
make_ready_hours = st.sidebar.number_input("Make-ready/clean-up hours", value=0.5)

camera_plate_hours = st.sidebar.number_input("Camera/Plate hours", value=0.5)
black_plates = st.sidebar.number_input("Number of black plates", value=20)
color_plates = st.sidebar.number_input("Number of color plates", value=12)
plate_sets = st.sidebar.number_input("Number of plate sets", value=1)

mailroom_manning = st.sidebar.number_input("Mailroom Leaders during run", value=1)
inserting_man_hours = st.sidebar.number_input("Mailroom Helpers hours", value=4.0)

total_pages = press_run * broadsheet_pages
pages_per_pound = 1900000 / (web_width * press_cutoff * basis_weight)

pounds_of_waste = (total_pages / pages_per_pound) * rates["waste_pct"]
total_pounds = (total_pages / pages_per_pound) + pounds_of_waste
newsprint_cost = total_pounds * rates["newsprint_cost_per_lb"]

black_ink_cost = total_pages * rates["black_ink_cost_per_impression"]

leader_cost = num_leaders * rates["press_leader_rate"] * run_hours
helper_cost = num_helpers * rates["press_helper_rate"] * run_hours
make_ready_cost = make_ready_hours * rates["make_ready_rate"]

press_maint_cost = newsprint_cost * rates["press_overhead_maint_pct"]

total_plates = (black_plates + color_plates) * plate_sets
plate_material_cost = total_plates * rates["plate_cost"]
plate_maint_cost = total_plates * rates["plate_overhead_maint"]
camera_plate_labor = camera_plate_hours * rates["camera_plate_rate"]

color_ink_cost = color_plates * (press_run / 1000) * rates["color_ink_cost_per_plate_m"]

mailroom_run_cost = mailroom_manning * rates["mailroom_leader_rate"] * run_hours
inserting_cost = inserting_man_hours * rates["mailroom_helper_rate"]

subtotal = sum([
    newsprint_cost, black_ink_cost, leader_cost, helper_cost, 
    make_ready_cost, press_maint_cost, plate_material_cost, 
    plate_maint_cost, camera_plate_labor, color_ink_cost, 
    mailroom_run_cost, inserting_cost
])

overhead_cost = subtotal * rates["overhead_pct"]
total_cost = subtotal + overhead_cost
profit = total_cost * rates["profit_margin"]
total_charge = total_cost + profit

st.header(f"Bid Summary: {customer_name} - {job_desc}")

col1, col2, col3 = st.columns(3)
col1.metric("Total Paper Cost", f"${newsprint_cost:.2f}")
col2.metric("Total Labor & Press", f"${(leader_cost + helper_cost + make_ready_cost + press_maint_cost + mailroom_run_cost + inserting_cost):.2f}")
col3.metric("Pre-Press & Ink", f"${(plate_material_cost + plate_maint_cost + camera_plate_labor + black_ink_cost + color_ink_cost):.2f}")

st.divider()

st.subheader("Bottom Line")
b_col1, b_col2, b_col3, b_col4 = st.columns(4)
b_col1.metric("Subtotal", f"${subtotal:.2f}")
b_col2.metric(f"Overhead ({rates['overhead_pct']*100}%)", f"${overhead_cost:.2f}")
b_col3.metric("Total Cost", f"${total_cost:.2f}")
b_col4.metric(f"Total Charge (w/ {rates['profit_margin']*100}% Margin)", f"${total_charge:.2f}")

st.caption("Rates actively adapt based on facility selection.")