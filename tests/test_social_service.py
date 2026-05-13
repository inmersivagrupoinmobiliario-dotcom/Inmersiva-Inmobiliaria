from unittest.mock import patch, MagicMock, mock_open
from services.social_service import publicar_instagram


def test_publicar_instagram_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"success": True}
    env = {"UPLOADPOST_API_KEY": "test-key", "UPLOADPOST_USER": "test-user"}
    with patch.dict("os.environ", env), \
         patch("builtins.open", mock_open(read_data=b"img")), \
         patch("services.social_service.httpx.post", return_value=mock_resp):
        result = publicar_instagram("path/to/img.jpg", "Copy de test #inmobiliaria")
    assert result["ok"] is True


def test_publicar_instagram_api_error():
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"
    with patch("services.social_service.httpx.post", return_value=mock_resp):
        result = publicar_instagram("path/to/img.jpg", "Copy")
    assert result["ok"] is False
    assert "error" in result


def test_publicar_instagram_missing_env():
    import os
    original = os.environ.pop("UPLOADPOST_API_KEY", None)
    try:
        result = publicar_instagram("img.jpg", "copy")
        assert result["ok"] is False
        assert "no configurados" in result["error"]
    finally:
        if original:
            os.environ["UPLOADPOST_API_KEY"] = original
