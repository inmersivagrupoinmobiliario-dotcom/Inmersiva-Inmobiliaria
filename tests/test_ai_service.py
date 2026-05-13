from unittest.mock import patch, MagicMock
from models.listing import Listing
from services.ai_service import generar_contenido


def _make_listing():
    return Listing(
        tipo="Casa", operacion="Venta",
        direccion="Calle Pino 12", ciudad="Guadalajara", estado="Jalisco",
        precio=4200000, recamaras=3, banos=2.5, m2_construidos=180,
        amenidades=["alberca", "jardín"],
        descripcion_agente="Excelente ubicación cerca de parques",
        agente_nombre="Luis R", agente_telefono="33112233", agente_email="luis@inmersiva.com",
    )


def _mock_client(content: str):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = content
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


def test_generar_contenido_returns_two_strings():
    with patch("services.ai_service._get_client", return_value=_mock_client(
        "[DESCRIPCIÓN]\nDescripción profesional de prueba.\n\n"
        "---INSTAGRAM---\n[INSTAGRAM]\nCopy para Instagram. #BienesRaices"
    )):
        desc, copy = generar_contenido(_make_listing())
    assert len(desc) > 10
    assert "#" in copy


def test_generar_contenido_strips_markers():
    with patch("services.ai_service._get_client", return_value=_mock_client(
        "[DESCRIPCIÓN]\nTexto limpio.\n\n---INSTAGRAM---\n[INSTAGRAM]\nCopy limpio. #mx"
    )):
        desc, copy = generar_contenido(_make_listing())
    assert "[DESCRIPCIÓN]" not in desc
    assert "[INSTAGRAM]" not in copy
