from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os

NAVY      = (27, 42, 74)
NAVY_DARK = (15, 26, 56)
GOLD      = (201, 168, 76)
GOLD_DARK = (170, 138, 54)
WHITE     = (255, 255, 255)
GRAY_LIGHT = (210, 215, 225)
DARK_BG   = (12, 18, 32)

SIZE = 1080          # square Instagram
W_VERT, H_VERT = 1080, 1920   # vertical stories/reels

_ROOT     = Path(__file__).parent.parent
FONTS_DIR = _ROOT / "static" / "fonts"
LOGO_PATH = _ROOT / "static" / "img" / "logo.jpeg"


# ── Font loader ───────────────────────────────────────────────────────────────

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = (["Inter-Bold.otf", "Inter-Bold.ttf"] if bold
             else ["Inter-Regular.otf", "Inter-Regular.ttf"])
    system = ([
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ] if bold else [
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ])
    for name in names:
        p = FONTS_DIR / name
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    for p in system:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _crop_center(img: Image.Image, w: int, h: int) -> Image.Image:
    ratio = max(w / img.width, h / img.height)
    nw, nh = int(img.width * ratio), int(img.height * ratio)
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def _bottom_gradient(width: int, height: int, start_frac: float = 0.35,
                     max_alpha: int = 220) -> Image.Image:
    """Dark gradient from transparent (top) to opaque dark (bottom)."""
    grad = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(grad)
    start_y = int(height * start_frac)
    for y in range(start_y, height):
        t = (y - start_y) / (height - start_y)
        alpha = int(max_alpha * (t ** 1.3))
        draw.line([(0, y), (width, y)], fill=(*DARK_BG, alpha))
    return grad


