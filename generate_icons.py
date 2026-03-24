"""Generate icon.png and logo.png for the HAAS CNC HA integration.

Run once to create brand images.  Safe to delete after generating.
"""
from PIL import Image, ImageDraw, ImageFont
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMPONENT_DIR = os.path.join(SCRIPT_DIR, "custom_components", "haas_cnc")

# --- Colour palette ---
BG_COLOR = (30, 30, 30)          # dark grey background
ACCENT = (0, 150, 136)           # teal accent (HA-friendly)
ACCENT_LIGHT = (77, 208, 195)    # lighter teal
WHITE = (255, 255, 255)
GREY = (180, 180, 180)

def draw_cnc_icon(size: int) -> Image.Image:
    """Draw a simple CNC machine icon at *size* × *size* pixels."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    pad = size * 0.1
    s = size  # shorthand

    # Rounded-rectangle background
    d.rounded_rectangle(
        [(0, 0), (s - 1, s - 1)],
        radius=int(s * 0.18),
        fill=BG_COLOR,
    )

    # --- Machine body (rectangle) ---
    body_l = int(s * 0.18)
    body_t = int(s * 0.30)
    body_r = int(s * 0.82)
    body_b = int(s * 0.78)
    d.rounded_rectangle(
        [(body_l, body_t), (body_r, body_b)],
        radius=int(s * 0.04),
        fill=(50, 50, 50),
        outline=ACCENT,
        width=max(2, int(s * 0.015)),
    )

    # --- Spindle column (vertical bar) ---
    sp_w = int(s * 0.10)
    sp_l = int(s * 0.45)
    sp_r = sp_l + sp_w
    sp_t = int(s * 0.14)
    sp_b = body_t + int(s * 0.06)
    d.rectangle([(sp_l, sp_t), (sp_r, sp_b)], fill=ACCENT)

    # Spindle head (triangle / tool)
    tool_cx = (sp_l + sp_r) // 2
    tool_top = sp_b
    tool_bot = sp_b + int(s * 0.16)
    tool_half = int(s * 0.04)
    d.polygon(
        [(tool_cx - tool_half, tool_top),
         (tool_cx + tool_half, tool_top),
         (tool_cx, tool_bot)],
        fill=ACCENT_LIGHT,
    )

    # --- Table (horizontal bar below body) ---
    tbl_l = int(s * 0.12)
    tbl_r = int(s * 0.88)
    tbl_t = body_b + int(s * 0.04)
    tbl_b = tbl_t + int(s * 0.05)
    d.rounded_rectangle(
        [(tbl_l, tbl_t), (tbl_r, tbl_b)],
        radius=int(s * 0.02),
        fill=ACCENT,
    )

    # --- Axis arrows (X and Z labels) ---
    arrow_len = int(s * 0.10)
    arrow_w = max(2, int(s * 0.012))

    # X arrow (horizontal, bottom-left of body)
    ax = int(s * 0.22)
    ay = body_b - int(s * 0.06)
    d.line([(ax, ay), (ax + arrow_len, ay)], fill=ACCENT_LIGHT, width=arrow_w)
    # arrowhead
    d.polygon([
        (ax + arrow_len, ay),
        (ax + arrow_len - int(s*0.02), ay - int(s*0.015)),
        (ax + arrow_len - int(s*0.02), ay + int(s*0.015)),
    ], fill=ACCENT_LIGHT)

    # Z arrow (vertical, bottom-left of body)
    d.line([(ax, ay), (ax, ay - arrow_len)], fill=ACCENT_LIGHT, width=arrow_w)
    d.polygon([
        (ax, ay - arrow_len),
        (ax - int(s*0.015), ay - arrow_len + int(s*0.02)),
        (ax + int(s*0.015), ay - arrow_len + int(s*0.02)),
    ], fill=ACCENT_LIGHT)

    # --- "CNC" text in body ---
    try:
        font_size = max(10, int(s * 0.11))
        font = ImageFont.truetype("arial.ttf", font_size)
    except (OSError, IOError):
        font_size = max(10, int(s * 0.11))
        font = ImageFont.load_default(size=font_size)

    text = "CNC"
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (body_l + body_r) // 2 - tw // 2
    ty = (body_t + body_b) // 2 - th // 2
    d.text((tx, ty), text, fill=WHITE, font=font)

    # --- Small "HAAS" label across top ---
    try:
        label_font_size = max(8, int(s * 0.065))
        label_font = ImageFont.truetype("arial.ttf", label_font_size)
    except (OSError, IOError):
        label_font_size = max(8, int(s * 0.065))
        label_font = ImageFont.load_default(size=label_font_size)

    label = "HAAS"
    lbox = d.textbbox((0, 0), label, font=label_font)
    lw = lbox[2] - lbox[0]
    lx = (s // 2) - (lw // 2)
    ly = int(s * 0.04)
    d.text((lx, ly), label, fill=GREY, font=label_font)

    return img


def draw_logo(width: int, height: int) -> Image.Image:
    """Draw a wider logo variant (icon + text)."""
    icon_size = height
    icon = draw_cnc_icon(icon_size)

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    # Centre the icon in the logo canvas
    x_off = (width - icon_size) // 2
    img.paste(icon, (x_off, 0), icon)
    return img


if __name__ == "__main__":
    os.makedirs(COMPONENT_DIR, exist_ok=True)

    # --- icon.png  (256×256) + icon@2x.png (512×512) ---
    icon_256 = draw_cnc_icon(256)
    icon_512 = draw_cnc_icon(512)

    icon_256.save(os.path.join(COMPONENT_DIR, "icon.png"))
    icon_512.save(os.path.join(COMPONENT_DIR, "icon@2x.png"))

    # Also save to repo root (HACS picks these up)
    icon_256.save(os.path.join(SCRIPT_DIR, "icon.png"))
    icon_512.save(os.path.join(SCRIPT_DIR, "icon@2x.png"))

    # --- logo.png (256×256) + logo@2x.png (512×512) ---
    logo_256 = draw_cnc_icon(256)
    logo_512 = draw_cnc_icon(512)
    logo_256.save(os.path.join(COMPONENT_DIR, "logo.png"))
    logo_512.save(os.path.join(COMPONENT_DIR, "logo@2x.png"))
    logo_256.save(os.path.join(SCRIPT_DIR, "logo.png"))
    logo_512.save(os.path.join(SCRIPT_DIR, "logo@2x.png"))

    print("Generated icons and logos:")
    for name in ["icon.png", "icon@2x.png", "logo.png", "logo@2x.png"]:
        for d in [COMPONENT_DIR, SCRIPT_DIR]:
            p = os.path.join(d, name)
            if os.path.exists(p):
                sz = os.path.getsize(p)
                print(f"  {os.path.relpath(p, SCRIPT_DIR)}  ({sz} bytes)")
