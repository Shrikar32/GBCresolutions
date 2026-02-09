import json
import os
import re
from typing import Optional, List, Dict
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

# --- 1. CONFIGURATION ---
app = FastAPI()

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Color Badges (Code -> Color Style)
CATEGORY_COLORS = {
    "ADM": "bg-slate-100 text-slate-700 border-slate-200",  # Administration
    "FIN": "bg-emerald-50 text-emerald-700 border-emerald-200", # Finance
    "GUR": "bg-amber-50 text-amber-700 border-amber-200",     # Guru Services
    "ZON": "bg-indigo-50 text-indigo-700 border-indigo-200",   # Zonal
    "EDU": "bg-sky-50 text-sky-700 border-sky-200",         # Education
    "LAW": "bg-rose-50 text-rose-700 border-rose-200",       # Legal
    "DEV": "bg-purple-50 text-purple-700 border-purple-200",   # Devotee Care / Development
    "BBT": "bg-orange-50 text-orange-700 border-orange-200",   # Book Trust
    "COM": "bg-blue-50 text-blue-700 border-blue-200",       # Communications
    "PRE": "bg-pink-50 text-pink-700 border-pink-200"        # Preaching
}

# FULL MAPPING: Code -> Full Name
# This ensures that selecting "Education" matches "EDU" and vice versa.
MINISTRY_NAMES = {
    "ADM": "Administration",
    "FIN": "Finance & Accounting",
    "GUR": "Guru Services",
    "ZON": "Zonal Services",
    "EDU": "Education",
    "LAW": "Justice & Legal",
    "DEV": "Devotee Care",
    "BBT": "Book Distribution (BBT)",
    "COM": "Communications",
    "PRE": "Preaching & Outreach",
    "TEM": "Temple Development",
    "ISK": "ISKCON Property",
    "MAN": "Management"
}

# Mapping: Full Name -> Code (Created dynamically)
NAME_TO_CODE = {v: k for k, v in MINISTRY_NAMES.items()}

# --- 2. DATA LOADING (JSON) ---
RESOLUTIONS: List[Dict] = []
RESOLUTION_META: Dict[str, Dict] = {}
REVERSE_LINKS: Dict[str, List[Dict]] = {}
NAV_TREE: Dict[str, List[int]] = {}

def clean_id_list(id_str):
    if not id_str: return []
    return [x.strip() for x in re.split(r'[,;]', str(id_str)) if x.strip()]

def load_data():
    global RESOLUTIONS, RESOLUTION_META, REVERSE_LINKS, NAV_TREE, NAME_TO_CODE
    
    json_path = os.path.join("data", "resolutions.json")
    
    if not os.path.exists(json_path):
        print("WARNING: resolutions.json not found.")
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            RESOLUTIONS = json.load(f)

        # 1. Build Metadata Map
        RESOLUTION_META = {r['Resolution_ID']: {"year": r['Year'], "date": r['Date_Passed']} for r in RESOLUTIONS}
        
        # 2. Build Links & Nav Tree
        unique_shelves = set()
        
        for res in RESOLUTIONS:
            # Reverse Links
            if res.get('Amends_IDs'):
                for target in clean_id_list(res['Amends_IDs']):
                    REVERSE_LINKS.setdefault(target, []).append(
                        {"type": "AMENDED BY", "source_id": res['Resolution_ID'], "date": res['Date_Passed']}
                    )
            
            if res['Shelf'] != "Unknown":
                unique_shelves.add(res['Shelf'])

        # 3. Build Navigation Tree
        sorted_eras = sorted(list(unique_shelves), reverse=True)
        for era in sorted_eras:
            years = sorted(list(set(r['Year'] for r in RESOLUTIONS if r['Shelf'] == era)), reverse=True)
            NAV_TREE[era] = years

        print(f"✅ Loaded {len(RESOLUTIONS)} records.")

    except Exception as e:
        print(f"❌ Error loading JSON: {e}")

load_data()

# --- 3. HELPER FUNCTIONS ---
def resolve_links(id_list_str, rel_type):
    links = []
    for rid in clean_id_list(id_list_str):
        clean_id = str(rid).strip()
        meta = RESOLUTION_META.get(clean_id)
        if meta:
            links.append({"id": clean_id, "type": rel_type, "year": meta.get('year', 'N/A')})
        else:
            links.append({"id": clean_id, "type": rel_type, "year": "Ref"})
    return links

