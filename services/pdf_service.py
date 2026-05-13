import base64
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from models.listing import Listing

_TEMPLATES = Path(__file__).parent.parent / "templates"
_jinja = Environment(loader=FileSystemLoader(str(_TEMPLATES)))


def _img_to_b64(path: str) -> str:
    p = Path("uploads") / path
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode()


def generar_pdf(listing: Listing, output_path: str):
    portada_b64 = _img_to_b64(listing.foto_portada) if listing.foto_portada else ""
    extras_b64_list = [b for f in listing.fotos_extras if (b := _img_to_b64(f))]

    template = _jinja.get_template("pdf_template.html")
    html_str = template.render(
        listing=listing,
        portada_b64=portada_b64,
        extras_b64_list=extras_b64_list,
    )

    HTML(string=html_str, base_url=".").write_pdf(output_path)
