import pandas as pd
import numpy as np
import math
import re

def extract_clean_number(val):
    if pd.isna(val):
        return np.nan
    text_val = str(val)
    match = re.search(r'[\d\.]+', text_val)
    if match:
        return float(match.group())
    return np.nan

def clean_inventory_sheet(file_name, output_name):
    # The actual data in these specific OVOL exports is buried on row 8
    df = pd.read_csv(file_name, skiprows=7)
    
    # Price per Pound Calculation (aggressively rounded UP to nearest penny)
    df['Price/lb'] = (df['Price/mt'] / 2204.62).apply(
        lambda x: math.ceil(x * 100) / 100 if pd.notna(x) else x
    )
    
    # Convert mm to standard Inches
    df['Raw Width'] = df['Roll Width'].apply(extract_clean_number)
    df['Paper Size (Inches)'] = np.round(df['Raw Width'] / 25.4, 2)
    
    # Convert Grammage to standard Newsprint Basis Weight (#)
    df['Raw Grammage'] = df['Grammage (g/m²)'].apply(extract_clean_number)
    df['Paper Weight (#)'] = np.round(df['Raw Grammage'] * 0.61386, 1)
    
    # Force cost columns up to the nearest cent
    for col in ['Cost', 'Net Cost']:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: math.ceil(x * 100) / 100 if pd.notna(x) else x
            )

    # Scrub the intermediate columns before exporting the final sheet
    df = df.drop(columns=['Raw Width', 'Raw Grammage'])
    
    df.to_csv(output_name, index=False)
    print(f"Successfully converted {file_name} -> {output_name}")

# Execute the conversions
clean_inventory_sheet("Minot.xlsx - Inventory.csv", "Minot_Converted.csv")
clean_inventory_sheet("Madelia.xlsx - Inventory.csv", "Madelia_Converted.csv")