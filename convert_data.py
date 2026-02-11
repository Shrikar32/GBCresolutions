import pandas as pd
import json
import os
import re

# CONFIG: KEYWORD MATCHING
# The script checks these in order. If a keyword matches, it assigns that Category.
# Order matters! (e.g., Check "Education" before "GBC" so "GBC Education" becomes "Education")
KEYWORD_MAP = {
    "Child Protection Office": ["child", "cpo", "cpt", "abuse"],
    "Bhaktivedanta Book Trust": ["bbt", "book", "publish", "trust"],
    "Education": ["educ", "school", "academ", "institut", "training", "research", "shastric"],
    "Justice & Legal": ["law", "legal", "justice", "dispute", "constitution", "property", "title"],
    "Finance & Accounting": ["financ", "account", "audit", "budget", "treasur"],
    "Deity Worship": ["deity", "worship", "arcana", "puja"],
    "Guru Services": ["guru", "disciple", "initiation"],
    "Preaching & Sannyasa": ["preach", "sannyas", "congregation", "outreach", "harinam", "book dist"],
    "Community & Social": ["grhasta", "grihastha", "women", "vaishnavi", "cow", "farm", "youth", "social"],
    "Communications": ["communic", "public relation", "media"],
    "Zonal Services": ["zonal", "regional", "divisional", "council"],
    "Administration": ["admin", "exec", "secretar", "manag", "ministr", "committee", "office"],
    "GBC Body": ["gbc", "resolution", "meeting"]  # Catch-all for remaining GBC items
}

def get_era(year):
    try:
        y = int(year)
        return f"{int(y//10 * 10)}s" if y > 0 else "Unknown"
    except: return "Unknown"

def clean_str(val):
    return str(val).strip() if val is not None else ""

def normalize_ministry(raw_name):
    """Scans the raw name for keywords and returns the Standard Category."""
    if not raw_name: return "Uncategorized"
    
    raw_lower = raw_name.lower()
    
    # 1. Check against our Keyword Map
    for category, keywords in KEYWORD_MAP.items():
        for k in keywords:
            # Check if keyword exists as a distinct word or start of word
            if k in raw_lower:
                return category
    
    # 2. If no keyword matched, return original (capitalized nicely)
    return raw_name

def run_conversion():
    data_folder = "data"
    files = [f for f in os.listdir(data_folder) if f.endswith('.xlsx') and not f.startswith('~')]
    if not files:
        print("❌ No Excel file found in 'data/' folder!")
        return

    filepath = os.path.join(data_folder, files[0])
    print(f"📂 Reading: {filepath}...")
    
    try:
        df = pd.read_excel(filepath)
    except PermissionError:
        print("❌ ERROR: Excel file is OPEN. Please close it and try again.")
        return

    df = df.fillna('')
    optimized_data = []

    for _, row in df.iterrows():
        res = {}
        res['Resolution_ID'] = clean_str(row.get('Resolution_ID', "MISSING-ID"))
        res['Full_Text'] = clean_str(row.get('Full_Text', ""))
        res['Title'] = clean_str(row.get('Title', "Untitled"))
        
        try: res['Year'] = int(float(row.get('Year', 0)))
        except: res['Year'] = 0
        res['Date_Passed'] = clean_str(row.get('Date_Passed', res['Year']))
        
        res['Is_Active'] = str(row.get('Status', 'active')).lower() == 'active'
        res['Shelf'] = get_era(res['Year'])
        
        # --- SMART MERGE LOGIC ---
        raw_ministry = clean_str(row.get('Section_Ministry', 'Uncategorized'))
        res['Section_Ministry'] = normalize_ministry(raw_ministry)
        # -------------------------

        # Category Cleanup (Administrative/Governing)
        raw_cat = clean_str(row.get('Category', 'General'))
        if "admin" in raw_cat.lower(): res['Category'] = "Administrative Order"
        elif "govern" in raw_cat.lower(): res['Category'] = "Governing Law"
        else: res['Category'] = raw_cat

        res['Scope'] = clean_str(row.get('Scope', 'Global')) or 'Global'
        res['Amends_IDs'] = clean_str(row.get('Amends_IDs', ''))
        res['Repeals_IDs'] = clean_str(row.get('Repeals_IDs', ''))

        # Generate simplified Code for colors (First 3 chars of merged name)
        res['Chapter_Code'] = res['Section_Ministry'][:3].upper()

        optimized_data.append(res)

    # Sort: Newest first
    optimized_data.sort(key=lambda x: (-x['Year'], x['Resolution_ID']))

    # Save to JSON
    output_path = os.path.join(data_folder, 'resolutions.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(optimized_data, f, ensure_ascii=False) 
    
    print(f"✅ SUCCESS! Cleaned & Merged {len(optimized_data)} records.")

if __name__ == "__main__":
    run_conversion()