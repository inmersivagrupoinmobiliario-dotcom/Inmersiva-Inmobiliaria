from pathlib import Path
from models.listing import Listing
from services.pdf_service import generar_pdf


def _make_listing():
    return Listing(
        tipo="Casa", operacion="Venta",
        direccion="Calle Verde 10", ciudad="Monterrey", estado="NL",
        precio=5000000, recamaras=4, banos=3, m2_construidos=220,
        amenidades=["Alberca", "Jardín"],
        descripcion_agente="Propiedad única",
        agente_nombre="María G", agente_telefono="8112345678", agente_email="m@inmersiva.com",
        foto_portada="",
        descripcion_generada="Descripción profesional de prueba.",
        copy_instagram="Copy de instagram #test",
    )


def test_generar_pdf_creates_file(tmp_path):
    listing = _make_listing()
    out = tmp_path / "test.pdf"
    generar_pdf(listing, str(out))
    assert out.exists()
    assert out.stat().st_size > 1000
