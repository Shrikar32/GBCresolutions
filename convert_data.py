import pandas as pd
import json
import os
import re

# CONFIG
MINISTRY_CODE_MAP = ["ADM", "FIN", "GUR", "ZON", "EDU", "LAW"]

def get_era(year):
    try:
        y = int(year)
        return f"{int(y//10 * 10)}s" if y > 0 else "Unknown"
    except: return "Unknown"

def clean_str(val):
    return str(val).strip() if val is not None else ""

def run_conversion():
    data_folder = "data"
    # Find the Excel file
    files = [f for f in os.listdir(data_folder) if f.endswith('.xlsx') and not f.startswith('~')]
    if not files:
        print("❌ No Excel file found in 'data/' folder!")
        return

    filepath = os.path.join(data_folder, files[0])
    print(f"📂 Reading: {filepath}...")
    
    df = pd.read_excel(filepath)
    df = df.fillna('')

    optimized_data = []

    for _, row in df.iterrows():
        res = {}
        # 1. Basic Fields
        res['Resolution_ID'] = clean_str(row.get('Resolution_ID', "MISSING-ID"))
        res['Full_Text'] = clean_str(row.get('Full_Text', ""))
        res['Title'] = clean_str(row.get('Title', "Untitled"))
        
        # 2. Year & Date
        try: res['Year'] = int(float(row.get('Year', 0)))
        except: res['Year'] = 0
        res['Date_Passed'] = clean_str(row.get('Date_Passed', res['Year']))
        
        # 3. Categorization
        res['Is_Active'] = str(row.get('Status', 'active')).lower() == 'active'
        res['Shelf'] = get_era(res['Year'])
        res['Section_Ministry'] = clean_str(row.get('Section_Ministry', 'Uncategorized')) or 'Uncategorized'
        res['Category'] = clean_str(row.get('Category', 'General')) or 'General'
        res['Scope'] = clean_str(row.get('Scope', 'Global')) or 'Global'
        
        # 4. Links (Pre-clean them)
        res['Amends_IDs'] = clean_str(row.get('Amends_IDs', ''))
        res['Repeals_IDs'] = clean_str(row.get('Repeals_IDs', ''))

        # 5. Generate the Chapter Code (ADM, FIN...)
        code = res['Section_Ministry'].upper()
        res['Chapter_Code'] = code if code in MINISTRY_CODE_MAP else "ADM"

        optimized_data.append(res)

    # Sort: Newest first
    optimized_data.sort(key=lambda x: (-x['Year'], x['Resolution_ID']))

    # Save to JSON
    output_path = os.path.join(data_folder, 'resolutions.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(optimized_data, f, ensure_ascii=False) 
    
    print(f"✅ SUCCESS! Converted {len(optimized_data)} records to {output_path}")

if __name__ == "__main__":
    run_conversion()