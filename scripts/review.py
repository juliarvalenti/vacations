#!/usr/bin/env python3
"""Local photo review: approve/reject photos for a trip built by import_local.py.

  scripts/review.py <slug> [port]      → opens http://localhost:4400

Shows every candidate photo (from _import/<slug>.manifest.json, written by import_local.py), grouped
by day and place. Rejections autosave to content/<slug>.overrides.json → "rejected". "Apply" reruns
import_local.py so rejected photos drop out of the site (and their files out of public/).
Rejected photos' thumbnails are rendered from the originals into _import/review/ (gitignored),
never into public/.
"""
import json, subprocess, sys, webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()
ROOT = Path(__file__).resolve().parent.parent


def make_handler(slug):
    manifest_path = ROOT / "_import" / f"{slug}.manifest.json"
    overrides_path = ROOT / "content" / f"{slug}.overrides.json"
    itinerary_path = ROOT / "content" / f"{slug}.itinerary.json"
    public = ROOT / "public" / "assets" / slug
    cache = ROOT / "_import" / "review" / slug
    cache.mkdir(parents=True, exist_ok=True)

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, body, ctype="application/json", code=200):
            if isinstance(body, str):
                body = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store" if ctype.startswith(("application", "text")) else "max-age=3600")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                return self.send((Path(__file__).parent / "review.html").read_text(), "text/html; charset=utf-8")
            if self.path == "/data":
                manifest = json.loads(manifest_path.read_text())
                ov = json.loads(overrides_path.read_text())
                itin = json.loads(itinerary_path.read_text())
                return self.send(json.dumps({"slug": slug, "title": itin["title"], "days": itin["days"],
                                             "photos": manifest["photos"], "rejected": ov.get("rejected", [])}))
            if self.path.startswith("/img/"):
                size, file = self.path.split("/")[2:4]  # /img/<800|1600>/<file>
                size = "1600" if size == "1600" else "800"
                pub = public / f"{file}-{size}.webp"
                if pub.exists():
                    return self.send(pub.read_bytes(), "image/webp")
                cached = cache / f"{file}-{size}.webp"
                if not cached.exists():
                    manifest = json.loads(manifest_path.read_text())
                    src = next((p["name"] for p in manifest["photos"] if p["file"] == file), None)
                    if not src:
                        return self.send("not found", "text/plain", 404)
                    im = ImageOps.exif_transpose(Image.open(Path(manifest["folder"]) / src)).convert("RGB")
                    im.thumbnail((int(size), int(size)))
                    im.save(cached, "WEBP", quality=80)
                return self.send(cached.read_bytes(), "image/webp")
            self.send("not found", "text/plain", 404)

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0)
            if self.path == "/rejected":
                ov = json.loads(overrides_path.read_text())
                ov["rejected"] = sorted(set(json.loads(body)))
                overrides_path.write_text(json.dumps(ov, indent=2, ensure_ascii=False) + "\n")
                return self.send(json.dumps({"ok": True, "count": len(ov["rejected"])}))
            if self.path == "/apply":
                folder = json.loads(manifest_path.read_text())["folder"]
                r = subprocess.run([sys.executable, str(ROOT / "scripts" / "import_local.py"), slug, folder],
                                   capture_output=True, text=True)
                return self.send(json.dumps({"ok": r.returncode == 0, "out": (r.stdout + r.stderr)[-2000:]}))
            self.send("not found", "text/plain", 404)

    return Handler


def main(slug, port="4400"):
    if not (ROOT / "_import" / f"{slug}.manifest.json").exists():
        sys.exit(f"no manifest for {slug} — run scripts/import_local.py {slug} <folder> first")
    server = HTTPServer(("127.0.0.1", int(port)), make_handler(slug))
    url = f"http://localhost:{port}/"
    print(f"reviewing {slug} at {url}  (ctrl-c to stop)")
    webbrowser.open(url)
    server.serve_forever()


if __name__ == "__main__":
    main(*sys.argv[1:])
