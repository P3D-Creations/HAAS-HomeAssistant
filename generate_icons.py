"""Generate brand images for the HAAS CNC Home Assistant integration.

Resizes the source HAAS logo (Haas-Logo-Single-01-1136046903.png) into
the formats required by the Home Assistant brands system:

  custom_components/haas_cnc/
    icon.png        256 × 256   (square icon, used in device/entity lists)
    icon@2x.png     512 × 512
    logo.png        256 × 256   (wordmark-style; square is fine for custom)
    logo@2x.png     512 × 512

Run:  python generate_icons.py
"""
from PIL import Image
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMPONENT_DIR = os.path.join(SCRIPT_DIR, "custom_components", "haas_cnc")

# Source file (official HAAS logo, 1800×1800 RGBA)
SOURCE = os.path.join(SCRIPT_DIR, "Haas-Logo-Single-01-1136046903.png")

# Output targets:  (filename, size)
TARGETS = [
    ("icon.png",     256),
    ("icon@2x.png",  512),
    ("logo.png",     256),
    ("logo@2x.png",  512),
]


def resize_logo(source_path: str, size: int) -> Image.Image:
    """Open *source_path* and resize to *size* × *size* with high-quality resampling."""
    img = Image.open(source_path).convert("RGBA")

    # Fit inside a square canvas, preserving aspect ratio and centering
    img.thumbnail((size, size), Image.LANCZOS)

    # If the image isn't perfectly square after thumbnail, centre it on
    # a transparent canvas
    if img.size != (size, size):
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        offset = ((size - img.width) // 2, (size - img.height) // 2)
        canvas.paste(img, offset, img)
        return canvas

    return img


def main() -> None:
    if not os.path.exists(SOURCE):
        print(f"ERROR: Source logo not found at {SOURCE}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(COMPONENT_DIR, exist_ok=True)

    print(f"Source: {SOURCE}")
    src = Image.open(SOURCE)
    print(f"  Size: {src.size}, Mode: {src.mode}")
    print()

    for name, size in TARGETS:
        resized = resize_logo(SOURCE, size)

        # Save into the component directory (HA loads from here)
        comp_path = os.path.join(COMPONENT_DIR, name)
        resized.save(comp_path, "PNG", optimize=True)

        # Also save to repo root (HACS picks up from here)
        root_path = os.path.join(SCRIPT_DIR, name)
        resized.save(root_path, "PNG", optimize=True)

        print(f"  {name:16s}  {size}×{size}  →  "
              f"component ({os.path.getsize(comp_path):,} B)  "
              f"root ({os.path.getsize(root_path):,} B)")

    print("\nDone.")


if __name__ == "__main__":
    main()
