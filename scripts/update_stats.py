import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from html import unescape

URLS = ["https://rc150.org/en/profiles", "https://rc150.org/bn/profiles"]
HEADERS = {"User-Agent": "RC150-public-statistics-dashboard/1.0"}

def fetch_page(url):
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=25) as response:
        return response.read().decode("utf-8", errors="replace")

def extract_total(html):
    text = unescape(re.sub(r"<[^>]+>", " ", html))
    text = re.sub(r"\s+", " ", text)
    patterns = [
        r"([\d,]+)\s+Verified Participants",
        r"Showing\s+[\d,]+\s+of\s+([\d,]+)",
        r"ইতিমধ্যেই\s*([\d,০-৯]+)\s*জন সদস্যের নিবন্ধন সম্পন্ন হয়েছে",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            raw = match.group(1).translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")).replace(",", "")
            return int(raw)
    raise ValueError("Could not find a recognizable public registration total")

def main():
    last_error = None
    for url in URLS:
        try:
            html = fetch_page(url)
            total = extract_total(html)
            path = Path("stats.json")
            data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            data.update({
                "total": total,
                "department_count": None,
                "departments": [],
                "updated_at": datetime.now(timezone(timedelta(hours=6))).isoformat(timespec="seconds"),
                "source": url,
                "note": "মোট নিবন্ধনসংখ্যা মূল RC150 ওয়েবসাইট থেকে স্বয়ংক্রিয়ভাবে নেওয়া হয়েছে। প্রকাশ্য পেজে যাচাইযোগ্য বিভাগভিত্তিক মোট সংখ্যা পাওয়া না যাওয়ায় বিভাগভিত্তিক চার্ট ফাঁকা রাখা হয়েছে।"
            })
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Updated public total: {total} from {url}")
            return
        except Exception as exc:
            last_error = exc
            print(f"Could not read {url}: {exc}")
    raise SystemExit(f"All RC150 profile pages failed: {last_error}")

if __name__ == "__main__":
    main()
