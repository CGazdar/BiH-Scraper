import os
import json
import time
import requests
from tqdm import tqdm

BASE_URL = "https://sudbih.gov.ba/Court/Case/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0 Safari/537.36"
    )
}

# ---- FIXED PATH HANDLING ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CASE_FILE = os.path.join(BASE_DIR, "practice_scraper", "case_ids.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "cases_html")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---- LOAD CASE IDS ----
with open(CASE_FILE, "r") as f:
    case_ids = json.load(f)

def download_case(case_id):
    url = BASE_URL + str(case_id)

    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()

    path = os.path.join(OUTPUT_DIR, f"{case_id}.html")

    with open(path, "w", encoding="utf-8") as f:
        f.write(r.text)

# ---- RUN DOWNLOAD ----
for cid in tqdm(case_ids):
    path = os.path.join(OUTPUT_DIR, f"{cid}.html")

    # skip if already downloaded (resume-safe)
    if os.path.exists(path):
        continue

    try:
        download_case(cid)
        time.sleep(0.5)  # polite delay
    except Exception as e:
        print(f"Failed {cid}: {e}")