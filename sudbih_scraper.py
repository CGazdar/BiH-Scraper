"""
Sud BiH (sudbih.gov.ba) war-crimes case scraper
================================================

Scrapes the public case-law listing (Court/Practice) and each individual
case page (Court/Case/{id}) into a single CSV, with one row for each case.

SETUP
-----
    pip install playwright beautifulsoup4 pandas
    playwright install chromium

RUN
---
    python sudbih_scraper.py --department 1
    python sudbih_scraper.py --department 1 --resume     
    python sudbih_scraper.py --department 1 --headful    

OUTPUT
------
    sudbih_cases_department_{N}.csv

"""

import argparse
import csv
import os
import re
import sys
import time
from dataclasses import dataclass, field

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE_URL = "https://sudbih.gov.ba"
LISTING_URL = "{base}/Court/Practice?Department={dept}"
CASE_URL_RE = re.compile(r"/Court/Case/(\d+)")

FIELD_LABELS = {
    "defendant": ["Optuženi", "Optužena", "Optuženi/na"],
    "location": ["Mjesto učinjenja", "Mjesto izvršenja"],
    "year": ["Vrijeme učinjenja", "Vrijeme izvršenja"],
    "victims": ["Broj oštećenih", "Broj žrtava"],
    "num_indicted": ["Broj optuženih"],
    "verdict": ["Presuda/Odluka", "Presuda", "Odluka"],
    "case_number": ["Broj predmeta"],
}


@dataclass
class CaseRow:
    case_id: str
    case_number: str = ""
    case_name: str = ""
    num_indicted: str = ""
    defendant_names: str = ""
    year_of_crime: str = ""
    num_victims: str = ""
    crime_location: str = ""
    verdict_result: str = ""


