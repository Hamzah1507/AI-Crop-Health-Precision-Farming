"""
Sample image library (development / demo aid).

Lists the images described by `uploads/sample_images/manifest.json` so the Disease Detection page can offer them
for testing. The images are served read-only from `/sample-images/...` (mounted in main.py). Selecting one in the
UI sends it through the NORMAL upload endpoint, so it gets the same byte-level validation as any user upload.

Disabled with ENABLE_SAMPLE_LIBRARY=false. Labels come from the source datasets and are not predictions.
"""
import json
import os
from typing import Optional
from fastapi import APIRouter, Depends
from app.config import get_settings
from app.models.user import User
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/samples", tags=["Sample Library"])
_cache = {"mtime": None, "images": []}

FIELDS = ("id", "path", "filename", "crop", "condition", "label", "label_source", "source", "license", "license_url",
          "author", "source_url", "width", "height", "setting")


def library_dir() -> str:
    return os.path.abspath(get_settings().SAMPLE_LIBRARY_DIR)


def load_manifest():
    """The manifest's image entries, re-read only when the file changes. Empty list if there is no library."""
    path = os.path.join(library_dir(), "manifest.json")
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return []
    if _cache["mtime"] != (path, mtime):
        with open(path, encoding="utf-8") as f:
            _cache["images"] = json.load(f).get("images", [])
        _cache["mtime"] = (path, mtime)
    return _cache["images"]


@router.get("/")
def list_samples(crop: Optional[str] = None, condition: Optional[str] = None, current_user: User = Depends(get_current_user)):
    if not get_settings().ENABLE_SAMPLE_LIBRARY:
        return {"enabled": False, "count": 0, "items": []}
    root = library_dir()
    items = []
    for e in load_manifest():
        if crop and e.get("crop") != crop:
            continue
        if condition and e.get("condition") != condition:
            continue
        full = os.path.abspath(os.path.join(root, e["path"]))
        if os.path.commonpath([root, full]) != root or not os.path.isfile(full):
            continue                      # never expose anything outside the library, or files that are missing
        items.append({**{k: e.get(k) for k in FIELDS}, "url": "/sample-images/" + e["path"]})
    return {"enabled": True, "count": len(items), "items": items}
