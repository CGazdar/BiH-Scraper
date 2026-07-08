import os
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_DIR = os.path.join(BASE_DIR, "data", "cases_html")
TEXT_DIR = os.path.join(BASE_DIR, "data", "cases_text")

os.makedirs(TEXT_DIR, exist_ok=True)

def html_to_text(html):
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    # clean empty lines
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join([l for l in lines if l])

files = [f for f in os.listdir(HTML_DIR) if f.endswith(".html")]

for file in tqdm(files):
    case_id = file.replace(".html", "")
    out_path = os.path.join(TEXT_DIR, f"{case_id}.txt")

    if os.path.exists(out_path):
        continue

    with open(os.path.join(HTML_DIR, file), "r", encoding="utf-8") as f:
        html = f.read()

    text = html_to_text(html)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)