def _draw_rounded_rect(draw: ImageDraw.ImageDraw, xy, radius: int, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def _draw_text_shadow(draw, pos, text, font, fill, shadow=(0, 0, 0), offset=2):
    draw.text((pos[0] + offset, pos[1] + offset), text, font=font, fill=(*shadow, 160))
    draw.text(pos, text, font=font, fill=fill)


def _wrap_text(draw, text: str, x: int, y: int, max_w: int, font,
               fill, line_gap: int = 8, max_lines: int = 2) -> int:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    for line in lines[:max_lines]:
        draw.text((x, y), line, font=font, fill=fill)
        _, _, _, bot = draw.textbbox((x, y), line, font=font)
        y = bot + line_gap
    return y


def _paste_logo(base: Image.Image, size=(100, 100), pos=(40, 40),
                bg_alpha=210) -> Image.Image:
    if not LOGO_PATH.exists():
        return base
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo.thumbnail(size, Image.LANCZOS)
        lw, lh = logo.size
        # Circular white background
        circle = Image.new("RGBA", (lw + 16, lh + 16), (0, 0, 0, 0))
        mask = Image.new("L", circle.size, 0)
        ImageDraw.Draw(mask).ellipse([0, 0, circle.width, circle.height], fill=bg_alpha)
        circle.paste((255, 255, 255, bg_alpha), mask=mask)
        base_rgba = base.convert("RGBA")
        base_rgba.paste(circle, pos, circle)
        base_rgba.paste(logo, (pos[0] + 8, pos[1] + 8), logo)
        return base_rgba.convert("RGB")
    except Exception:
        return base


# ── Square 1080x1080 (Instagram feed) ────────────────────────────────────────

def generar_imagen_instagram(listing, portada_path, output_path: str):
    # Base photo
    if portada_path and Path(portada_path).exists():
        base = Image.open(portada_path).convert("RGB")
        base = _crop_center(base, SIZE, SIZE)
    else:
        base = Image.new("RGB", (SIZE, SIZE), NAVY)
        # subtle navy grid texture
        draw_bg = ImageDraw.Draw(base)
        for i in range(0, SIZE, 60):
            draw_bg.line([(i, 0), (i, SIZE)], fill=(35, 52, 90), width=1)
            draw_bg.line([(0, i), (SIZE, i)], fill=(35, 52, 90), width=1)

    # Bottom gradient overlay
    grad = _bottom_gradient(SIZE, SIZE, start_frac=0.40, max_alpha=230)
    base = Image.alpha_composite(base.convert("RGBA"), grad).convert("RGB")
    draw = ImageDraw.Draw(base)

    # ── Top-left: operation badge ─────────────────────────────────────────
    op_text = f"  {listing.operacion.upper()}  "
    f_badge = _font(30, bold=True)
    bw = draw.textbbox((0, 0), op_text, font=f_badge)[2]
    bh = draw.textbbox((0, 0), op_text, font=f_badge)[3]
    badge_fill = GOLD if listing.operacion.lower() == "venta" else (50, 110, 210)
    _draw_rounded_rect(draw, [40, 40, 40 + bw + 8, 40 + bh + 10], radius=6, fill=badge_fill)
    badge_text_color = NAVY if listing.operacion.lower() == "venta" else WHITE
    draw.text((44, 44), op_text, font=f_badge, fill=badge_text_color)

    # ── Top-right: tipo ───────────────────────────────────────────────────
    tipo_text = listing.tipo.upper()
    f_tipo = _font(26)
    tw = draw.textbbox((0, 0), tipo_text, font=f_tipo)[2]
    draw.text((SIZE - tw - 44, 48), tipo_text, font=f_tipo,
              fill=(200, 205, 215))

    # ── Gold accent bar ───────────────────────────────────────────────────
    bar_y = SIZE - 355
    draw.rectangle([(56, bar_y), (56 + 64, bar_y + 4)], fill=GOLD)

    # ── Price ─────────────────────────────────────────────────────────────
    f_precio = _font(80, bold=True)
    _draw_text_shadow(draw, (56, bar_y + 18), listing.precio_str,
                      font=f_precio, fill=GOLD, offset=3)

    # ── Location ──────────────────────────────────────────────────────────
    f_ubi = _font(36)
    ubi = f"{listing.ciudad}, {listing.estado}" if listing.ciudad else listing.estado
    _draw_text_shadow(draw, (56, SIZE - 248), ubi, font=f_ubi,
                      fill=GRAY_LIGHT, offset=2)

    # ── Stats (no emojis — plain unicode bullets) ─────────────────────────
    f_stats = _font(32)
    stats = []
    if listing.recamaras:       stats.append(f"{listing.recamaras} dorm.")
    if listing.banos:           stats.append(f"{listing.banos} ban.")
    if listing.m2_construidos:  stats.append(f"{listing.m2_construidos} m²")
    if listing.estacionamientos: stats.append(f"{listing.estacionamientos} coch.")
    if stats:
        stats_text = "  ·  ".join(stats)
        draw.text((56, SIZE - 196), stats_text, font=f_stats, fill=GRAY_LIGHT)

    # ── Divider line ──────────────────────────────────────────────────────
    draw.line([(56, SIZE - 150), (SIZE - 56, SIZE - 150)],
              fill=(255, 255, 255, 60), width=1)

    # ── Brand watermark ───────────────────────────────────────────────────
    f_brand = _font(24, bold=True)
    brand = "INMERSIVA  ·  inmobiliariainmersiva.com"
    bw2 = draw.textbbox((0, 0), brand, font=f_brand)[2]
    draw.text((SIZE - bw2 - 44, SIZE - 120), brand, font=f_brand,
              fill=(*GOLD, 210))

    # ── Agente ───────────────────────────────────────────────────────────
    f_agente = _font(28)
    draw.text((56, SIZE - 110), listing.agente_nombre, font=f_agente,
              fill=(210, 215, 225))

    base = _paste_logo(base, size=(72, 72), pos=(SIZE - 116, SIZE - 132))
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path, "JPEG", quality=95, optimize=True)


# ── Vertical 1080x1920 (Stories / Reels) ─────────────────────────────────────

