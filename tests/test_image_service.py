from PIL import Image
from models.listing import Listing
from services.image_service import generar_imagen_instagram


def _make_listing():
    return Listing(
        tipo="Departamento", operacion="Renta",
        direccion="Polanco", ciudad="CDMX", estado="CDMX",
        precio=35000, recamaras=2, banos=2, m2_construidos=90,
        descripcion_agente="Lujoso depa",
        agente_nombre="Ana L", agente_telefono="5509876543", agente_email="ana@inmersiva.com",
        foto_portada="",
    )


def test_imagen_dimensions(tmp_path):
    listing = _make_listing()
    out = tmp_path / "test.jpg"
    generar_imagen_instagram(listing, None, str(out))
    img = Image.open(out)
    assert img.size == (1080, 1080)


def test_imagen_creates_file(tmp_path):
    listing = _make_listing()
    out = tmp_path / "test2.jpg"
    generar_imagen_instagram(listing, None, str(out))
    assert out.stat().st_size > 10000


from services.image_service import generar_imagen_vertical
import tempfile, os
from unittest.mock import MagicMock

def test_generar_imagen_vertical_sin_foto():
    listing = MagicMock()
    listing.tipo = "Departamento"
    listing.operacion = "Venta"
    listing.precio = 450000
    listing.moneda = "PEN"
    listing.ciudad = "Miraflores"
    listing.estado = "Lima"
    listing.recamaras = 3
    listing.banos = 2.0
    listing.m2_construidos = 120
    listing.descripcion_generada = "Hermoso departamento con vista al mar en Miraflores."
    listing.agente_nombre = "Juan Pérez"

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        out = tmp.name

    try:
        generar_imagen_vertical(listing, None, out)
        assert os.path.exists(out)
        assert os.path.getsize(out) > 10_000
    finally:
        os.unlink(out)
