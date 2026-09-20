#!/usr/bin/env python3
"""Pull content out of the published Google Sites pages.

For each trip:
  _import/<trip>.html            raw snapshot of the page
  _import/originals/<trip>/      full-size downloads (gitignored)
  assets/<trip>/<nnn>-1600.webp  web size
  assets/<trip>/<nnn>-800.webp   phone size
  assets/<trip>/<nnn>-24.jpg     blur placeholder
  content/<trip>.json            page structure: sections, grids, carousels, image order

Usage: scripts/harvest.py [trip ...]   (default: all)
"""
import html, json, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SITES = {
    "japan":     "https://sites.google.com/view/2024-holiday-in-japan/home",
    "seattle":   "https://sites.google.com/view/seattle-summer-2024/home",
    "southwest": "https://sites.google.com/view/2021summerinthesouthwest/home",
    "london":    "https://sites.google.com/view/2022summerinlondon/2022-london-trip",
}
IMG = "https://sites.google.com/sitesv-images-rt/"
SIZES = [1600, 800]
UA = {"User-Agent": "Mozilla/5.0"}


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


def clean(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def parse(page):
    """Walk the main content in document order and build sections."""
    main = page[page.find('role="main"'):]
    tokens = re.finditer(
        r'<h([1-6])[^>]*>(.*?)</h\1>'           # heading
        r'|aria-label="Image carousel"'           # carousel start
        r'|sitesv-images-rt/([A-Za-z0-9_-]+)'    # image
        r'|<p [^>]*>(.*?)</p>',                   # paragraph
        main, re.S)
    doc = {"title": None, "subtitle": None, "hero": [], "sections": []}
    cur = None            # current section
    block = None          # current image block within section
    seen = set()

    def new_block(kind):
        nonlocal block
        block = {"type": kind, "images": []}
        (cur["blocks"] if cur else doc["hero"]).append(block)

    for t in tokens:
        if t.group(2) is not None:
            text = clean(t.group(2))
            if not text:
                continue
            if doc["title"] is None:
                doc["title"] = text
            else:
                cur = {"heading": text, "subtitle": None, "text": [], "blocks": []}
                doc["sections"].append(cur)
            block = None
        elif t.group(3):
            if t.group(3) in seen:
                continue
            seen.add(t.group(3))
            if block is None:
                new_block("grid")
            block["images"].append(t.group(3))
        elif t.group(4) is not None:
            text = clean(t.group(4))
            if not text:
                continue
            if cur is None:
                doc["subtitle"] = doc["subtitle"] or text
            elif cur["subtitle"] is None and not cur["blocks"]:
                cur["subtitle"] = text
            else:
                cur["text"].append(text)
        else:
            new_block("carousel")
    # hero blocks when the page has no leading images
    doc["hero"] = [b for b in doc["hero"] if b["images"]]
    return doc


def process(trip, idx, image_id, orig_dir, out_dir):
    src = orig_dir / f"{idx:03d}.jpg"
    if not src.exists():
        src.write_bytes(fetch(f"{IMG}{image_id}=w2400"))
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    w, h = im.size
    for s in SIZES:
        dst = out_dir / f"{idx:03d}-{s}.webp"
        if not dst.exists():
            r = im.copy(); r.thumbnail((s, s))
            r.save(dst, "WEBP", quality=82, method=6)
    ph = out_dir / f"{idx:03d}-24.jpg"
    if not ph.exists():
        r = im.copy(); r.thumbnail((24, 24))
        r.save(ph, "JPEG", quality=50)
    return {"id": image_id, "file": f"{idx:03d}", "w": w, "h": h}


def harvest(trip):
    url = SITES[trip]
    snap = ROOT / "_import" / f"{trip}.html"
    snap.parent.mkdir(exist_ok=True)
    if not snap.exists():
        snap.write_bytes(fetch(url))
    doc = parse(snap.read_text())
    doc["source"] = url

    ids = [i for b in doc["hero"] for i in b["images"]] + \
          [i for s in doc["sections"] for b in s["blocks"] for i in b["images"]]
    orig_dir = ROOT / "_import" / "originals" / trip
    out_dir = ROOT / "assets" / trip
    orig_dir.mkdir(parents=True, exist_ok=True); out_dir.mkdir(parents=True, exist_ok=True)

    print(f"{trip}: {len(doc['sections'])} sections, {len(ids)} images")
    with ThreadPoolExecutor(8) as ex:
        meta = list(ex.map(lambda a: process(trip, *a, orig_dir, out_dir), enumerate(ids, 1)))
    lookup = {m["id"]: m for m in meta}
    for b in doc["hero"] + [b for s in doc["sections"] for b in s["blocks"]]:
        b["images"] = [lookup[i] for i in b["images"]]
    (ROOT / "content").mkdir(exist_ok=True)
    (ROOT / "content" / f"{trip}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    for trip in (sys.argv[1:] or SITES):
        harvest(trip)
