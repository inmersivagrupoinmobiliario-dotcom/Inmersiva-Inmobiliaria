import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

import services.uploadpost_service as svc
from services.uploadpost_service import publicar_en_redes, UploadPostError


@pytest.fixture
def dummy_image():
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        img.save(f.name)
        yield f.name
    os.unlink(f.name)


def test_publicar_sin_api_key(dummy_image):
    svc.API_KEY = ""
    with pytest.raises(UploadPostError, match="UPLOADPOST_API_KEY"):
        publicar_en_redes("caption", dummy_image, ["instagram"])


def test_publicar_plataforma_invalida(dummy_image):
    svc.API_KEY = "test-key"
    with pytest.raises(UploadPostError, match="plataforma"):
        publicar_en_redes("caption", dummy_image, ["twitter_invalid"])


def test_publicar_imagen_no_existe():
    svc.API_KEY = "test-key"
    with pytest.raises(UploadPostError, match="no encontrada"):
        publicar_en_redes("caption", "/tmp/no_existe_12345.jpg", ["instagram"])


def test_publicar_mock_exitoso(dummy_image):
    svc.API_KEY = "test-key"

    mock_upload = MagicMock()
    mock_upload.status_code = 201
    mock_upload.json.return_value = {"id": "media-abc-123"}

    mock_post = MagicMock()
    mock_post.status_code = 201
    mock_post.json.return_value = {"id": "post-xyz-456", "status": "published", "urls": {}}

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.side_effect = [mock_upload, mock_post]

    with patch("services.uploadpost_service.httpx.Client", return_value=mock_client):
        result = publicar_en_redes("Test caption #inmersiva", dummy_image, ["instagram", "facebook"])

    assert result["post_id"] == "post-xyz-456"
    assert result["status"] == "published"
