#!/usr/bin/env python3
"""Build a trip from a local folder of phone photos, using EXIF time + GPS.

  scripts/import_local.py <slug> <photo-dir>

Reads, all in content/:
  <slug>.itinerary.json   {title, subtitle, map?, days: [{date: "September 6", name, stops[]}]} → one section per day
                          (map: name of an outline in src/maps/, shown in the lightbox)
  <slug>.places.json      gazetteer: [{name, lat, lon, radius?, after?, before?}] — photos are labelled
                          with the nearest place in range
  <slug>.overrides.json   {hero?, rejected?: [name], files: {name: "skip" | {when?, place?}}} — fixes for
                          bad/missing EXIF; `rejected` is maintained by scripts/review.py

Photos with no GPS borrow the place of the nearest-in-time GPS photo that day (two phones, one with
location off). Consecutive photos at the same place become one captioned block in the day's section.

Writes public/assets/<slug>/NNN-{1600,800}.webp + NNN-24.jpg (no EXIF — locations are NOT published)
and content/<slug>.json. Videos are skipped.
"""
import json, math, re, subprocess, sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()
ROOT = Path(__file__).resolve().parent.parent
PHOTO_EXT = {".heic", ".jpg", ".jpeg", ".png"}
BORROW_WINDOW = timedelta(minutes=45)
SIZES = [1600, 800]


