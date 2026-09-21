#!/usr/bin/env python3
"""Generate placeholder photos + content JSON for a trip that doesn't have real photos yet.

Usage: scripts/placeholders.py <slug> "<Title>" "<Subtitle>" "Section A" "Section B" ...
       scripts/placeholders.py <slug> --itinerary content/<slug>.itinerary.json
         (itinerary: {title, subtitle, days: [{date, name, stops[]}]} → one section per day)

Writes public/assets/<slug>/NNN-{1600,800}.webp + NNN-24.jpg and content/<slug>.json in the same
shape harvest.py produces, so the page renders now and real photos can replace the files later.
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
TONES = ["#c9b8a8", "#a8b5c9", "#b8c9a8", "#c9a8b8", "#d9cdb8", "#a8c9c4"]
SHAPES = [(3, 2), (2, 3), (4, 5), (16, 9), (1, 1), (3, 2)]

def make(out: Path, n: int, label: str):
    aw, ah = SHAPES[n % len(SHAPES)]
    w, h = 1600, int(1600 * ah / aw)
    im = Image.new("RGB", (w, h), TONES[n % len(TONES)])
    d = ImageDraw.Draw(im)
    d.text((w / 2, h / 2), f"{label} · {n:03d}", fill=(60, 55, 50), anchor="mm", font_size=64)
    im.save(out / f"{n:03d}-1600.webp", "WEBP", quality=80)
    s = im.copy(); s.thumbnail((800, 800)); s.save(out / f"{n:03d}-800.webp", "WEBP", quality=80)
    p = im.copy(); p.thumbnail((24, 24)); p.save(out / f"{n:03d}-24.jpg", "JPEG", quality=50)
    return {"id": f"placeholder-{n}", "file": f"{n:03d}", "w": w, "h": h}

def main(slug, title, subtitle, sections, grid=3, carousel=5):
    """sections: list of (heading, subtitle, text[])"""
    out = ROOT / "public" / "assets" / slug
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*"):
        old.unlink()
    n = 0
    def batch(k):
        nonlocal n
        imgs = []
        for _ in range(k):
            n += 1
            imgs.append(make(out, n, slug))
        return imgs
    doc = {
        "title": title, "subtitle": subtitle, "placeholder": True,
        "hero": [{"type": "grid", "images": batch(1)}],
        "sections": [
            {"heading": h, "subtitle": sub, "text": text, "blocks": [
                {"type": "grid", "images": batch(grid)},
                {"type": "carousel", "images": batch(carousel)},
            ]} for h, sub, text in sections
        ],
        "source": None,
    }
    (ROOT / "content" / f"{slug}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    print(f"{slug}: {n} placeholder images, {len(sections)} sections")

if __name__ == "__main__":
    slug, *rest = sys.argv[1:]
    if rest[:1] == ["--itinerary"]:
        it = json.loads(Path(rest[1]).read_text())
        main(slug, it["title"], it["subtitle"],
             [(d["name"], d["date"], d["stops"]) for d in it["days"]], grid=2, carousel=4)
    else:
        title, subtitle, *heads = rest
        main(slug, title, subtitle, [(h, None, []) for h in heads])
