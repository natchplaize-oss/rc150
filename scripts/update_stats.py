import json
import re
from datetime import datetime, timezone, timedelta
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen

# Prefer the official homepage because it publishes the public aggregate count.
URLS = [
    "https://www.rc150.org/bn",
    "https://rc150.org/bn",
    "https://www.rc150.org/en/profiles",
    "https://rc150.org/en/profiles",
    "https://www.rc150.org/bn/profiles",
    "https://rc150.org/bn/profiles",
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RC150-Public-Statistics/1.0)",
    "Accept-Language": "bn,en;q=0.9",
}

DEPARTMENTS = [
    "বাংলা",
    "ইংরেজি",
    "আরবি ও ইসলামিক স্টাডিজ",
    "সংস্কৃত",
    "উর্দু",
    "ইতিহাস",
    "ইসলামের ইতিহাস ও সংস্কৃতি",
    "দর্শন",
    "রাষ্ট্রবিজ্ঞান",
    "সমাজবিজ্ঞান",
    "সমাজকর্ম",
    "অর্থনীতি",
    "পদার্থবিজ্ঞান",
    "রসায়ন",
    "গণিত",
    "উদ্ভিদবিজ্ঞান",
    "প্রাণিবিদ্যা",
    "মনোবিজ্ঞান",
    "পরিসংখ্যান",
    "ভূগোল ও পরিবেশ",
    "মার্কেটিং",
    "ফিন্যান্স ও ব্যাংকিং",
    "হিসাববিজ্ঞান",
    "ব্যবস্থাপনা"
]

BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def fetch_page(url):
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=25) as response:
        return response.read().decode("utf-8", errors="replace")


def visible_text(html):
    # Drop script/style blocks first so unrelated embedded code cannot be mistaken for page text.
    html = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html, flags=re.I | re.S)
    text = unescape(re.sub(r"<[^>]+>", " ", html))
    return re.sub(r"\s+", " ", text)


def parse_count(raw):
    raw = raw.translate(BN_DIGITS).replace(",", "").replace("٬", "").strip()
    return int(raw)


def extract_total(html):
    text = visible_text(html)
    patterns = [
        r"ইতিমধ্যেই\s*([\d,০-৯٬]+)\s*জন সদস্যের নিবন্ধন সম্পন্ন হয়েছে",
        r"ইতিমধ্যেই\s*([\d,০-৯٬]+)\s*জন সদস্যের নিবন্ধন সম্পন্ন হয়েছে",
        r"([\d,]+)\s+Verified Participants",
        r"Showing\s+[\d,]+\s+of\s+([\d,]+)",
        r"([\d,০-৯٬]+)\s*(?:জন\s*)?(?:সদস্য|অংশগ্রহণকারী)\s*(?:নিবন্ধন সম্পন্ন|নিবন্ধিত)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return parse_count(match.group(1))
    raise ValueError("Could not find a recognizable public registration total")


def main():
    last_error = None
    for url in URLS:
        try:
            html = fetch_page(url)
            total = extract_total(html)
            path = Path("stats.json")
            data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            now = datetime.now(timezone(timedelta(hours=6))).isoformat(timespec="seconds")
            old_total = data.get("total")
            data.update({
                "total": total,
                # Department aggregates are intentionally left empty until they can be
                # derived and verified from the official public profiles data.
                "department_count": len(DEPARTMENTS),
                "departments": [{"name": name, "count": None} for name in DEPARTMENTS],
                "updated_at": now,
                "source": url,
                "total_changed_at": now if old_total != total else data.get("total_changed_at", now),
                "note": (
                    "মোট নিবন্ধনসংখ্যা মূল RC150 ওয়েবসাইটের প্রকাশ্য পেজ থেকে স্বয়ংক্রিয়ভাবে নেওয়া হয়েছে। "
                    "রাজশাহী কলেজের অফিসিয়াল বিভাগ তালিকা যোগ করা হয়েছে। বিভাগভিত্তিক নিবন্ধনসংখ্যা এখনো যাচাই করা হয়নি।"
                ),
            })
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Updated public total: {total} from {url}")
            return
        except Exception as exc:
            last_error = exc
            print(f"Could not read {url}: {exc}")
    raise SystemExit(f"All RC150 public pages failed; existing stats.json was preserved. Last error: {last_error}")


if __name__ == "__main__":
    main()
