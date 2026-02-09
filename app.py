import pandas as pd
import os
import re
from typing import Optional, List, Dict
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

# --- 1. INITIALIZATION ---
app = FastAPI()

if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- 2. CONFIGURATION ---
# Colors for the badges
CATEGORY_COLORS = {
    "ADM": "bg-slate-100 text-slate-700 border-slate-200",
    "FIN": "bg-emerald-50 text-emerald-700 border-emerald-200",
    "GUR": "bg-amber-50 text-amber-700 border-amber-200",
    "ZON": "bg-indigo-50 text-indigo-700 border-indigo-200",
    "EDU": "bg-sky-50 text-sky-700 border-sky-200",
    "LAW": "bg-rose-50 text-rose-700 border-rose-200"
}

# FULL NAME DEFINITIONS
MINISTRY_NAMES = {
    "ADM": "Administrative",
    "FIN": "Finance",
    "GUR": "Guru Services",
    "ZON": "Zonal Services",
    "EDU": "Education",
    "LAW": "Legal & Justice"
}

MINISTRY_CODE_MAP = ["ADM", "FIN", "GUR", "ZON", "EDU", "LAW"]

# Global Data Stores
RESOLUTIONS: List[Dict] = []
RESOLUTION_META: Dict[str, Dict] = {}
REVERSE_LINKS: Dict[str, List[Dict]] = {}
NAV_TREE: Dict[str, List[int]] = {}

# --- 3. HELPERS ---
def clean_id_list(id_str):
    if not id_str or str(id_str).strip().lower() in ['nan', 'none', '']: return []
    return [x.strip() for x in re.split(r'[,;]', str(id_str)) if x.strip()]

def resolve_links(id_list_str, rel_type):
    links = []
    for rid in clean_id_list(id_list_str):
        rid_clean = str(rid).strip()
        meta = RESOLUTION_META.get(rid_clean)
        if meta:
            links.append({"id": rid_clean, "type": rel_type, "year": meta.get('year', 'N/A'), "date": meta.get('date', 'N/A')})
        else:
            links.append({"id": rid_clean, "type": rel_type, "year": "Ref", "date": "External"})
    return links

def get_era(year):
    try:
        y = int(year)
        return f"{int(y//10 * 10)}s" if y > 0 else "Unknown"
    except: return "Unknown"

# --- 4. DATA ENGINE (Pandas/Excel Version) ---
def load_data():
    global RESOLUTIONS, RESOLUTION_META, REVERSE_LINKS, NAV_TREE
    RESOLUTIONS = []
    RESOLUTION_META = {}
    REVERSE_LINKS = {}
    NAV_TREE = {}
    
    data_folder = "data"
    if not os.path.exists(data_folder): return

    files = [f for f in os.listdir(data_folder) if f.endswith('.xlsx')]
    if not files: return

    filepath = os.path.join(data_folder, files[0])
    
    try:
        df = pd.read_excel(filepath)
        df = df.fillna('')  

        for _, row in df.iterrows():
            res = {}
            res['Resolution_ID'] = str(row.get('Resolution_ID', "MISSING-ID")).strip()
            res['Full_Text'] = str(row.get('Full_Text', "")).strip()
            res['Title'] = str(row.get('Title', "Untitled")).strip()
            
            try: res['Year'] = int(float(row.get('Year', 0)))
            except: res['Year'] = 0
            
            res['Is_Active'] = str(row.get('Status', 'active')).lower() == 'active'
            res['Shelf'] = get_era(res['Year'])
            res['Section_Ministry'] = str(row.get('Section_Ministry', 'Uncategorized')).strip() or 'Uncategorized'
            res['Category'] = str(row.get('Category', 'General')).strip() or 'General'
            res['Scope'] = str(row.get('Scope', 'Global')).strip() or 'Global'
            res['Date_Passed'] = str(row.get('Date_Passed', res['Year'])).strip()
            
            res['Amends_IDs'] = str(row.get('Amends_IDs', ''))
            res['Repeals_IDs'] = str(row.get('Repeals_IDs', ''))

            # Assign Code
            code = res['Section_Ministry'].upper()
            res['Chapter_Code'] = code if code in MINISTRY_CODE_MAP else "ADM"

            RESOLUTIONS.append(res)
            RESOLUTION_META[res['Resolution_ID']] = {"year": res['Year'], "date": res['Date_Passed'], "title": res['Title']}
            
            for target in clean_id_list(res['Amends_IDs']):
                REVERSE_LINKS.setdefault(str(target).strip(), []).append(
                    {"type": "AMENDED BY", "source_id": res['Resolution_ID'], "date": res['Date_Passed']}
                )

        RESOLUTIONS.sort(key=lambda x: (-x['Year'], x['Resolution_ID']))
        
        eras = sorted(list(set(r['Shelf'] for r in RESOLUTIONS if r['Shelf'] != "Unknown")), reverse=True)
        for era in eras:
            years = sorted(list(set(r['Year'] for r in RESOLUTIONS if r['Shelf'] == era)), reverse=True)
            NAV_TREE[era] = years

    except Exception as e:
        print(f"❌ Load Error: {e}")

load_data()

# --- 5. ROUTES ---

@app.get("/")
async def home(request: Request):
    if not RESOLUTIONS: load_data()
    min_year = min((r['Year'] for r in RESOLUTIONS), default=0) if RESOLUTIONS else 0
    max_year = max((r['Year'] for r in RESOLUTIONS), default=0) if RESOLUTIONS else 0
    
    stats = {
        "count": len(RESOLUTIONS),
        "min_year": min_year,
        "max_year": max_year,
    }
    return templates.TemplateResponse("home.html", {"request": request, "stats": stats})

@app.get("/archive")
async def archive(request: Request, q: Optional[str] = None, ministry: Optional[str] = None, category: Optional[str] = None, scope: Optional[str] = None, year: Optional[str] = None):
    if not RESOLUTIONS: load_data()
    
    results = RESOLUTIONS
    if ministry: results = [r for r in results if r['Section_Ministry'] == ministry]
    if category: results = [r for r in results if r['Category'] == category]
    if scope: results = [r for r in results if r['Scope'] == scope]
    if year and year.isdigit(): results = [r for r in results if r['Year'] == int(year)]
    
    if q:
        q_lower = q.lower()
        results = [r for r in results if q_lower in r['Full_Text'].lower() or q_lower in r['Resolution_ID'].lower() or q_lower in r['Title'].lower()]

    unique_ministries = sorted(list(set(r['Section_Ministry'] for r in RESOLUTIONS)))
    unique_categories = sorted(list(set(r['Category'] for r in RESOLUTIONS)))
    unique_scopes = sorted(list(set(r['Scope'] for r in RESOLUTIONS)))

    return templates.TemplateResponse("archive.html", {
        "request": request, "results": results, "query": q, "nav": NAV_TREE,
        "ministries": unique_ministries, "categories": unique_categories, "scopes": unique_scopes,
        "selected_ministry": ministry, "selected_category": category, "selected_scope": scope, "selected_year": year,
        "cat_colors": CATEGORY_COLORS,
        "min_names": MINISTRY_NAMES  # Passing names here
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
        "min_names": MINISTRY_NAMES # Passing names here
    })