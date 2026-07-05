"""
Diagnostic: dump the real structure of a single case page so we can fix
verdict/defendant/location extraction properly instead of guessing.

Run this on a CONCLUDED case (has an actual date in verdict_result, e.g.
case_id 2217)

    pip install playwright beautifulsoup4
    playwright install chromium
    python diagnose_case.py 2217
"""

import sys

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE_URL = "https://sudbih.gov.ba"


def main():
    case_id = sys.argv[1] if len(sys.argv) > 1 else "2217"
    url = f"{BASE_URL}/Court/Case/{case_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print(f"Navigating to {url} ...")
        page.goto(url, wait_until="load", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(2500)

        html = page.content()
        with open(f"case_{case_id}.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Saved rendered HTML ({len(html)} chars) to case_{case_id}.html")

        page.screenshot(path=f"case_{case_id}.png", full_page=True)
        print(f"Saved screenshot to case_{case_id}.png")

        soup = BeautifulSoup(html, "html.parser")

        body_text = soup.get_text("\n", strip=True)
        lines = [l for l in body_text.split("\n") if l.strip()]
        print(f"\n--- Full visible page text ({len(lines)} non-empty lines) ---")
        for i, line in enumerate(lines):
            print(f"{i:4d}: {line}")

        print("\n--- Elements with suggestive class names ---")
        for cls_guess in ["timeline", "history", "postupak", "presuda", "odluka",
                           "tok", "verdict", "decision", "news", "vijest"]:
            matches = soup.select(f"[class*='{cls_guess}']")
            if matches:
                print(f"\nclass contains '{cls_guess}': {len(matches)} elements")
                for m in matches[:3]:
                    print(f"  <{m.name} class={m.get('class')}> "
                          f"text={m.get_text(' ', strip=True)[:150]!r}")

        browser.close()

    print(f"\nDone. Please send me:\n"
          f" 1) The full numbered text dump above\n"
          f" 2) case_{case_id}.png\n"
          f" 3) case_{case_id}.html (or first ~300 lines if huge)")


if __name__ == "__main__":
    main()