def generar_imagen_vertical(listing, portada_path, output_path: str) -> str:
    photo_h = int(H_VERT * 0.56)

    if portada_path and Path(portada_path).exists():
        photo = Image.open(portada_path).convert("RGB")
        photo = _crop_center(photo, W_VERT, photo_h)
    else:
        photo = Image.new("RGB", (W_VERT, photo_h), NAVY)

    base = Image.new("RGB", (W_VERT, H_VERT), DARK_BG)
    base.paste(photo, (0, 0))

    # Gradient fade photo → dark
    grad = _bottom_gradient(W_VERT, H_VERT, start_frac=0.42, max_alpha=255)
    base = Image.alpha_composite(base.convert("RGBA"), grad).convert("RGB")
    draw = ImageDraw.Draw(base)

    # ── Logo circle (top-left) ────────────────────────────────────────────
    base = _paste_logo(base, size=(80, 80), pos=(48, 48))
    draw = ImageDraw.Draw(base)

    # ── Brand name (top-left, next to logo) ──────────────────────────────
    f_brand_sm = _font(30, bold=True)
    f_brand_sub = _font(22)
    draw.text((156, 56), "INMERSIVA", font=f_brand_sm, fill=WHITE)
    draw.text((156, 94), "GRUPO INMOBILIARIO", font=f_brand_sub, fill=(*GOLD, 200))

    # ── Operation badge (top-right) ───────────────────────────────────────
    op_text = f"  {listing.operacion.upper()}  "
    f_op = _font(32, bold=True)
    ow = draw.textbbox((0, 0), op_text, font=f_op)[2]
    oh = draw.textbbox((0, 0), op_text, font=f_op)[3]
    op_fill = GOLD if listing.operacion.lower() == "venta" else (50, 110, 210)
    _draw_rounded_rect(draw, [W_VERT - ow - 56, 48, W_VERT - 48, 48 + oh + 12],
                       radius=8, fill=op_fill)
    op_text_col = NAVY if listing.operacion.lower() == "venta" else WHITE
    draw.text((W_VERT - ow - 52, 54), op_text, font=f_op, fill=op_text_col)

    # ── Tipo + ubicación (over photo, lower portion) ──────────────────────
    y = photo_h - 180
    tipo_ubi = f"{listing.tipo.upper()}  ·  {listing.ciudad}, {listing.estado}"
    draw.text((60, y), tipo_ubi, font=_font(34), fill=GRAY_LIGHT)

    # ── Gold accent bar ───────────────────────────────────────────────────
    y = photo_h - 120
    draw.rectangle([(60, y), (60 + 80, y + 5)], fill=GOLD)

    # ── Price ─────────────────────────────────────────────────────────────
    y = photo_h - 100
    _draw_text_shadow(draw, (60, y), listing.precio_str,
                      font=_font(96, bold=True), fill=GOLD, offset=3)

    # ── Stats ─────────────────────────────────────────────────────────────
    y = photo_h + 30
    specs = []
    if listing.recamaras:       specs.append(f"{listing.recamaras} Dormitorios")
    if listing.banos:           specs.append(f"{listing.banos} Baños")
    if listing.m2_construidos:  specs.append(f"{listing.m2_construidos} m² const.")
    if listing.m2_terreno:      specs.append(f"{listing.m2_terreno} m² terreno")
    if listing.estacionamientos: specs.append(f"{listing.estacionamientos} Cocheras")

    f_stat = _font(38, bold=True)
    f_stat_lbl = _font(28)
    col_gap = W_VERT // min(len(specs), 3) if specs else W_VERT
    for i, spec in enumerate(specs[:3]):
        num, *rest = spec.split(" ", 1)
        lbl = rest[0] if rest else ""
        cx = 60 + i * col_gap
        draw.text((cx, y), num, font=f_stat, fill=GOLD)
        nw = draw.textbbox((0, 0), num, font=f_stat)[2]
        draw.text((cx, y + 52), lbl, font=f_stat_lbl, fill=GRAY_LIGHT)

    if len(specs) > 3:
        y2 = y + 110
        for i, spec in enumerate(specs[3:6]):
            num, *rest = spec.split(" ", 1)
            lbl = rest[0] if rest else ""
            cx = 60 + i * col_gap
            draw.text((cx, y2), num, font=f_stat, fill=GOLD)
            draw.text((cx, y2 + 52), lbl, font=f_stat_lbl, fill=GRAY_LIGHT)
        y = y2 + 100
    else:
        y += 110

    # ── Gold divider ──────────────────────────────────────────────────────
    y += 20
    draw.rectangle([(60, y), (W_VERT - 60, y + 2)], fill=(*GOLD, 120))
    y += 24

    # ── Description snippet ───────────────────────────────────────────────
    desc = (listing.descripcion_generada or listing.descripcion_agente or "").strip()
    if desc:
        y = _wrap_text(draw, desc[:200], 60, y, W_VERT - 120,
                       _font(30), fill=(195, 200, 210), line_gap=12, max_lines=3)

    # ── Footer bar ────────────────────────────────────────────────────────
    footer_y = H_VERT - 180
    draw.rectangle([(0, footer_y), (W_VERT, H_VERT)], fill=(8, 12, 22))
    draw.rectangle([(0, footer_y), (W_VERT, footer_y + 3)], fill=GOLD)

    f_ag_name = _font(38, bold=True)
    f_ag_sub  = _font(28)
    draw.text((60, footer_y + 22), listing.agente_nombre, font=f_ag_name, fill=WHITE)
    draw.text((60, footer_y + 74), listing.agente_telefono, font=f_ag_sub, fill=(*GOLD, 200))

    base = _paste_logo(base, size=(90, 90), pos=(W_VERT - 140, footer_y + 16))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path, "JPEG", quality=93, optimize=True)
    return output_path
