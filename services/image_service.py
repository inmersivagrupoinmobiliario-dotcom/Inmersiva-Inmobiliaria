from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os

NAVY = (27, 42, 74)
GOLD = (201, 168, 76)
WHITE = (255, 255, 255)
SIZE = 1080


def _load_font(size: int):
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _gradient_overlay(img: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for i in range(SIZE):
        alpha = int(200 * (i / SIZE) ** 1.2)
        draw.line([(0, i), (SIZE, i)], fill=(0, 0, 0, alpha))
    img = img.convert("RGBA")
    img.paste(overlay, (0, 0), overlay)
    return img


def generar_imagen_instagram(listing, portada_path: str | None, output_path: str):
    if portada_path and Path(portada_path).exists():
        base = Image.open(portada_path).convert("RGB")
        base = base.resize((SIZE, SIZE), Image.LANCZOS)
    else:
        base = Image.new("RGB", (SIZE, SIZE), NAVY)

    base = _gradient_overlay(base).convert("RGB")
    draw = ImageDraw.Draw(base)

    # Badge operacion
    badge_color = GOLD if listing.operacion == "Venta" else (60, 120, 200)
    badge_text = f"  EN {listing.operacion.upper()}  "
    font_badge = _load_font(32)
    bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.rectangle([48, 60, 48 + bw + 16, 60 + bh + 12], fill=badge_color)
    draw.text((56, 66), badge_text, font=font_badge,
              fill=NAVY if listing.operacion == "Venta" else WHITE)

    # Precio
    font_precio = _load_font(72)
    draw.text((60, SIZE - 320), listing.precio_str, font=font_precio, fill=GOLD)

    # Ubicación
    font_ubi = _load_font(38)
    draw.text((60, SIZE - 230), f"  {listing.ciudad}, {listing.estado}", font=font_ubi, fill=WHITE)

    # Stats
    font_stats = _load_font(36)
    stats = []
    if listing.recamaras:       stats.append(f"  {listing.recamaras} rec")
    if listing.banos:           stats.append(f"  {listing.banos} banos")
    if listing.m2_construidos:  stats.append(f"  {listing.m2_construidos}m2")
    draw.text((60, SIZE - 160), "   ".join(stats), font=font_stats, fill=WHITE)

    # Watermark
    font_wm = _load_font(26)
    wm = "INMERSIVA Grupo Inmobiliario"
    bbox_wm = draw.textbbox((0, 0), wm, font=font_wm)
    wm_w = bbox_wm[2] - bbox_wm[0]
    draw.text((SIZE - wm_w - 50, SIZE - 60), wm, font=font_wm, fill=GOLD)

    base.save(output_path, "JPEG", quality=95)
