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


W_VERT, H_VERT = 1080, 1920
GOLD_VERT = (212, 175, 55)
WHITE_VERT = (255, 255, 255)
DARK_BG = (15, 15, 20)
FONTS_DIR = Path(__file__).parent.parent / "static" / "fonts"
LOGO_PATH_VERT = Path(__file__).parent.parent / "static" / "img" / "logo.jpeg"


def _load_inter(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = ["Inter-Bold.otf", "Inter-Bold.ttf"] if bold else ["Inter-Regular.otf", "Inter-Regular.ttf"]
    system_fallbacks = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for name in names:
        p = FONTS_DIR / name
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    for p in system_fallbacks:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _crop_to_fit(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    ratio = max(target_w / src_w, target_h / src_h)
    new_w, new_h = int(src_w * ratio), int(src_h * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _draw_text_wrapped(draw: ImageDraw.ImageDraw, text: str, x: int, y: int,
                       max_width: int, font, fill, line_spacing: int = 8) -> int:
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    for line in lines[:2]:  # max 2 lines
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((x, y), line, font=font)
        y += (bbox[3] - bbox[1]) + line_spacing
    return y


def generar_imagen_vertical(listing, portada_path: str | None, output_path: str) -> str:
    """Genera imagen 1080x1920 (stories/reels) profesional para RRSS."""
    photo_h = int(H_VERT * 0.58)
    if portada_path and Path(portada_path).exists():
        photo = Image.open(portada_path).convert("RGB")
        photo = _crop_to_fit(photo, W_VERT, photo_h)
    else:
        photo = Image.new("RGB", (W_VERT, photo_h), (30, 45, 80))

    base = Image.new("RGB", (W_VERT, H_VERT), DARK_BG)
    base.paste(photo, (0, 0))

    # Gradient fade photo->dark
    grad = Image.new("RGBA", (W_VERT, H_VERT), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(grad)
    fade_start = int(photo_h * 0.55)
    for y in range(fade_start, photo_h + 80):
        alpha = min(255, int(255 * (y - fade_start) / (photo_h - fade_start + 80)))
        grad_draw.line([(0, y), (W_VERT, y)], fill=(DARK_BG[0], DARK_BG[1], DARK_BG[2], alpha))
    base = Image.alpha_composite(base.convert("RGBA"), grad).convert("RGB")
    draw = ImageDraw.Draw(base)

    # Logo top-left
    if LOGO_PATH_VERT.exists():
        try:
            logo = Image.open(LOGO_PATH_VERT).convert("RGBA")
            logo.thumbnail((220, 88), Image.LANCZOS)
            lw, lh = logo.size
            bg_logo = Image.new("RGBA", (lw + 20, lh + 16), (255, 255, 255, 200))
            base_rgba = base.convert("RGBA")
            base_rgba.paste(bg_logo, (30, 30), bg_logo)
            base_rgba.paste(logo, (40, 38), logo)
            base = base_rgba.convert("RGB")
            draw = ImageDraw.Draw(base)
        except Exception:
            pass

    y = photo_h - 30
    tipo_text = f"{listing.tipo.upper()} EN {listing.operacion.upper()}"
    draw.text((60, y), tipo_text, font=_load_inter(40), fill=(200, 200, 200))

    y += 58
    moneda = getattr(listing, "moneda", "PEN")
    sym = "S/." if moneda == "PEN" else "USD"
    precio_text = f"{sym} {listing.precio:,}"
    draw.text((60, y), precio_text, font=_load_inter(88, bold=True), fill=GOLD_VERT)

    y += 115
    ubi_text = f"📍 {listing.ciudad}, {listing.estado}"
    draw.text((60, y), ubi_text, font=_load_inter(38), fill=WHITE_VERT)

    y += 62
    specs = []
    if listing.recamaras:      specs.append(f"🛏  {listing.recamaras} rec.")
    if listing.banos:          specs.append(f"🚿  {listing.banos} baños")
    if listing.m2_construidos: specs.append(f"📐  {listing.m2_construidos} m²")
    if specs:
        draw.text((60, y), "    ".join(specs), font=_load_inter(34), fill=(220, 220, 220))
        y += 55

    y += 10
    draw.rectangle([(60, y), (W_VERT - 60, y + 3)], fill=GOLD_VERT)
    y += 22

    desc_raw = (listing.descripcion_generada or getattr(listing, "descripcion_agente", "") or "")
    _draw_text_wrapped(draw, desc_raw[:160], 60, y, W_VERT - 120, _load_inter(30),
                       fill=(210, 210, 210), line_spacing=10)

    footer_y = H_VERT - 160
    draw.rectangle([(0, footer_y - 10), (W_VERT, H_VERT)], fill=(10, 10, 15))
    draw.line([(0, footer_y - 10), (W_VERT, footer_y - 10)], fill=GOLD_VERT, width=2)
    agente = getattr(listing, "agente_nombre", "") or "Inmersiva"
    draw.text((60, footer_y + 10), agente, font=_load_inter(36, bold=True), fill=WHITE_VERT)
    draw.text((60, footer_y + 60), "@inmersivainmobiliaria", font=_load_inter(30), fill=GOLD_VERT)

    if LOGO_PATH_VERT.exists():
        try:
            logo_sm = Image.open(LOGO_PATH_VERT).convert("RGBA")
            logo_sm.thumbnail((120, 50), Image.LANCZOS)
            lw, lh = logo_sm.size
            base_rgba2 = base.convert("RGBA")
            base_rgba2.paste(logo_sm, (W_VERT - lw - 40, footer_y + 20), logo_sm)
            base = base_rgba2.convert("RGB")
        except Exception:
            pass

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path, "JPEG", quality=92, optimize=True)
    return output_path
