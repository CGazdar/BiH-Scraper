"""
Translate the Bosnian text fields in the scraped Sud BiH CSV into English.

SETUP
-----
    pip install deep-translator pandas

RUN
---
    python translate_csv.py sudbih_cases_department_1.csv
"""

import argparse
import sys
import time

import pandas as pd
from deep_translator import GoogleTranslator

DEFAULT_COLUMNS = ["case_name", "defendant_names", "crime_location", "verdict_result"]
LIST_COLUMNS = {"defendant_names", "crime_location", "year_of_crime", "num_victims"}

SOURCE_LANG = "bs"   
TARGET_LANG = "en"
SAVE_EVERY = 20       
MAX_RETRIES = 4


def translate_one(translator: GoogleTranslator, text: str, cache: dict) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if text in cache:
        return cache[text]

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = translator.translate(text)
            cache[text] = result or text
            return cache[text]
        except Exception as e:
            wait = attempt * 2
            print(f"    translate failed ({e}); retrying in {wait}s "
                  f"[{attempt}/{MAX_RETRIES}]")
            time.sleep(wait)

    print(f"    giving up on: {text[:60]!r} -- leaving untranslated")
    cache[text] = text
    return text


def translate_cell(translator: GoogleTranslator, value: str, cache: dict, is_list_col: bool) -> str:
    """Handles parsing and translating cell contents appropriately."""
    if not isinstance(value, str) or not value.strip():
        return ""
    
    if is_list_col:
        parts = [p.strip() for p in value.split(";") if p.strip()]
        translated_parts = [translate_one(translator, p, cache) for p in parts]
        return "; ".join(translated_parts)
    
    return translate_one(translator, value, cache)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", help="path to the scraped CSV")
    parser.add_argument("--columns", nargs="+", default=DEFAULT_COLUMNS,
                         help=f"columns to translate (default: {DEFAULT_COLUMNS})")
    parser.add_argument("--out", default=None,
                         help="output path (default: <input>_translated.csv)")
    parser.add_argument("--resume", action="store_true",
                         help="continue into an existing partially-translated output file")
    parser.add_argument("--delay", type=float, default=0.3,
                         help="seconds to sleep between translation calls")
    args = parser.parse_args()

    out_path = args.out or args.csv_path.rsplit(".csv", 1)[0] + "_translated.csv"

    if args.resume:
        try:
            df = pd.read_csv(out_path, encoding="utf-8-sig")
            print(f"Resuming from existing partial output: {out_path}")
        except FileNotFoundError:
            df = pd.read_csv(args.csv_path, encoding="utf-8-sig")
            print("No existing output found, starting fresh.")
    else:
        df = pd.read_csv(args.csv_path, encoding="utf-8-sig")

    missing = [c for c in args.columns if c not in df.columns]
    if missing:
        print(f"ERROR: these columns aren't in the CSV: {missing}")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)

    for col in args.columns:
        en_col = f"{col}_en"
        if en_col not in df.columns:
            df[en_col] = ""

    translator = GoogleTranslator(source=SOURCE_LANG, target=TARGET_LANG)
    cache: dict = {}

    total = len(df)
    for i, row in df.iterrows():
        already_done = all(
            bool(str(row.get(f"{col}_en", "")).strip()) or not str(row.get(col, "")).strip()
            for col in args.columns
        )
        if args.resume and already_done:
            continue

        print(f"[{i+1}/{total}] translating case {row.get('case_id', '?')} ...")
        for col in args.columns:
            en_col = f"{col}_en"
            is_list = col in LIST_COLUMNS
            df.at[i, en_col] = translate_cell(translator, str(row.get(col, "")), cache, is_list_col=is_list)
            time.sleep(args.delay)

        if (i + 1) % SAVE_EVERY == 0:
            df.to_csv(out_path, index=False, encoding="utf-8-sig")
            print(f"  ... progress saved ({i+1}/{total})")

    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\nDone. Translated CSV written to {out_path}")
    print(f"Unique phrases translated: {len(cache)}")


if __name__ == "__main__":
    main()