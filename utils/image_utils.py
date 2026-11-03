"""
SmartRent AI - Image Processing and Storage Utilities
"""
import base64
import io
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
from config import ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_SIZE_MB


def validate_image(file_obj) -> Tuple[bool, str]:
    """
    Validate uploaded image file by size, extension, and integrity.
    """
    if file_obj is None:
        return False, "No file provided"

    # Check extension
    name = file_obj.name
    ext = name.split(".")[-1].lower() if "." in name else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False, f"Unsupported file type .{ext}. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"

    # Check size
    file_bytes = file_obj.getvalue()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_IMAGE_SIZE_MB:
        return False, f"File size ({size_mb:.1f} MB) exceeds maximum allowed limit of {MAX_IMAGE_SIZE_MB} MB"

    # Verify image integrity with Pillow
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
    except Exception as e:
        return False, f"Corrupted or invalid image file: {e}"

    return True, "Valid"


def save_image_to_disk(file_bytes: bytes, original_name: str, target_dir: Path, prefix: str = "img") -> Tuple[str, str, int]:
    """
    Save validated image bytes to disk with a sanitized, unique filename.
    Returns (absolute_path_str, filename, file_size_bytes).
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    ext = original_name.split(".")[-1].lower() if "." in original_name else "jpg"
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{prefix}_{unique_id}.{ext}"
    filepath = target_dir / filename

    with open(filepath, "wb") as f:
        f.write(file_bytes)

    return str(filepath), filename, len(file_bytes)


def encode_image_for_api(image_path_or_bytes, max_dim: int = 1200, quality: int = 85) -> str:
    """
    Load an image, convert RGBA/P to RGB, resize if larger than max_dim to maintain fast API processing,
    and return base64-encoded JPEG string.
    """
    if isinstance(image_path_or_bytes, (str, Path)):
        img = Image.open(image_path_or_bytes)
    elif isinstance(image_path_or_bytes, bytes):
        img = Image.open(io.BytesIO(image_path_or_bytes))
    else:
        # File uploader-like object
        img = Image.open(image_path_or_bytes)

    # Convert to RGB if needed
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Resize proportionally if width or height exceeds max_dim
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / float(max(w, h))
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def delete_file_safely(filepath: str) -> bool:
    """Safely remove a file from disk if it exists."""
    try:
        p = Path(filepath)
        if p.exists() and p.is_file():
            p.unlink()
            return True
    except Exception:
        pass
    return False
