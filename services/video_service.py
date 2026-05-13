import base64
import json
import subprocess
import threading
from pathlib import Path
from models.listing import Listing

_video_status: dict[str, str] = {}


def _img_to_b64(path: Path) -> str:
    if path.exists():
        return base64.b64encode(path.read_bytes()).decode()
    return ""


def _render(listing: Listing, output_path: str):
    _video_status[listing.id] = "rendering"
    try:
        uploads = Path("uploads")
        photos_b64 = []
        if listing.foto_portada:
            b64 = _img_to_b64(uploads / listing.foto_portada)
            if b64:
                photos_b64.append(b64)
        for extra in listing.fotos_extras:
            b64 = _img_to_b64(uploads / extra)
            if b64:
                photos_b64.append(b64)

        props = {
            "photos": photos_b64,
            "precio": listing.precio_str,
            "ubicacion": f"{listing.ciudad}, {listing.estado}",
            "tipo": listing.tipo,
            "operacion": listing.operacion,
            "recamaras": listing.recamaras,
            "banos": listing.banos,
            "m2": listing.m2_construidos,
            "agenteNombre": listing.agente_nombre,
            "agenteTelefono": listing.agente_telefono,
            "agenteEmail": listing.agente_email,
        }

        result = subprocess.run(
            ["npx", "remotion", "render", "src/index.ts", "PropertyReel", output_path,
             "--props", json.dumps(props)],
            cwd="video",
            capture_output=True,
            text=True,
            timeout=300,
        )

        _video_status[listing.id] = "done" if result.returncode == 0 else "error"
    except Exception:
        _video_status[listing.id] = "error"


def iniciar_render(listing: Listing, output_path: str) -> None:
    t = threading.Thread(target=_render, args=(listing, output_path), daemon=True)
    t.start()


def get_status(listing_id: str) -> str:
    return _video_status.get(listing_id, "pending")
