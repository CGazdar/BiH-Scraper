import os
import json
from tqdm import tqdm
import ollama

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEXT_DIR = os.path.join(BASE_DIR, "data", "cases_text")
OUT_DIR = os.path.join(BASE_DIR, "data", "json")

os.makedirs(OUT_DIR, exist_ok=True)

def extract_fields(text, case_id):
    prompt = f"""
You are extracting structured data from Bosnian court judgments.

Return ONLY valid JSON.

FIELDS:
- case_id
- case_number
- defendant_name
- indicted_people
- crime_year
- victims
- crime_location
- verdict

RULES:
- If missing, use null
- crime_year must be a number or null
- victims and indicted_people must be integers or null
- verdict must be short (e.g. Guilty, Acquitted, Partially Guilty)

TEXT:
{text}
"""

    response = ollama.chat(
        model="llama3.1:8b",
        messages=[{"role": "user", "content": prompt}]
    )

    content = response["message"]["content"]

    try:
        return json.loads(content)
    except Exception:
        return {
            "case_id": case_id,
            "error": "parse_failed"
        }

files = [f for f in os.listdir(TEXT_DIR) if f.endswith(".txt")]

for file in tqdm(files):
    case_id = file.replace(".txt", "")
    out_path = os.path.join(OUT_DIR, f"{case_id}.json")

    if os.path.exists(out_path):
        continue

    with open(os.path.join(TEXT_DIR, file), "r", encoding="utf-8") as f:
        text = f.read()

    result = extract_fields(text, case_id)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)