#!/usr/bin/env python3
"""Download champion portrait thumbnails from the Idle Champions Fandom Wiki."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
OUT = ROOT / "assets" / "champions"
WIKI = "https://idlechampions.fandom.com/wiki/Special:FilePath/"
HEADERS = {"User-Agent": "IdleChampionsHelper/1.0 (community fan project; portrait cache)"}


def slug(name):
    import unicodedata
    name = unicodedata.normalize("NFKD", name)
    name = "".join(ch for ch in name if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def names_from_index():
    html = INDEX.read_text(encoding="utf-8")
    raw = re.search(r"const raw = \[(.*?)\];", html, re.S)
    if not raw:
        raise RuntimeError("Could not find champion list in index.html")
    entries = re.findall(r'"([^"\n]*\|\d+\|[^"\n]*)"', raw.group(1))
    names = []
    for entry in entries:
        name = entry.split("|", 1)[0].strip()
        if name and name not in names:
            names.append(name)
    return names


def candidates(name):
    return [
        f"{name} Portrait.png",
        f"{name}.png",
        f"{name} Head.png",
        f"Champion {name}.png",
        f"Icon {name}.png",
        f"{name} Standard.png",
    ]


def download_one(name):
    target = OUT / f"{slug(name)}.png"
    if target.exists() and target.stat().st_size > 500:
        return name, "cached"
    for filename in candidates(name):
        url = WIKI + quote(filename, safe="")
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=18) as response:
                content_type = response.headers.get("Content-Type", "").lower()
                data = response.read()
            if not content_type.startswith("image/") or len(data) < 500:
                continue
            try:
                with Image.open(BytesIO(data)) as original:
                    original.seek(0)
                    image = original.convert("RGBA")
                    image = ImageOps.fit(image, (160, 160), method=Image.Resampling.LANCZOS, centering=(0.5, 0.42))
                    buffer = BytesIO()
                    image.save(buffer, format="PNG", optimize=True)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(buffer.getvalue())
                time.sleep(0.08)
                return name, f"downloaded ({filename})"
            except Exception:
                continue
        except (HTTPError, URLError, TimeoutError, OSError):
            continue
    return name, "not found"


def main():
    names = names_from_index()
    print(f"Found {len(names)} champions.")
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(download_one, name) for name in names]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"{result[0]}: {result[1]}")
    ok = sum(status.startswith(("downloaded", "cached")) for _, status in results)
    missing = [name for name, status in results if status == "not found"]
    print(f"\nCached portraits: {ok}/{len(names)}; missing: {len(missing)}")
    if missing:
        print("Missing: " + ", ".join(missing))
    if ok == 0:
        raise SystemExit("No portraits downloaded; refusing to commit an empty cache.")


if __name__ == "__main__":
    main()
