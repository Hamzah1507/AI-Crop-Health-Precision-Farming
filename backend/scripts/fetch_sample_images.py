"""
Build the CropHealth AI sample image library from openly licensed sources.

    python scripts/fetch_sample_images.py            # download, validate, write manifest + README
    python scripts/fetch_sample_images.py --dry-run  # only list what would be fetched

Output: backend/uploads/sample_images/  (images, manifest.json, README.md)

Sources (all real photographs, nothing generated):
  * PlantVillage (lab-condition leaf images with expert disease labels), licensed CC BY-SA 3.0 per the
    dataset's Hugging Face card (the GitHub mirror itself states no license - see README.md).
  * Wikimedia Commons photographs. The licence of every file is read from Commons at download time and
    the file is skipped unless it is CC0 / public domain / CC BY / CC BY-SA.

Every image is verified to decode, exact duplicates are dropped, and the original attribution is stored in
manifest.json and README.md. Images are a TEST LIBRARY; the dataset labels are the sources' labels, not
predictions made by this application.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover
    sys.exit("This script needs opencv-python-headless and numpy (see requirements.txt).")

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads", "sample_images")
ROOT = os.path.abspath(ROOT)
UA = {"User-Agent": "CropHealthAI-capstone/1.0 (student project; contacts@vectrastaffing.com)"}

PV_REPO = "spMohanty/PlantVillage-Dataset"
PV_AUTHOR = "Hughes D.P. & Salathé M. (PlantVillage); distributed with Mohanty, Hughes & Salathé (2016)"
PV_LICENSE = "CC BY-SA 3.0"
PV_LICENSE_URL = "https://creativecommons.org/licenses/by-sa/3.0/"
PV_LICENSE_SOURCE = "Hugging Face dataset card mohanty/PlantVillage (cardData.license: cc-by-sa-3.0)"

# (class folder in raw/color, crop, condition, human label, how many images)
PLANTVILLAGE = [
    ("Tomato___healthy", "tomato", "healthy", "Healthy", 3),
    ("Tomato___Early_blight", "tomato", "disease", "Early blight", 3),
    ("Tomato___Late_blight", "tomato", "disease", "Late blight", 3),
    ("Tomato___Bacterial_spot", "tomato", "disease", "Bacterial spot", 3),
    ("Tomato___Leaf_Mold", "tomato", "disease", "Leaf mold", 2),
    ("Tomato___Septoria_leaf_spot", "tomato", "disease", "Septoria leaf spot", 2),
    ("Tomato___Target_Spot", "tomato", "disease", "Target spot", 2),
    ("Tomato___Tomato_mosaic_virus", "tomato", "disease", "Tomato mosaic virus", 2),
    ("Tomato___Tomato_Yellow_Leaf_Curl_Virus", "tomato", "disease", "Yellow leaf curl virus", 2),
    ("Tomato___Spider_mites Two-spotted_spider_mite", "tomato", "pest", "Two-spotted spider mite damage", 3),
    ("Potato___healthy", "potato", "healthy", "Healthy", 3),
    ("Potato___Early_blight", "potato", "disease", "Early blight", 3),
    ("Potato___Late_blight", "potato", "disease", "Late blight", 3),
    ("Corn_(maize)___healthy", "maize", "healthy", "Healthy", 3),
    ("Corn_(maize)___Common_rust_", "maize", "disease", "Common rust", 2),
    ("Corn_(maize)___Northern_Leaf_Blight", "maize", "disease", "Northern leaf blight", 2),
    ("Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot", "maize", "disease", "Gray leaf spot", 2),
    ("Apple___healthy", "apple", "healthy", "Healthy", 2),
    ("Apple___Apple_scab", "apple", "disease", "Apple scab", 2),
    ("Grape___healthy", "grape", "healthy", "Healthy", 2),
    ("Grape___Black_rot", "grape", "disease", "Black rot", 2),
    ("Pepper,_bell___healthy", "pepper", "healthy", "Healthy", 2),
    ("Pepper,_bell___Bacterial_spot", "pepper", "disease", "Bacterial spot", 2),
]

# Wikimedia Commons files (exact titles). condition: pest / disease / photo (a crop photo with no health label).
# `title_prefix` entries are resolved to the full file title at run time.
COMMONS = [
    # pests
    ("Pentalonia nigronervosa P5280047.jpg", "banana", "pest", "Banana aphid (Pentalonia nigronervosa)", "pest_banana-aphid"),
    ("Corn leaf aphids (Rhopalosiphum maidis) on maize (Zea mays).jpg", "maize", "pest", "Corn leaf aphids on maize", "pest_maize-aphids"),
    ("Illinoia pepperi - blueberry aphid.jpg", "blueberry", "pest", "Blueberry aphid (Illinoia pepperi)", "pest_blueberry-aphid"),
    ("Bemisia tabaci under leaf of eggplant.jpg", "eggplant", "pest", "Whitefly (Bemisia tabaci) under an eggplant leaf", "pest_whitefly-eggplant"),
    ("Larva of Spodoptera litura on leaf.jpg", "other", "pest", "Armyworm / cutworm larva (Spodoptera litura)", "pest_armyworm-spodoptera"),
    ("Chard leaf miner damage (blisters).jpg", "chard", "pest", "Leaf miner damage on chard", "pest_leaf-miner-chard"),
    ("Basilikum Thripsbefall-Schlaghecken.jpg", "basil", "pest", "Thrips damage on basil", "pest_thrips-basil"),
    ("Leaf-miner-tomato.jpg", "tomato", "pest", "Leaf miner damage on tomato", "pest_leaf-miner-tomato"),
    ("@Solanum lycopersicum leaves with spider mite or thrips damage in Dnipro", "tomato", "pest", "Spider mite or thrips damage on tomato leaves", "pest_tomato-mite-thrips"),
    # crops without a PlantVillage class
    ("Oryza sativa (Asian rice)- Plants.jpg", "rice", "photo", "Rice plants", "rice_plants"),
    ("Oryza sativa (Asian rice)- Farm.jpg", "rice", "photo", "Rice farm", "rice_farm"),
    ("Paddy nursery in Raichur, Karnataka.jpg", "rice", "photo", "Paddy nursery", "rice_paddy-nursery"),
    ("Triticum aestivum - Common Wheat 01.jpg", "wheat", "photo", "Wheat plant", "wheat_plant"),
    ("Naked wheat(Triticum aestivum) in Nepal-September 27, 2016-IMG 8014.jpg", "wheat", "photo", "Wheat field", "wheat_field"),
    ("Young wheat near Screveton - geograph.org.uk - 6503059.jpg", "wheat", "photo", "Young wheat", "wheat_young"),
    ("Bruine roest op tarwe (Puccinia recondita f.sp. tritici on Triticum aestivum).jpg", "wheat", "disease", "Leaf (brown) rust, Puccinia triticina", "wheat_leaf-rust"),
    ("Bipolaris maydis Southern leaf blight of maize 50952.jpg", "maize", "disease", "Southern leaf blight (Bipolaris maydis)", "maize_southern-leaf-blight"),
    ("Cotton plant, Ware County, GA, US.jpg", "cotton", "photo", "Cotton plant", "cotton_plant"),
    ("CSIRO ScienceImage 1366 Cotton boll.jpg", "cotton", "photo", "Cotton boll", "cotton_boll"),
    ("Mr. Stripey Heirloom Tomato leaf.jpg", "tomato", "photo", "Tomato leaf", "tomato_leaf-photo"),
]

SIX_CROPS = {"rice", "wheat", "tomato", "potato", "cotton", "maize"}
ALLOWED_LICENSE = re.compile(r"^(CC0|Public domain|PD|CC BY(-SA)? [0-9.]+)", re.I)


def http_get(url, retries=4, binary=True, delay=8):
    last = None
    for attempt in range(retries):
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
            return data if binary else data.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 503) and attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
                continue
            raise
        except Exception as e:  # network hiccup
            last = e
            time.sleep(3)
    raise last if last else RuntimeError(f"could not fetch {url}")


def api_json(url):
    return json.loads(http_get(url, binary=False))


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def is_valid_image(data):
    """Magic bytes + a real decode. Returns (format, width, height) or None."""
    fmt = ("jpeg" if data[:3] == b"\xff\xd8\xff" else "png" if data[:8] == b"\x89PNG\r\n\x1a\n"
           else "webp" if data[:4] == b"RIFF" and data[8:12] == b"WEBP" else None)
    if not fmt:
        return None
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None or min(img.shape[:2]) < 64:
        return None
    return fmt, img.shape[1], img.shape[0]


def pick_spread(names, k):
    names = sorted(names)
    if k >= len(names):
        return names
    return [names[round(i * (len(names) - 1) / (k - 1))] for i in range(k)] if k > 1 else [names[len(names) // 2]]


def plantvillage_candidates(dry):
    """Yield (class, crop, condition, label, file name, raw url) using the GitHub trees API (the recursive tree is truncated)."""
    base = f"https://api.github.com/repos/{PV_REPO}/git/trees/"
    root = api_json(base + "master")
    raw = next(e["sha"] for e in root["tree"] if e["path"] == "raw")
    color = next(e["sha"] for e in api_json(base + raw)["tree"] if e["path"] == "color")
    classes = {e["path"]: e["sha"] for e in api_json(base + color)["tree"] if e["type"] == "tree"}
    for cls, crop, cond, label, k in PLANTVILLAGE:
        if cls not in classes:
            print(f"  ! class not found upstream, skipped: {cls}")
            continue
        files = [e["path"] for e in api_json(base + classes[cls])["tree"] if e["path"].lower().endswith((".jpg", ".jpeg", ".png"))]
        for name in pick_spread(files, k):
            url = f"https://raw.githubusercontent.com/{PV_REPO}/master/raw/color/{urllib.parse.quote(cls)}/{urllib.parse.quote(name)}"
            yield cls, crop, cond, label, name, url


def commons_info(title):
    q = urllib.parse.urlencode({"action": "query", "titles": "File:" + title, "prop": "imageinfo", "format": "json",
                                "iiprop": "url|size|extmetadata|mime"})
    page = next(iter(api_json("https://commons.wikimedia.org/w/api.php?" + q)["query"]["pages"].values()))
    ii = (page.get("imageinfo") or [None])[0]
    if not ii:
        return None
    meta = ii["extmetadata"]
    strip = lambda k: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", meta.get(k, {}).get("value", ""))).strip()
    return {"license": strip("LicenseShortName"), "license_url": meta.get("LicenseUrl", {}).get("value", ""),
            "artist": strip("Artist"), "page": ii["descriptionurl"], "mime": ii["mime"], "width": ii["width"]}


def resolve_prefix(prefix):
    q = urllib.parse.urlencode({"action": "query", "list": "allpages", "apnamespace": 6, "apprefix": prefix, "aplimit": 5, "format": "json"})
    pages = api_json("https://commons.wikimedia.org/w/api.php?" + q)["query"]["allpages"]
    return pages[0]["title"][5:] if pages else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--readme-only", action="store_true", help="regenerate README.md from the existing manifest.json (no downloads)")
    args = ap.parse_args()

    if args.readme_only:
        with open(os.path.join(ROOT, "manifest.json"), encoding="utf-8") as f:
            existing = json.load(f)
        write_readme(existing["images"], [tuple(s) for s in existing.get("skipped", [])])
        print("README.md regenerated from manifest.json")
        return

    entries, seen_hashes, skipped = [], {}, []
    counters = {}

    def next_name(stem):
        counters[stem] = counters.get(stem, 0) + 1
        return f"{stem}_{counters[stem]:03d}.jpg"

    def add(data, crop, cond, label, label_source, source, stem, extra):
        info = is_valid_image(data)
        if not info:
            skipped.append((stem, "not a valid image"))
            return
        sha = hashlib.sha256(data).hexdigest()
        if sha in seen_hashes:
            skipped.append((stem, f"exact duplicate of {seen_hashes[sha]}"))
            return
        fmt, w, h = info
        ext = {"jpeg": ".jpg", "png": ".png", "webp": ".webp"}[fmt]
        filename = next_name(stem)[:-4] + ext
        seen_hashes[sha] = filename
        entries.append({"filename": filename, "crop": crop, "condition": cond, "label": label, "label_source": label_source,
                        "source": source, "format": fmt, "width": w, "height": h, "bytes": len(data), "sha256": sha, "_data": data, **extra})

    print("PlantVillage (GitHub mirror)...")
    for cls, crop, cond, label, name, url in plantvillage_candidates(args.dry_run):
        if args.dry_run:
            print("  would fetch", cls, name)
            continue
        data = http_get(url)
        add(data, crop, cond, label, "PlantVillage class folder: " + cls, "PlantVillage",
            f"{crop}_{slug(label)}",
            {"author": PV_AUTHOR, "license": PV_LICENSE, "license_url": PV_LICENSE_URL, "license_source": PV_LICENSE_SOURCE,
             "source_url": f"https://github.com/{PV_REPO}/tree/master/raw/color/{urllib.parse.quote(cls)}",
             "original_file": name, "setting": "lab (single leaf, plain background)", "modifications": "none (original file)"})

    print("Wikimedia Commons...")
    for title, crop, cond, label, stem in COMMONS:
        if title.startswith("@"):
            resolved = resolve_prefix(title[1:])
            if not resolved:
                skipped.append((stem, "title prefix not found on Commons"))
                continue
            title = resolved
        info = commons_info(title)
        if not info:
            skipped.append((title, "file not found on Commons"))
            continue
        if not ALLOWED_LICENSE.match(info["license"]) or re.search(r"NC|ND", info["license"]) or info["mime"] != "image/jpeg":
            skipped.append((title, f"licence/format not acceptable: {info['license']} {info['mime']}"))
            continue
        if args.dry_run:
            print("  would fetch", title, "|", info["license"])
            continue
        time.sleep(3)
        width = min(1024, info["width"])
        data = http_get("https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(title) + f"?width={width}")
        cond_label_source = "Wikimedia Commons file title/description" if cond in ("disease", "pest") else "none (crop photo, no health label)"
        add(data, crop, cond, label, cond_label_source, "Wikimedia Commons", stem,
            {"author": info["artist"], "license": info["license"], "license_url": info["license_url"] or info["page"],  # public-domain files have no licence URL: point at the file page
             "license_source": "Wikimedia Commons file metadata",
             "source_url": info["page"], "original_file": title, "setting": "field/garden photograph",
             "modifications": f"downscaled to {width}px wide by the Wikimedia thumbnailer" if width < info["width"] else "none (original file)"})

    if args.dry_run:
        print("skipped:", skipped)
        return

    # ---- write files: ONE real copy per image; crop folders get hard-link views (copy if links are unsupported) ----
    for sub in ("healthy", "disease", "pests", "rice", "wheat", "tomato", "potato", "cotton", "maize", "other_crops"):
        os.makedirs(os.path.join(ROOT, sub), exist_ok=True)
    manifest = []
    for e in entries:
        data = e.pop("_data")
        crop_dir = e["crop"] if e["crop"] in SIX_CROPS else "other_crops"
        primary = {"healthy": "healthy", "disease": "disease", "pest": "pests"}.get(e["condition"], crop_dir)
        primary_rel = f"{primary}/{e['filename']}"
        with open(os.path.join(ROOT, primary_rel), "wb") as f:
            f.write(data)
        crop_rel = f"{crop_dir}/{e['filename']}"
        if crop_rel != primary_rel:
            try:
                if os.path.exists(os.path.join(ROOT, crop_rel)):
                    os.remove(os.path.join(ROOT, crop_rel))
                os.link(os.path.join(ROOT, primary_rel), os.path.join(ROOT, crop_rel))
            except OSError:
                shutil.copy2(os.path.join(ROOT, primary_rel), os.path.join(ROOT, crop_rel))
        manifest.append({"id": os.path.splitext(e["filename"])[0], "path": primary_rel, "crop_folder_path": crop_rel, **e})

    manifest.sort(key=lambda m: m["path"])
    with open(os.path.join(ROOT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"generated_by": "scripts/fetch_sample_images.py", "count": len(manifest), "skipped": skipped,
                   "note": "Dataset/source labels are NOT predictions of this application. 'condition' is one of healthy, disease, pest, photo (crop photo without a health label).",
                   "images": manifest}, f, indent=2, ensure_ascii=False)
    write_readme(manifest, skipped)
    print(f"\nWrote {len(manifest)} images, {len(skipped)} skipped:")
    for s in skipped:
        print("   skipped:", s)


def write_readme(manifest, skipped):
    by = {}
    for m in manifest:
        by.setdefault(m["source"], []).append(m)
    counts, views = {}, {}
    for m in manifest:
        counts[m["path"].split("/")[0]] = counts.get(m["path"].split("/")[0], 0) + 1
        if m["crop_folder_path"] != m["path"]:
            views[m["crop_folder_path"].split("/")[0]] = views.get(m["crop_folder_path"].split("/")[0], 0) + 1
    lines = [
        "# CropHealth AI sample image library",
        "",
        "A small **test library** of real crop photographs for demonstrating the Disease Detection workflow.",
        "It is separate from user uploads (those are saved in `uploads/` with random names; this folder is `uploads/sample_images/`).",
        "",
        "## Read this first",
        "- The labels below come from the **source datasets / Wikimedia contributors**. They are *not* predictions made by CropHealth AI.",
        "- CropHealth AI's disease detector is **simulated** until a trained model is loaded, so its results on these images are not real diagnoses.",
        "- PlantVillage images are laboratory images (one leaf, plain background) and are not representative of field photographs.",
        "- Nothing here was generated by AI. Re-create the library with `python scripts/fetch_sample_images.py`.",
        "",
        "## Folder structure",
        "Each image exists **once** on disk. Images with a health label are stored under `healthy/`, `disease/` or `pests/`;",
        "a hard link (or copy where hard links are unsupported) is also placed in the matching crop folder so you can browse by crop.",
        "Crop photographs without a health label live directly in their crop folder. `manifest.json` is the source of truth.",
        "",
        "| Folder | Primary images | Linked views | Files you will see |", "|---|---|---|---|",
    ]
    for d in ("healthy", "disease", "pests", "rice", "wheat", "tomato", "potato", "cotton", "maize", "other_crops"):
        lines.append(f"| `{d}/` | {counts.get(d, 0)} | {views.get(d, 0)} | {counts.get(d, 0) + views.get(d, 0)} |")
    lines += ["", f"**Total distinct images: {len(manifest)}**", "", "## Sources and licences", ""]
    lines += [
        "### PlantVillage (CC BY-SA 3.0)",
        f"- Images: {len(by.get('PlantVillage', []))}, unmodified originals from <https://github.com/{PV_REPO}> (`raw/color`).",
        "- Licence: **CC BY-SA 3.0** <https://creativecommons.org/licenses/by-sa/3.0/> as given in the dataset's Hugging Face card (`mohanty/PlantVillage`). "
        "The GitHub repository itself states no licence, so this README follows the dataset card; check it again before redistributing.",
        "- Attribution: Hughes, D. P. & Salathé, M. (PlantVillage). Mohanty, S. P., Hughes, D. P. & Salathé, M. (2016). "
        "*Using deep learning for image-based plant disease detection.* Frontiers in Plant Science 7:1419. <https://doi.org/10.3389/fpls.2016.01419>",
        "- ShareAlike: if you modify and redistribute these images, license the result under CC BY-SA too.",
        "",
        "### Wikimedia Commons (per-file licences)",
        "Each file keeps its own licence (CC0, public domain, CC BY or CC BY-SA); author, licence and page URL are listed below and in `manifest.json`.",
        "",
        "| File | Subject | Author | Licence | Source |", "|---|---|---|---|---|",
    ]
    for m in by.get("Wikimedia Commons", []):
        author = (m["author"] or "unknown")[:60].replace("|", "/")
        lines.append(f"| `{m['path']}` | {m['label']} | {author} | {m['license']} | <{m['source_url']}> |")
    lines += ["", "## Not obtained"]
    lines.append("- **Rice disease photographs**: no suitably licensed, correctly labelled file was found on Wikimedia Commons, and no rice class exists in PlantVillage. "
                 "Rice is represented by crop photographs only (no health label).")
    for s in skipped:
        lines.append(f"- {s[0]}: {s[1]}")
    lines += ["", "## Known limitations", "- PlantVillage contains near-duplicate crops of the same leaf; only exact duplicates (by SHA-256) are removed.",
              "- Wikimedia images were downscaled to at most 1024 px wide by the Wikimedia thumbnailer (noted per image in `manifest.json`).", ""]
    with open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
