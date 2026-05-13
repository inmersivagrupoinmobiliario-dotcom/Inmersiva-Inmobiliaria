from models.listing import Listing


def test_listing_defaults():
    l = Listing(
        tipo="Casa",
        operacion="Venta",
        direccion="Av. Reforma 100",
        ciudad="CDMX",
        estado="CDMX",
        precio=3500000,
        descripcion_agente="Amplia y luminosa",
        agente_nombre="Carlos López",
        agente_telefono="5512345678",
        agente_email="carlos@inmersiva.com",
    )
    assert l.id != ""
    assert l.amenidades == []
    assert l.fotos_extras == []


def test_listing_precio_formateado():
    l = Listing(
        tipo="Departamento", operacion="Renta",
        direccion="Nápoles 45", ciudad="CDMX", estado="CDMX",
        precio=25000,
        descripcion_agente="Moderno y bien ubicado",
        agente_nombre="Ana M", agente_telefono="55999", agente_email="a@b.com",
    )
    assert l.precio_str == "$25,000 MXN"