def _safe_goto(page, url: str):
    """
    Navigate robustly. This site never truly reaches Playwright's
    'networkidle' state (confirmed via diagnostics -- some background
    script keeps polling), so we use 'load' + a short best-effort wait
    instead of relying on networkidle, which was throwing an unhandled
    TimeoutError and killing the scraper before it could read anything.
    """
    page.goto(url, wait_until="load", timeout=30000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass 
    page.wait_for_timeout(2000)


def discover_case_links(page, department: int) -> list[tuple[str, str, str]]:
    """
    Returns a list of (case_id, case_name, case_number).

    Confirmed via diagnostics: all case links for a department are plain
    <a href="/Court/Case/{id}"> tags present on the single listing page
    (no pagination needed -- 554/554 found on first load for Department 1).
    We still do one "scroll + wait" pass in case any cases are lazy-loaded
    further down the page, but no click-through pagination is required.
    """
    url = LISTING_URL.format(base=BASE_URL, dept=department)
    _safe_goto(page, url)

    page.mouse.wheel(0, 20000)
    page.wait_for_timeout(1500)

    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    found = {}
    links = soup.select("a[href*='/Court/Case/']")
    for a in links:
        href = a.get("href", "")
        m = CASE_URL_RE.search(href)
        if not m:
            continue
        case_id = m.group(1)
        text = a.get_text(strip=True)
        if text or case_id not in found:
            found[case_id] = text

    print(f"  Found {len(found)} unique case links on the listing page.")

    results = []
    for case_id, text in found.items():
        m = re.search(r"(S\d[\s\S]*)$", text)
        case_number = m.group(1).strip() if m else ""
        case_name = text.replace(case_number, "").strip() if case_number else text
        results.append((case_id, case_name, case_number))
    return results


def extract_field(soup: BeautifulSoup, labels: list[str]) -> str:
    """Find a known Bosnian label on the page and return the text right after it."""
    body_text = soup.get_text("\n", strip=True)
    lines = body_text.split("\n")
    for i, line in enumerate(lines):
        for label in labels:
            if label.lower() in line.lower():
                if ":" in line:
                    after = line.split(":", 1)[1].strip()
                    if after:
                        return after
                if i + 1 < len(lines):
                    return lines[i + 1].strip()
    return ""


def scrape_case(page, case_id: str) -> CaseRow:
    url = f"{BASE_URL}/Court/Case/{case_id}"
    _safe_goto(page, url)
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    row = CaseRow(case_id=case_id)
    row.case_number = extract_field(soup, FIELD_LABELS["case_number"])

    title = soup.find(["h1", "h2"])
    title_text = title.get_text(strip=True) if title else ""

    if row.case_number and title_text.startswith(row.case_number):
        title_text = title_text[len(row.case_number):].strip()
    row.case_name = title_text

    def extract_all(labels):
        body_text = soup.get_text("\n", strip=True)
        lines = body_text.split("\n")
        vals = []
        for i, line in enumerate(lines):
            for label in labels:
                if label.lower() in line.lower():
                    if ":" in line:
                        after = line.split(":", 1)[1].strip()
                        if after:
                            vals.append(after)
                            continue
                    if i + 1 < len(lines):
                        vals.append(lines[i + 1].strip())
        seen = set()
        out = []
        for v in vals:
            if v and v not in seen:
                seen.add(v)
                out.append(v)
        return out

    row.defendant_names = "; ".join(extract_all(FIELD_LABELS["defendant"]))
    row.crime_location = "; ".join(extract_all(FIELD_LABELS["location"]))
    row.year_of_crime = "; ".join(extract_all(FIELD_LABELS["year"]))
    row.num_victims = "; ".join(extract_all(FIELD_LABELS["victims"]))

    num_indicted = extract_field(soup, FIELD_LABELS["num_indicted"])
    if not num_indicted and row.defendant_names:
        num_indicted = str(len(row.defendant_names.split(";")))
    row.num_indicted = num_indicted

# --- DYNAMIC TEXT-BASED VERDICT EXTRACTION ---
    body_text = soup.get_text("\n", strip=True)
    lines = [line.strip() for line in body_text.split("\n") if line.strip()]
    
    verdict_text = "there is no information about the verdict"
    
    section_index = -1
    for idx, line in enumerate(lines):
        if re.search(r"izvr(š|s)enje", line, re.IGNORECASE):
            section_index = idx
            break
            
    if section_index != -1:
        # We scan a window of 30 lines ahead of the section header
        search_window = lines[section_index : section_index + 30]
        
        for i, line in enumerate(search_window):
            if "ostvarena protivpravna korist" in line.lower():
                if ":" in line and line.split(":", 1)[1].strip():
                    verdict_text = line
                elif i + 1 < len(search_window):
                    next_line = search_window[i + 1]
                    base_label = line.split(":")[0].strip()
                    verdict_text = f"{base_label}: {next_line}"
                else:
                    verdict_text = line
                break
                
    row.verdict_result = verdict_text
    # ----------------------------------------------

    return row

    row.defendant_names = "; ".join(extract_all(FIELD_LABELS["defendant"]))
    row.crime_location = "; ".join(extract_all(FIELD_LABELS["location"]))
    row.year_of_crime = "; ".join(extract_all(FIELD_LABELS["year"]))
    row.num_victims = "; ".join(extract_all(FIELD_LABELS["victims"]))

    num_indicted = extract_field(soup, FIELD_LABELS["num_indicted"])
    if not num_indicted and row.defendant_names:
        num_indicted = str(len(row.defendant_names.split(";")))
    row.num_indicted = num_indicted

    verdicts = extract_all(FIELD_LABELS["verdict"])
    row.verdict_result = verdicts[-1] if verdicts else ""

    return row


def load_existing_ids(csv_path: str) -> set:
    if not os.path.exists(csv_path):
        return set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        return {r["case_id"] for r in csv.DictReader(f)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--department", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--headful", action="store_true", help="show the browser window")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between case fetches")
    args = parser.parse_args()

    csv_path = f"sudbih_cases_department_{args.department}.csv"
    fieldnames = list(CaseRow.__dataclass_fields__.keys())

    write_header = not (args.resume and os.path.exists(csv_path))
    existing_ids = load_existing_ids(csv_path) if args.resume else set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful)
        page = browser.new_page()

        print(f"Discovering case links for Department {args.department} ...")
        cases = discover_case_links(page, args.department)
        print(f"Found {len(cases)} cases in the listing.\n")

        mode = "a" if (args.resume and not write_header) else "w"
        with open(csv_path, mode, newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()

            for i, (case_id, case_name, case_number) in enumerate(cases, 1):
                if case_id in existing_ids:
                    continue
                print(f"[{i}/{len(cases)}] scraping case {case_id} ({case_name}) ...")
                try:
                    row = scrape_case(page, case_id)
                    if not row.case_name:
                        row.case_name = case_name
                    if not row.case_number:
                        row.case_number = case_number
                    writer.writerow(row.__dict__)
                    f.flush()
                except Exception as e:
                    print(f"  !! failed on case {case_id}: {e}")
                time.sleep(args.delay)

        browser.close()

    print(f"\nDone. Output written to {csv_path}")


if __name__ == "__main__":
    main()