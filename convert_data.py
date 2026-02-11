import pandas as pd
import json
import os
import re

# CONFIG
# This maps the *Target Name* to the list of *Source Names* to merge.
TOPIC_MERGES = {
    "Bhaktivedanta Book Trust": [
        "BBT/GBC", "BBT-GBC Relations Committee", "Bhaktivedanta Institute", 
        "Bhaktivedanta Research Center", "Book Distribution (BBT)", 
        "Book Distribution Ministry", "BBT"
    ],
    "Child Protection Office": [
        "CPO", "CPT/GBC", "Child Protection Office", "Child Protection Task Force"
    ],
    "Deity Worship": [
        "Deity Worship", "Deity Worship Committee", "Deity Worship Ministry"
    ],
    "Divisional Council": [
        "Divisional Council", "Divisional Councils"
    ],
    "Education Committee": [
        "Education", "Education Committee"
    ],
    "Finance and Accounting": [
        "Finance", "Finance & Accounting"
    ],
    "GBC": [
        "GBC", "GBC/ Guru Services", "GBC/Law", "GBC/ Mayapur", "GBC/SAC", 
        "GBC Deputies", "GBC Education Committee", "GBC Executive Committee", 
        "GBC Executive Office", "GBC Finance", "GBC Organizational Development Committee", 
        "GBC Preaching Subcommittee", "GBC Sannyasa Sub-committee", "GBC Secretariat"
    ],
    "Grhasta Ministry": [
        "Grhasta Ministry", "Grhasta and Community Development Ministry"
    ]
}

def get_era(year):
    try:
        y = int(year)
        return f"{int(y//10 * 10)}s" if y > 0 else "Unknown"
    except: return "Unknown"

def clean_str(val):
    return str(val).strip() if val is not None else ""

def run_conversion():
    data_folder = "data"
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
        res['Resolution_ID'] = clean_str(row.get('Resolution_ID', "MISSING-ID"))
        res['Full_Text'] = clean_str(row.get('Full_Text', ""))
        res['Title'] = clean_str(row.get('Title', "Untitled"))
        
        try: res['Year'] = int(float(row.get('Year', 0)))
        except: res['Year'] = 0
        res['Date_Passed'] = clean_str(row.get('Date_Passed', res['Year']))
        
        res['Is_Active'] = str(row.get('Status', 'active')).lower() == 'active'
        res['Shelf'] = get_era(res['Year'])
        
        # --- 1. MERGE TOPICS (MINISTRIES) ---
        raw_ministry = clean_str(row.get('Section_Ministry', 'Uncategorized')) or 'Uncategorized'
        
        # Check if this ministry exists in any of our merge lists
        final_ministry = raw_ministry # Default to original
        for target, sources in TOPIC_MERGES.items():
            # Case-insensitive check
            if raw_ministry.lower() in [s.lower() for s in sources]:
                final_ministry = target
                break
        
        res['Section_Ministry'] = final_ministry
        # ------------------------------------

        # --- 2. MERGE CATEGORIES (Previous Request) ---
        raw_cat = clean_str(row.get('Category', 'General')) or 'General'
        if raw_cat == "Administrative order": res['Category'] = "Administrative Order"
        elif raw_cat == "Governing law": res['Category'] = "Governing Law"
        else: res['Category'] = raw_cat
        # ----------------------------------------------

        res['Scope'] = clean_str(row.get('Scope', 'Global')) or 'Global'
        res['Amends_IDs'] = clean_str(row.get('Amends_IDs', ''))
        res['Repeals_IDs'] = clean_str(row.get('Repeals_IDs', ''))

        # Generate simple code (First 3 letters uppercase) for internal logic
        res['Chapter_Code'] = res['Section_Ministry'][:3].upper()

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