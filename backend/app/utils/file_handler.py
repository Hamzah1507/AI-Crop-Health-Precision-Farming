"""
Safe handling of uploaded images.

Nothing the client sends about the file is trusted:
- The file type is identified from the actual bytes (magic numbers), not from
  the Content-Type header or the filename.
- Only JPEG, PNG and WebP are accepted.
- The size limit is enforced while streaming, so an oversized upload is
  rejected without reading all of it.
- Image dimensions are read from the header BEFORE decoding, so a tiny file
  that claims a huge canvas ("decompression bomb") is refused.
- When OpenCV is installed the image is fully decoded, which rejects truncated,
  corrupt or disguised files. Without OpenCV only the byte/header checks apply.
- The stored name is a random UUID plus an extension derived from the detected
  format. The client filename is never used for a path, so path traversal and
  double extensions are impossible.
Invalid uploads are rejected before anything is written to disk.
"""

import os
import re
import struct
import uuid
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException
from app.config import get_settings
from app.ml.image_preprocessing import cv2, np, OPENCV_AVAILABLE

settings = get_settings()

MAX_FILE_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes
MAX_PIXELS = 40_000_000       # ~40 megapixels; larger canvases are refused
MIN_DIMENSION = 8             # pixels; smaller images are not usable leaf photos
READ_CHUNK = 64 * 1024
EXTENSIONS = {"jpeg": ".jpg", "png": ".png", "webp": ".webp"}


def sniff_format(data: bytes) -> Optional[str]:
    """Identify the image format from its leading bytes. Returns None if unsupported."""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def read_dimensions(fmt: str, data: bytes) -> Optional[Tuple[int, int]]:
    """Read (width, height) from the file header without decoding pixels."""
    try:
        if fmt == "png":
            if data[12:16] != b"IHDR":
                return None
            return struct.unpack(">II", data[16:24])

        if fmt == "jpeg":
            i = 2
            while i + 9 < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker == 0xFF:
                    i += 1
                    continue
                if marker in (0x01, 0xD8) or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                # Start-of-frame markers carry the dimensions (not DHT/JPG/DAC)
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    height, width = struct.unpack(">HH", data[i + 5:i + 9])
                    return width, height
                i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
            return None

        if fmt == "webp":
            chunk = data[12:16]
            if chunk == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
                width, height = struct.unpack("<HH", data[26:30])
                return width & 0x3FFF, height & 0x3FFF
            if chunk == b"VP8L" and data[20] == 0x2F:
                bits = struct.unpack("<I", data[21:25])[0]
                return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
            if chunk == b"VP8X":
                return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little")
    except (struct.error, IndexError):
        return None
    return None


def safe_display_name(filename: Optional[str], default: str = "upload") -> str:
    """A harmless version of the client's filename, for DISPLAY only (never used as a path)."""
    name = os.path.basename((filename or "").replace("\\", "/"))
    name = re.sub(r"[^\w.\- ]", "_", name).strip(" .")
    return (name or default)[-120:]


async def validate_and_save_image(file: UploadFile) -> str:
    """Validate the upload from its real bytes and save it safely. Returns the stored file path."""
    # 1. Read with a hard size limit
    chunks, total = [], 0
    while True:
        chunk = await file.read(READ_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE_MB}MB"
            )
        chunks.append(chunk)
    content = b"".join(chunks)
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")

    # 2. Identify the real format from the bytes
    fmt = sniff_format(content)
    if fmt is None:
        raise HTTPException(status_code=400, detail="Unsupported or invalid file. Please upload a JPEG, PNG or WebP image.")

    # 3. Check the claimed dimensions before decoding anything
    dims = read_dimensions(fmt, content)
    if dims is None:
        raise HTTPException(status_code=400, detail="The image file is corrupt or has an unreadable header.")
    width, height = dims
    if width < MIN_DIMENSION or height < MIN_DIMENSION:
        raise HTTPException(status_code=400, detail=f"Image is too small (minimum {MIN_DIMENSION}x{MIN_DIMENSION} pixels).")
    if width * height > MAX_PIXELS:
        raise HTTPException(status_code=400, detail="Image dimensions are too large to process.")

    # 4. Fully decode to prove the file really is a valid image
    if OPENCV_AVAILABLE:
        try:
            decoded = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
        except Exception:
            decoded = None
        if decoded is None:
            raise HTTPException(status_code=400, detail="The file could not be decoded as a valid image.")

    # 5. Store under a server-chosen name; the extension comes from the detected format
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}{EXTENSIONS[fmt]}")
    root = os.path.realpath(upload_dir)
    if os.path.commonpath([root, os.path.realpath(file_path)]) != root:
        raise HTTPException(status_code=400, detail="Invalid upload location")

    with open(file_path, "xb") as f:   # 'x': never overwrite an existing file
        f.write(content)

    return file_path


def delete_file(file_path: str):
    """Delete a file if it exists."""
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
