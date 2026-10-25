#!/usr/bin/env python3
"""Inspect publicly accessible RC150 profile pages without an AI/API key.

This is bounded reconnaissance only. It does not log in, bypass access controls,
submit forms, or enumerate private records. It records public HTML and same-site
JavaScript evidence for a human/agent to inspect.
"""
from __future__ import annotations

import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

BASE_URLS = [
    "https://rc150.org/bn/profiles",
    "https://rc150.org/en/profiles",
]
HEADERS = {
    "User-Agent": "RC150-Public-Recon/1.0 (+https://github.com/natchplaize-oss/rc150)",
    "Accept-Language": "bn,en;q=0.9",
}
OUT = Path("recon-report")
MAX_BYTES = 2_000_000
MAX_ASSETS = 15
PAUSE_SECONDS = 0.35


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.forms = []
        self.controls = []
        self.links = []
        self._form = None
        self._select = None
        self._active_option_index = None
        self._active_link_index = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and a.get("src"):
            self.scripts.append(a["src"])
        if tag == "form":
            self._form = {"action": a.get("action", ""), "method": a.get("method", "get").upper()}
            self.forms.append(self._form)
        if tag == "select":
            self._select = {"name": a.get("name", ""), "id": a.get("id", ""), "options": []}
            self.controls.append(self._select)
        if tag == "option" and self._select is not None:
            self._select["options"].append({"value": a.get("value", ""), "label": ""})
            self._active_option_index = len(self._select["options"]) - 1
        if tag in ("input", "button"):
            self.controls.append({
                "tag": tag, "type": a.get("type", ""), "name": a.get("name", ""),
                "id": a.get("id", ""), "placeholder": a.get("placeholder", ""),
                "aria_label": a.get("aria-label", ""),
            })
        if tag == "a" and a.get("href"):
            self.links.append({"href": a["href"], "label": ""})
            self._active_link_index = len(self.links) - 1

    def handle_data(self, data):
        text = " ".join(data.split())
        if not text:
            return
        if self._select is not None and self._active_option_index is not None:
            option = self._select["options"][self._active_option_index]
            option["label"] = f"{option['label']} {text}".strip()
        if self._active_link_index is not None:
            link = self.links[self._active_link_index]
            link["label"] = f"{link['label']} {text}".strip()

    def handle_endtag(self, tag):
        if tag == "a":
            self._active_link_index = None
        elif tag == "option":
            self._active_option_index = None
        elif tag == "select":
            self._select = None
            self._active_option_index = None
        elif tag == "form":
            self._form = None


def fetch(url):
    request = Request(url, headers=HEADERS)
    with urlopen(request, timeout=20) as response:
        data = response.read(MAX_BYTES + 1)
        return {
            "requested_url": url,
            "final_url": response.geturl(),
            "status": getattr(response, "status", 200),
            "content_type": response.headers.get("Content-Type", ""),
            "truncated": len(data) > MAX_BYTES,
            "body": data[:MAX_BYTES],
        }


def write_text(path, value):
    path.write_text(value, encoding="utf-8", errors="replace")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "scope": "Public pages and same-site JavaScript assets only; no login or form submission.",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pages": [],
        "javascript_assets": [],
        "endpoint_candidates": [],
        "errors": [],
    }
    asset_urls = []
    site_hosts = {"rc150.org", "www.rc150.org"}

    for index, url in enumerate(BASE_URLS):
        try:
            result = fetch(url)
            time.sleep(PAUSE_SECONDS)
            page_path = OUT / f"profile-{index}.html"
            page_path.write_bytes(result.pop("body"))
            parser = PageParser()
            html = page_path.read_text(encoding="utf-8", errors="replace")
            parser.feed(html)
            page_info = {
                **result,
                "saved_file": page_path.name,
                "forms": parser.forms,
                "controls": parser.controls,
                "links_sample": parser.links[:150],
                "script_sources": parser.scripts,
            }
            report["pages"].append(page_info)
            for source in parser.scripts:
                absolute = urljoin(result["final_url"], source)
                if urlparse(absolute).netloc in site_hosts and absolute not in asset_urls:
                    asset_urls.append(absolute)
        except Exception as exc:
            report["errors"].append({"url": url, "error": f"{type(exc).__name__}: {exc}"})

    # Inspect bounded, publicly served first-party JavaScript only.
    for index, url in enumerate(asset_urls[:MAX_ASSETS]):
        try:
            result = fetch(url)
            time.sleep(PAUSE_SECONDS)
            body = result.pop("body")
            filename = f"asset-{index:02d}.js"
            write_text(OUT / filename, body.decode("utf-8", "replace"))
            report["javascript_assets"].append({**result, "saved_file": filename})
            source = body.decode("utf-8", "replace")
            # These are leads for review, not proof that an endpoint is usable.
            patterns = [
                r"""https?://[^\s"'<>]+""",
                r"""(?:fetch|axios\.(?:get|post)|\.get|\.post)\s*\(\s*['"`]([^'"`]+)""",
                r"""['"`](/(?:api|graphql|ajax|bn|en)/[^'"` ]{1,240})['"`]""",
                r"""(?:page|per_page|perPage|pagination|department|faculty|group|search|filter)""",
            ]
            for pattern in patterns:
                for match in re.finditer(pattern, source, re.I):
                    value = match.group(0)[:400]
                    report["endpoint_candidates"].append({
                        "asset": filename, "pattern": pattern, "match": value
                    })
        except Exception as exc:
            report["errors"].append({"url": url, "error": f"{type(exc).__name__}: {exc}"})

    # Keep the evidence report readable and avoid duplicate candidate lines.
    seen = set()
    unique = []
    for item in report["endpoint_candidates"]:
        key = (item["asset"], item["match"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    report["endpoint_candidates"] = unique[:500]
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# RC150 public-site reconnaissance",
        "",
        f"- Captured (UTC): {report['captured_at_utc']}",
        "- Scope: public pages and same-site JavaScript only. No authentication, form submissions, or access-control bypass.",
        f"- Pages captured: {len(report['pages'])}",
        f"- JavaScript assets captured: {len(report['javascript_assets'])}",
        f"- Endpoint/code leads: {len(report['endpoint_candidates'])} (not verified API endpoints)",
        f"- Errors: {len(report['errors'])}",
        "",
        "## Pages, forms and controls",
    ]
    for page in report["pages"]:
        lines += [
            f"### {page['requested_url']}",
            f"- Final URL: {page['final_url']}",
            f"- HTTP status: {page['status']}; content type: {page['content_type']}",
            f"- Forms: {json.dumps(page['forms'], ensure_ascii=False)}",
            f"- Controls: {json.dumps(page['controls'], ensure_ascii=False)}",
            f"- Script sources: {json.dumps(page['script_sources'], ensure_ascii=False)}",
            "",
        ]
    lines += ["## Candidate strings for manual verification", ""]
    lines += [f"- `{x['asset']}`: `{x['match']}`" for x in unique[:100]]
    lines += ["", "These strings are search leads only. Confirm endpoint behavior and response schema before using them."]
    if report["errors"]:
        lines += ["", "## Errors", ""]
        lines += [f"- {x['url']}: {x['error']}" for x in report["errors"]]
    write_text(OUT / "report.md", "\n".join(lines) + "\n")
    print(f"Recon complete: {len(report['pages'])} pages, {len(report['javascript_assets'])} JS assets, {len(unique)} candidate strings.")
    if not report["pages"]:
        raise SystemExit("No public page could be captured; inspect report.json errors.")


if __name__ == "__main__":
    main()
