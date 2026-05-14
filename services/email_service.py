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


def enviar_consulta_propiedad(
    corredor_email: str,
    corredor_nombre: str,
    propiedad_titulo: str,
    nombre_cliente: str,
    email_cliente: str,
    telefono_cliente: str,
    mensaje: str,
) -> dict:
    """Sends property inquiry email from a potential buyer/renter to the assigned corredor."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    if not smtp_user or not smtp_password:
        print("[EMAIL] SMTP no configurado — omitiendo consulta de propiedad")
        return {"ok": False, "error": "SMTP no configurado"}

    html = f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:24px;background:#f4f6f9;font-family:Arial,sans-serif;">
<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08);">
  <div style="padding:28px 36px;background:#1B2A4A;text-align:center;">
    <h2 style="margin:0;color:#C9A84C;font-size:1.1rem;letter-spacing:1px;">NUEVA CONSULTA DE PROPIEDAD</h2>
    <p style="color:#aaa;margin:6px 0 0;font-size:.85rem;">Inmersiva Grupo Inmobiliario</p>
  </div>
  <div style="padding:28px 36px;">
    <p style="color:#333;margin:0 0 6px;">Hola <strong>{corredor_nombre}</strong>,</p>
    <p style="color:#666;margin:0 0 20px;font-size:.9rem;">Tienes una nueva consulta sobre la siguiente propiedad:</p>

    <div style="background:#f8f9fa;border-radius:10px;padding:14px 18px;margin-bottom:22px;font-size:.9rem;">
      <strong style="color:#1B2A4A;">Propiedad:</strong> {propiedad_titulo}
    </div>

    <table style="width:100%;border-collapse:collapse;font-size:.9rem;">
      <tr style="border-bottom:1px solid #f0f0f0;">
        <td style="padding:10px 0;color:#888;width:120px;">Nombre</td>
        <td style="padding:10px 0;font-weight:600;color:#1B2A4A;">{nombre_cliente}</td>
      </tr>
      <tr style="border-bottom:1px solid #f0f0f0;">
        <td style="padding:10px 0;color:#888;">Email</td>
        <td style="padding:10px 0;"><a href="mailto:{email_cliente}" style="color:#C9A84C;font-weight:600;">{email_cliente}</a></td>
      </tr>
      <tr style="border-bottom:1px solid #f0f0f0;">
        <td style="padding:10px 0;color:#888;">Teléfono</td>
        <td style="padding:10px 0;color:#333;">{telefono_cliente or '—'}</td>
      </tr>
    </table>

    <div style="margin-top:20px;background:#fffbf0;border:1.5px solid #e8c96d;border-radius:10px;padding:16px 18px;">
      <p style="margin:0 0 8px;color:#1B2A4A;font-weight:700;font-size:.82rem;text-transform:uppercase;letter-spacing:1px;">Mensaje</p>
      <p style="margin:0;color:#333;font-size:.9rem;line-height:1.6;">{mensaje}</p>
    </div>

    <div style="text-align:center;margin-top:24px;">
      <a href="mailto:{email_cliente}?subject=Re: Consulta — {propiedad_titulo}"
         style="display:inline-block;background:#C9A84C;color:#1B2A4A;font-weight:800;padding:13px 32px;border-radius:8px;text-decoration:none;font-size:.9rem;">
        Responder al cliente
      </a>
    </div>
  </div>
  <div style="background:#f8f9fa;padding:12px;text-align:center;">
    <p style="color:#aaa;font-size:.72rem;margin:0;">© 2026 Inmersiva Grupo Inmobiliario</p>
  </div>
</div>
</body></html>
"""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Nueva consulta — {propiedad_titulo}"
        msg["From"] = f"Inmersiva Grupo Inmobiliario <{smtp_from}>"
        msg["To"] = corredor_email
        msg["Reply-To"] = email_cliente
        msg.attach(MIMEText(html, "html"))

        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_from, corredor_email, msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_from, corredor_email, msg.as_string())

        print(f"[EMAIL] Consulta enviada a corredor {corredor_email}")
        return {"ok": True}
    except Exception as e:
        print(f"[EMAIL] Error al enviar consulta: {e}")
        return {"ok": False, "error": str(e)}
