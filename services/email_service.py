import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def setup_cloudflare_email_routing(email_corporativo: str, email_personal: str) -> dict:
    """Creates a Cloudflare Email Routing forwarding rule: email_corporativo → email_personal."""
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "")
    zone_id = os.getenv("CLOUDFLARE_ZONE_ID", "")
    if not api_token or not zone_id:
        print("[EMAIL] Cloudflare no configurado — omitiendo creación de regla de reenvío")
        return {"ok": False, "error": "Cloudflare no configurado"}

    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing/rules"
    payload = {
        "name": f"Corredor {email_corporativo}",
        "enabled": True,
        "matchers": [{"type": "literal", "field": "to", "value": email_corporativo}],
        "actions": [{"type": "forward", "value": [email_personal]}],
    }
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
            timeout=10,
        )
        data = resp.json()
        if data.get("success"):
            print(f"[CF] Regla creada: {email_corporativo} → {email_personal}")
            return {"ok": True}
        print(f"[CF] Error API: {data.get('errors')}")
        return {"ok": False, "error": str(data.get("errors", ""))}
    except Exception as e:
        print(f"[CF] Excepción: {e}")
        return {"ok": False, "error": str(e)}


def enviar_credenciales_corredor(
    nombre: str,
    email_corporativo: str,
    email_personal: str,
    username: str,
    password: str,
) -> dict:
    """Sends welcome email with login credentials to the corredor's personal email."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    if not smtp_user or not smtp_password:
        print("[EMAIL] SMTP no configurado — omitiendo envío de credenciales")
        return {"ok": False, "error": "SMTP no configurado"}

    html = f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:24px;background:#0f1623;font-family:Arial,sans-serif;">
<div style="max-width:520px;margin:0 auto;background:#1B2A4A;border-radius:16px;overflow:hidden;">
  <div style="padding:32px 40px;text-align:center;border-bottom:1px solid #2d4070;">
    <img src="https://inmobiliariainmersiva.com/static/img/logo_nuevo.png"
         alt="Inmersiva" style="height:56px;margin-bottom:16px;" onerror="this.style.display='none'">
    <h1 style="margin:0;font-size:1.3rem;color:#fff;">¡Bienvenido al equipo!</h1>
    <p style="color:#C9A84C;margin:4px 0 0;letter-spacing:2px;font-size:.7rem;text-transform:uppercase;">
      Inmersiva Grupo Inmobiliario
    </p>
  </div>
  <div style="padding:32px 40px;">
    <p style="color:#ccc;margin:0 0 16px;">Hola <strong style="color:#fff;">{nombre}</strong>,</p>
    <p style="color:#aaa;margin:0 0 24px;line-height:1.6;">
      Tu cuenta de corredor ha sido activada. A partir de ahora puedes gestionar tus
      propiedades, clientes y publicaciones desde el panel de control de Inmersiva.
    </p>

    <div style="background:#111d30;border:1.5px solid #2d4070;border-radius:12px;padding:24px;margin-bottom:24px;">
      <p style="margin:0 0 16px;color:#C9A84C;font-weight:700;font-size:.75rem;
                text-transform:uppercase;letter-spacing:2px;">Tus credenciales de acceso</p>
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          <td style="color:#888;padding:8px 0;font-size:.85rem;border-bottom:1px solid #1e2e4a;">
            Email corporativo
          </td>
          <td style="color:#C9A84C;font-weight:700;text-align:right;padding:8px 0;
                     font-size:.85rem;border-bottom:1px solid #1e2e4a;">
            {email_corporativo}
          </td>
        </tr>
        <tr>
          <td style="color:#888;padding:8px 0;font-size:.85rem;border-bottom:1px solid #1e2e4a;">
            Usuario
          </td>
          <td style="color:#fff;font-weight:600;text-align:right;padding:8px 0;
                     font-size:.85rem;border-bottom:1px solid #1e2e4a;">
            {username}
          </td>
        </tr>
        <tr>
          <td style="color:#888;padding:8px 0;font-size:.85rem;">Contraseña inicial</td>
          <td style="color:#fff;font-weight:600;text-align:right;padding:8px 0;font-size:.85rem;">
            {password}
          </td>
        </tr>
      </table>
    </div>

    <p style="color:#888;font-size:.8rem;line-height:1.5;margin-bottom:28px;">
      Tu email corporativo <strong style="color:#C9A84C;">{email_corporativo}</strong>
      redirige automáticamente a este correo. Úsalo siempre al comunicarte con clientes.
      Inicia sesión con tu email corporativo y la contraseña inicial — puedes cambiarla
      desde tu perfil.
    </p>

    <div style="text-align:center;">
      <a href="https://inmobiliariainmersiva.com/login"
         style="display:inline-block;background:#C9A84C;color:#1B2A4A;font-weight:800;
                padding:14px 36px;border-radius:8px;text-decoration:none;
                letter-spacing:1px;font-size:.9rem;">
        INGRESAR AL DASHBOARD
      </a>
    </div>
  </div>
  <div style="background:#111827;padding:14px 40px;text-align:center;">
    <p style="color:#555;font-size:.72rem;margin:0;">
      © 2026 Inmersiva Grupo Inmobiliario ·
      <a href="https://inmobiliariainmersiva.com" style="color:#C9A84C;text-decoration:none;">
        inmobiliariainmersiva.com
      </a>
    </p>
  </div>
</div>
</body>
</html>
"""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Bienvenido a Inmersiva — Tus credenciales de acceso"
        msg["From"] = f"Inmersiva Grupo Inmobiliario <{smtp_from}>"
        msg["To"] = email_personal
        msg.attach(MIMEText(html, "html"))

        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_from, email_personal, msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_from, email_personal, msg.as_string())

        print(f"[EMAIL] Credenciales enviadas a {email_personal}")
        return {"ok": True}
    except Exception as e:
        print(f"[EMAIL] Error al enviar: {e}")
        return {"ok": False, "error": str(e)}
