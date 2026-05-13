import os
import httpx

UPLOAD_POST_URL = "https://api.upload-post.com/api/upload"


def publicar_instagram(image_path: str, caption: str) -> dict:
    api_key = os.getenv("UPLOADPOST_API_KEY")
    user = os.getenv("UPLOADPOST_USER")

    if not api_key or not user:
        return {"ok": False, "error": "UPLOADPOST_API_KEY o UPLOADPOST_USER no configurados en .env"}

    try:
        with open(image_path, "rb") as f:
            response = httpx.post(
                UPLOAD_POST_URL,
                headers={"Authorization": f"Apikey {api_key}"},
                data={"user": user, "platform[]": "instagram", "title": caption},
                files={"image": (os.path.basename(image_path), f, "image/jpeg")},
                timeout=30.0,
            )

        if response.status_code == 200:
            return {"ok": True, "data": response.json()}
        return {"ok": False, "error": f"API respondió {response.status_code}: {response.text}"}

    except Exception as e:
        return {"ok": False, "error": str(e)}
