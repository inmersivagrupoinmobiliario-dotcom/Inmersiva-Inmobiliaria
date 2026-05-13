import base64
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from models.listing import Listing

_ROOT = Path(__file__).parent.parent
_TEMPLATES = _ROOT / "templates"
_STATIC = _ROOT / "static"
_UPLOADS = _ROOT / "uploads"
_jinja = Environment(loader=FileSystemLoader(str(_TEMPLATES)))


def _to_b64(path: Path) -> str:
    if path and path.exists():
        return base64.b64encode(path.read_bytes()).decode()
    return ""


def generar_pdf(listing: Listing, output_path: str):
    portada_b64 = _to_b64(_UPLOADS / listing.foto_portada) if listing.foto_portada else ""
    extras_b64 = [b for f in listing.fotos_extras if (b := _to_b64(_UPLOADS / f))]
    logo_b64 = _to_b64(_STATIC / "img" / "logo.jpeg")

    template = _jinja.get_template("pdf_template.html")
    html_str = template.render(
        listing=listing,
        portada_b64=portada_b64,
        extras_b64_list=extras_b64,
        logo_b64=logo_b64,
    )

    HTML(string=html_str, base_url=str(_STATIC)).write_pdf(output_path)
