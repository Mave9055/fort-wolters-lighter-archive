"""Check internal GitHub Pages links for fort-wolters."""
from __future__ import annotations

import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE = "https://daniel-lingar.github.io/fort-wolters/"
ROOT = Path(__file__).resolve().parents[1]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "a" and attr_map.get("href"):
            self.links.append(("href", attr_map["href"]))
        elif tag == "img" and attr_map.get("src"):
            self.links.append(("src", attr_map["src"]))


def normalize(url: str, page_url: str) -> str | None:
    url = url.strip()
    if not url or url.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return urllib.parse.urljoin(page_url, url)


def check(url: str) -> int | str:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "fw-link-check/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        if exc.code in {403, 405}:
            req = urllib.request.Request(url, headers={"User-Agent": "fw-link-check/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.status
        return exc.code
    except Exception as exc:  # noqa: BLE001
        return str(exc)


def main() -> int:
    seen: set[str] = set()
    internal: list[tuple[str, str, str]] = []
    broken: list[tuple[str, str, str, object]] = []

    for html_file in sorted(ROOT.glob("*.html")):
        rel = html_file.name
        page_url = urllib.parse.urljoin(BASE, rel)
        parser = LinkParser()
        parser.feed(html_file.read_text(encoding="utf-8", errors="replace"))
        for kind, raw in parser.links:
            resolved = normalize(raw, page_url)
            if not resolved or "daniel-lingar.github.io/fort-wolters" not in resolved:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            internal.append((rel, kind, resolved))

    print(f"Checking {len(internal)} internal links...\n")
    for source, kind, url in sorted(internal):
        status = check(url)
        ok = isinstance(status, int) and status < 400
        print(f"[{'OK' if ok else 'FAIL'}] {status} {kind} {url}\n    from {source}")
        if not ok:
            broken.append((source, kind, url, status))

    print(f"\nSummary: {len(internal) - len(broken)}/{len(internal)} OK")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())