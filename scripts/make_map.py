#!/usr/bin/env python3
"""Extract simplified coastline outlines for one US state into src/maps/<slug>.json.

  scripts/make_map.py <states.shp> "<State name>" <slug> [min_area_deg2] [tolerance_deg]

Source: Census cartographic boundary file, e.g.
  https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_state_5m.zip
Output: {"shapes": [[[lon, lat], ...], ...]} — one ring per island/landmass, largest first.
Used by src/components/MiniMap.astro.
"""
import json, sys
from pathlib import Path
import shapefile

ROOT = Path(__file__).resolve().parent.parent


def area(ring):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]))) / 2


def simplify(pts, tol):
    """Douglas–Peucker."""
    if len(pts) < 3:
        return pts
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    dx, dy = x1 - x0, y1 - y0
    norm = (dx * dx + dy * dy) ** 0.5 or 1e-12
    i, dmax = 0, 0.0
    for k in range(1, len(pts) - 1):
        d = abs(dy * pts[k][0] - dx * pts[k][1] + x1 * y0 - y1 * x0) / norm
        if d > dmax:
            i, dmax = k, d
    if dmax <= tol:
        return [pts[0], pts[-1]]
    return simplify(pts[: i + 1], tol)[:-1] + simplify(pts[i:], tol)


def main(shp, state, slug, min_area="0.001", tol="0.002"):
    r = shapefile.Reader(shp)
    idx = [f[0] for f in r.fields[1:]].index("NAME")
    shape = next(s.shape for s in r.iterShapeRecords() if s.record[idx] == state)
    parts = list(shape.parts) + [len(shape.points)]
    rings = [shape.points[a:b] for a, b in zip(parts, parts[1:])]
    rings = [ring for ring in rings if area(ring) >= float(min_area)]
    rings.sort(key=area, reverse=True)
    # rings are closed (first == last point), which DP can't handle — simplify each half separately
    halves = lambda ring: simplify(ring[: len(ring) // 2 + 1], float(tol))[:-1] + simplify(ring[len(ring) // 2:], float(tol))
    out = [[[round(x, 4), round(y, 4)] for x, y in halves(list(ring))] for ring in rings]
    dest = ROOT / "src" / "maps" / f"{slug}.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps({"shapes": out}, separators=(",", ":")))
    print(f"{slug}: {len(out)} shapes, {sum(map(len, out))} points, {dest.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main(*sys.argv[1:])