def exif(folder: Path):
    out = subprocess.run(
        ["exiftool", "-q", "-j", "-n", "-FileName", "-DateTimeOriginal", "-CreateDate",
         "-GPSLatitude", "-GPSLongitude", str(folder)],
        capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def parse_when(s):
    if not s:
        return None
    s = str(s)[:16]
    s = s[:10].replace(":", "-") + s[10:]  # EXIF writes dates as 2026:09:06
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def km(a, b):
    dlat, dlon = math.radians(b[0] - a[0]), math.radians(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def nearest_place(places, gps, when):
    hhmm = when.strftime("%H:%M")
    best = None
    for p in places:
        if p.get("after") and hhmm < p["after"]:
            continue
        if p.get("before") and hhmm >= p["before"]:
            continue
        d = km(gps, (p["lat"], p["lon"]))
        if d <= p.get("radius", 1.5) and (best is None or d < best[0]):
            best = (d, p["name"])
    return best and best[1]


def series(name):
    m = re.match(r"([A-Za-z_]+)(\d+)", name)
    return (m.group(1), int(m.group(2))) if m else None


def render(args):
    src, out_dir, stem = args
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    im.info.pop("exif", None)
    w, h = im.size
    for s in SIZES:
        r = im.copy(); r.thumbnail((s, s))
        r.save(out_dir / f"{stem}-{s}.webp", "WEBP", quality=82, method=6)
    r = im.copy(); r.thumbnail((24, 24))
    r.save(out_dir / f"{stem}-24.jpg", "JPEG", quality=50)
    return w, h


def main(slug, folder):
    folder = Path(folder)
    content = ROOT / "content"
    itin = json.loads((content / f"{slug}.itinerary.json").read_text())
    places = json.loads((content / f"{slug}.places.json").read_text())["places"]
    ov = json.loads((content / f"{slug}.overrides.json").read_text())
    fixes = ov.get("files", {})

    # 1. collect photos with time + gps
    photos, skipped = [], []
    for x in exif(folder):
        name = x["FileName"]
        if Path(name).suffix.lower() not in PHOTO_EXT or fixes.get(name) == "skip":
            skipped.append(name); continue
        fix = fixes.get(name) or {}
        when = parse_when(fix.get("when")) or parse_when(x.get("DateTimeOriginal") or x.get("CreateDate"))
        gps = (x["GPSLatitude"], x["GPSLongitude"]) if "GPSLatitude" in x else None
        # an override with "place" (even null) pins it — GPS/borrowing won't relabel the photo
        photos.append({"name": name, "when": when, "gps": gps, "place": fix.get("place"), "pinned": "place" in fix})

    # 2. undated: take the time of the previous dated file in the same filename series
    dated = sorted((series(p["name"]), p["when"]) for p in photos if p["when"] and series(p["name"]))
    for p in photos:
        if p["when"] or not series(p["name"]):
            continue
        prev = [w for s, w in dated if s[0] == series(p["name"])[0] and s[1] < series(p["name"])[1]]
        if prev:
            p["when"] = prev[-1] + timedelta(minutes=1)
    undated = [p["name"] for p in photos if not p["when"]]
    photos = [p for p in photos if p["when"]]

    # 3. place: override → gps → borrow from nearest-in-time gps photo on the same day
    for p in photos:
        if not p["pinned"] and p["gps"]:
            p["place"] = nearest_place(places, p["gps"], p["when"])
    located = [p for p in photos if p["gps"]]
    for p in photos:
        if p["pinned"] or p["gps"]:
            continue
        near = min((q for q in located if q["when"].date() == p["when"].date()),
                   key=lambda q: abs(q["when"] - p["when"]), default=None)
        if near and abs(near["when"] - p["when"]) <= BORROW_WINDOW:
            p["place"] = near["place"]
    photos.sort(key=lambda p: (p["when"], p["name"]))

    # 3b. an unplaced run sandwiched between two photos at the same place (same day) is at that place
    for i, p in enumerate(photos):
        if p["place"] or p["pinned"]:
            continue
        before = next((q for q in reversed(photos[:i]) if q["place"]), None)
        after = next((q for q in photos[i + 1:] if q["place"]), None)
        if before and after and before["place"] == after["place"] and before["when"].date() == after["when"].date() == p["when"].date():
            p["place"] = before["place"]

    for p in photos:
        p["file"] = re.sub(r"[^a-z0-9]+", "-", Path(p["name"]).stem.lower()).strip("-")

    # 3c. manifest of every candidate (rejected included) for scripts/review.py, then drop rejects.
    # Rejected photos still count above, so their GPS keeps helping place their neighbours.
    rejected = set(ov.get("rejected", []))
    (ROOT / "_import" / f"{slug}.manifest.json").write_text(json.dumps({
        "folder": str(folder.resolve()),
        "photos": [{"name": p["name"], "file": p["file"], "date": str(p["when"].date()),
                    "time": p["when"].strftime("%H:%M"), "place": p["place"]} for p in photos],
    }, indent=1, ensure_ascii=False))
    photos = [p for p in photos if p["name"] not in rejected]

    # 4. render images, named after the source file so reruns only render what's new
    out_dir = ROOT / "public" / "assets" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    keep = {f"{p['file']}-{s}" for p in photos for s in [*SIZES, 24]}
    for old in out_dir.glob("*"):
        if old.stem not in keep:
            old.unlink()
    todo = [p for p in photos if not (out_dir / f"{p['file']}-24.jpg").exists()]
    with ProcessPoolExecutor(8) as ex:
        list(ex.map(render, [(folder / p["name"], out_dir, p["file"]) for p in todo]))
    dims = []
    for p in photos:
        with Image.open(out_dir / f"{p['file']}-1600.webp") as im:
            w, h = im.size
        dims.append((w, h))
    for p, (w, h) in zip(photos, dims):
        p["img"] = {"id": p["name"], "file": p["file"], "w": w, "h": h,
                    "time": p["when"].strftime("%H:%M"), "place": p["place"]}

    # 5. sections per itinerary day, blocks = runs of the same place
    def day_key(d):
        try:
            return datetime.strptime(f"{d} {photos[0]['when'].year}", "%B %d %Y").date()
        except ValueError:
            return None
    sections = []
    for day in itin["days"]:
        date = day_key(day["date"])
        todays = [p for p in photos if date and p["when"].date() == date]
        blocks = []
        for p in todays:
            if blocks and blocks[-1]["caption"] == p["place"]:
                blocks[-1]["images"].append(p["img"])
            else:
                blocks.append({"caption": p["place"], "images": [p["img"]]})
        for b in blocks:
            b["type"] = "carousel" if len(b["images"]) >= 7 else "grid"
        sections.append({"heading": day["name"], "subtitle": day["date"], "text": day["stops"],
                         "blocks": [{"type": b["type"], "caption": b["caption"], "images": b["images"]} for b in blocks]})

    hero = next((p["img"] for p in photos if p["name"] == ov.get("hero")), photos[0]["img"])
    # Only the gazetteer's coordinates for named places are published, never a photo's own GPS.
    used = {p["place"] for p in photos if p["place"]}
    info = ("lat", "lon", "kind", "blurb", "url", "q")
    place_coords = {pl["name"]: {k: pl[k] for k in info if k in pl} for pl in places if pl["name"] in used}
    doc = {"title": itin["title"], "subtitle": itin["subtitle"], "date": str(photos[0]["when"].date()),
           "map": itin.get("map"), "places": place_coords,
           "hero": [{"type": "grid", "images": [hero]}], "sections": sections, "source": None}
    (content / f"{slug}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False))

    no_coords = sorted(used - set(place_coords))
    if no_coords:
        print(f"places with no coordinates (no map dot) — add them to {slug}.places.json: {no_coords}")
    labelled = sum(1 for p in photos if p["place"])
    print(f"{slug}: {len(photos)} photos, {labelled} placed, {len(photos) - labelled} unplaced")
    print(f"skipped {len(skipped)} (videos/overrides); undated & dropped: {undated}")


if __name__ == "__main__":
    main(*sys.argv[1:])