# --- 4. ROUTES ---
@app.get("/")
async def home(request: Request):
    if not RESOLUTIONS: load_data()
    stats = {
        "count": len(RESOLUTIONS),
        "min_year": min((r['Year'] for r in RESOLUTIONS), default=0) if RESOLUTIONS else 0,
        "max_year": max((r['Year'] for r in RESOLUTIONS), default=0) if RESOLUTIONS else 0,
    }
    return templates.TemplateResponse("home.html", {"request": request, "stats": stats})

@app.get("/archive")
async def archive(request: Request, q: Optional[str] = None, ministry: Optional[str] = None, category: Optional[str] = None, scope: Optional[str] = None, year: Optional[str] = None):
    # Start with all data
    results = RESOLUTIONS
    
    # --- 1. SMART MINISTRY FILTER (Cross-Correct) ---
    if ministry:
        # Check if the user selected a "Full Name" (e.g., "Education")
        target_code = NAME_TO_CODE.get(ministry)
        
        # Check if they selected a "Code" directly (e.g., "EDU")
        target_name = MINISTRY_NAMES.get(ministry)

        results = [
            r for r in results 
            if r['Section_Ministry'] == ministry  # Exact match
            or (target_code and r['Chapter_Code'] == target_code) # Name matches Code (Education -> EDU)
            or (target_name and r['Section_Ministry'] == target_name) # Code matches Name (EDU -> Education)
        ]

    # --- 2. OTHER FILTERS ---
    if category: results = [r for r in results if r['Category'] == category]
    if scope: results = [r for r in results if r['Scope'] == scope]
    if year and year.isdigit(): results = [r for r in results if r['Year'] == int(year)]
    
    # --- 3. SMART KEYWORD SEARCH ---
    if q:
        terms = [t.lower() for t in q.split() if t.strip()]
        if terms:
            filtered_results = []
            for r in results:
                id_txt = r['Resolution_ID'].lower()
                title_txt = r['Title'].lower()
                body_txt = r['Full_Text'].lower()
                
                all_found = True
                for term in terms:
                    # Boundary matching: start of word
                    pattern = r'\b' + re.escape(term)
                    found = (re.search(pattern, id_txt) or re.search(pattern, title_txt) or re.search(pattern, body_txt))
                    if not found:
                        all_found = False
                        break
                
                if all_found:
                    filtered_results.append(r)
            results = filtered_results

    # --- 4. DYNAMIC DROPDOWNS (Smart List) ---
    # We want to display nice names in the dropdown, not just raw codes.
    raw_ministries = set(r['Section_Ministry'] for r in RESOLUTIONS)
    
    clean_ministry_list = set()
    for m in raw_ministries:
        # If 'm' is a code (e.g., "EDU"), show "Education"
        if m in MINISTRY_NAMES:
            clean_ministry_list.add(MINISTRY_NAMES[m])
        # If 'm' is already a name (e.g., "Education"), keep it
        elif m in NAME_TO_CODE:
            clean_ministry_list.add(m)
        else:
            # Fallback for unknown ones
            clean_ministry_list.add(m)
            
    unique_ministries = sorted(list(clean_ministry_list))
    unique_categories = sorted(list(set(r['Category'] for r in RESOLUTIONS)))
    unique_scopes = sorted(list(set(r['Scope'] for r in RESOLUTIONS)))

    return templates.TemplateResponse("archive.html", {
        "request": request, "results": results, "query": q, "nav": NAV_TREE,
        "ministries": unique_ministries, "categories": unique_categories, "scopes": unique_scopes,
        "selected_ministry": ministry, "selected_category": category, "selected_scope": scope, "selected_year": year,
        "cat_colors": CATEGORY_COLORS,
        "min_names": MINISTRY_NAMES
    })

@app.get("/page/{res_id}")
async def page_view(request: Request, res_id: str):
    res_id_clean = str(res_id).strip()
    res = next((r for r in RESOLUTIONS if r['Resolution_ID'] == res_id_clean), None)
    
    if not res: return RedirectResponse("/archive")
    
    trace = {
        "forward": resolve_links(res.get('Amends_IDs'), "AMENDS") + resolve_links(res.get('Repeals_IDs'), "REPEALS"),
        "backward": REVERSE_LINKS.get(res_id_clean, [])
    }
    return templates.TemplateResponse("resolution.html", {
        "request": request, "res": res, "trace": trace, 
        "cat_colors": CATEGORY_COLORS, "nav": NAV_TREE, 
        "min_names": MINISTRY_NAMES
    })