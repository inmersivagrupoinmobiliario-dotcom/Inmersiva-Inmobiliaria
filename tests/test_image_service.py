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
