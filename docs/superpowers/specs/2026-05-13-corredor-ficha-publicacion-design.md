# Diseño: Sistema de Corredores, Ficha y Publicación en RRSS
**Fecha:** 2026-05-13  
**Proyecto:** Inmersiva Grupo Inmobiliario  
**Alcance:** Gestión de corredores reales, ficha de captación, imagen vertical profesional, flujo de aprobación admin, publicación via UploadPost, dashboard de actividad.

---

## 1. Visión General

El sistema permite que **corredores reales** operen de forma autónoma: ingresan propiedades, generan fichas visuales verticales (formato redes sociales), y las envían al admin para aprobación. El admin aprueba o rechaza con comentarios, y al aprobar, el contenido se publica automáticamente en Instagram, Facebook, WhatsApp y TikTok via UploadPost API, y también aparece en el portal público.

### Flujo completo

```
Corredor → llena ficha → genera imagen vertical → solicita publicación
                                                          ↓
Admin → ve cola de aprobación → aprueba (con comentario opcional)
                                          ↓
              UploadPost API → publica en RRSS simultáneamente
                                          ↓
              Portal público → propiedad aparece automáticamente
```

---

## 2. Base de Datos — Cambios a `db_models.py`

### 2.1 Tabla nueva: `solicitudes_corredor`
Para auto-registro de corredores pendientes de aprobación.

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | Integer PK | — |
| `nombre` | String(100) | Nombre completo |
| `email` | String(100) unique | Email de contacto |
| `telefono` | String(30) | Teléfono |
| `mensaje` | Text | Por qué quiere unirse |
| `estado` | String(20) | `Pendiente` / `Aprobado` / `Rechazado` |
| `created_at` | DateTime | — |

### 2.2 Modificaciones a `Corredor`
Agregar campos de perfil profesional:
- `foto_perfil` — String(300), path a imagen subida
- `bio` — Text, descripción breve del corredor
- `instagram` — String(100), usuario de Instagram
- `whatsapp` — String(30), número con código de país

### 2.3 Modificaciones a `PostRRSS`
Tabla ya existe; agregar campos para el flujo de aprobación y publicación:

| Campo nuevo | Tipo | Descripción |
|---|---|---|
| `listing_id` | String(36) | FK a la ficha JSON (UUID) |
| `titulo` | String(200) | Título de la propiedad |
| `imagen_url` | String(500) | Path/URL de imagen vertical generada |
| `estado` | String(20) | `Pendiente` / `Aprobado` / `Rechazado` / `Publicado` |
| `comentario_admin` | Text | Feedback del admin al corredor |
| `redes` | String(200) | CSV: `instagram,facebook,whatsapp,tiktok` |
| `upload_post_id` | String(100) | ID retornado por UploadPost al publicar |
| `publicado_at` | DateTime | Timestamp de publicación efectiva |
| `caption` | Text | Texto generado para la publicación |

---

## 3. Gestión de Corredores

### 3.1 Auto-registro (nuevo)
- Ruta pública: `GET/POST /corredor/registro`
- Template nuevo: `registro_corredor.html`
- Al enviar → crea registro en `solicitudes_corredor` con estado `Pendiente`
- El corredor ve pantalla de confirmación: "Tu solicitud fue enviada, te contactaremos pronto."

### 3.2 Creación por Admin (mejora al dashboard existente)
- El admin ya puede crear corredores desde `/dashboard`
- Mejorar el formulario existente para incluir: foto_perfil, bio, instagram, whatsapp
- Ruta existente: `POST /admin/crear-corredor`

### 3.3 Aprobación de solicitudes por Admin
- Nueva sección en `dashboard_empresa.html`: "Solicitudes de corredores"
- Muestra tabla de `solicitudes_corredor` con estado `Pendiente`
- Botón "Aprobar" → crea cuenta en `corredores` y actualiza solicitud a `Aprobado`
- Botón "Rechazar" → actualiza solicitud a `Rechazado`
- Rutas: `POST /admin/solicitud/{id}/aprobar` y `POST /admin/solicitud/{id}/rechazar`

---

## 4. Ficha de Captación — Sin cambios al form

El formulario (`form.html`) ya tiene 80+ campos y funciona bien. No se modifica. Lo que sí cambia es lo que ocurre **después** de llenarlo:

1. El corredor llena la ficha → se genera PDF y contenido IA (ya funciona)
2. **Nuevo:** aparece botón "Generar imagen para redes sociales"
3. **Nuevo:** aparece botón "Solicitar publicación" que envía a la cola de admin

---

## 5. Imagen Vertical Profesional

### 5.1 Especificaciones técnicas
- **Formato:** 1080 × 1920 px (9:16 — stories/reels) generado con Pillow
- **Output:** JPEG 90% quality, guardado en `generated/{listing_id}/social_vertical.jpg`
- **Generador:** `services/image_service.py` — reescribir completamente

### 5.2 Estructura visual de la imagen

```
┌─────────────────────────────┐
│  Logo Inmersiva (top-left)  │ ← 60px, blanco sobre overlay
│                             │
│   FOTO PRINCIPAL            │ ← ocupa 55% del alto
│   (foto_portada del listing)│
│                             │
├─────────────────────────────┤
│ GRADIENT OVERLAY (oscuro)   │
│                             │
│  CASA EN VENTA              │ ← tipo + operación, bold 52px
│  S/. 450,000                │ ← precio, bold 72px, color dorado
│                             │
│  📍 Miraflores, Lima        │ ← ciudad/distrito, 36px
│  🛏 3   🚿 2   📐 120m²    │ ← specs, 32px con íconos
│                             │
│  ─────────────────────────  │ ← línea divisoria dorada
│                             │
│  Descripción breve...       │ ← primeros 120 chars del copy IA
│  (máx 2 líneas, 28px)       │
│                             │
├─────────────────────────────┤
│  [Foto corredor] Nombre     │ ← avatar circular 80px + nombre
│  📞 +51 999 999 999         │ ← teléfono del corredor
│  @inmersivainmobiliaria     │ ← handle de Instagram fijo
└─────────────────────────────┘
```

### 5.3 Paleta de colores profesional
- Fondo overlay: `rgba(0, 0, 0, 0.65)` sobre foto
- Precio: `#D4AF37` (dorado)
- Línea divisoria: `#D4AF37`
- Texto principal: `#FFFFFF`
- Texto secundario: `rgba(255,255,255,0.85)`
- Fuentes: `Inter Bold` para títulos, `Inter Regular` para cuerpo (descargar en static/fonts/)

### 5.4 Ruta
- `POST /generar-imagen-vertical/{listing_id}` → genera imagen y retorna URL
- La imagen se muestra en `results.html` con botón de descarga

---

## 6. Flujo de Aprobación

### 6.1 Corredor solicita publicación
- En `results.html` (página de resultados de la ficha): botón "Solicitar publicación en redes"
- Modal con checklist de redes: Instagram ✓ Facebook ✓ WhatsApp ✓ TikTok
- Al confirmar → `POST /corredor/solicitar-publicacion/{listing_id}`
- Crea registro en `PostRRSS` con estado `Pendiente`
- El corredor ve en su dashboard: sección "Mis publicaciones" con estado de cada post

### 6.2 Admin revisa y decide
- Dashboard admin: sección "Cola de aprobación" — tabla con posts `Pendiente`
- Cada fila muestra: miniatura imagen vertical, corredor, precio, ciudad, fecha solicitud
- Botón "Aprobar" → modal con campo de comentario opcional → aprueba y publica
- Botón "Rechazar" → modal con campo de comentario obligatorio → rechaza y notifica

### 6.3 Publicación automática al aprobar
- `POST /admin/post/{post_id}/aprobar`
- Actualiza `PostRRSS.estado = "Aprobado"`
- Llama a `services/uploadpost_service.py` → publica en redes seleccionadas
- Si UploadPost responde OK → actualiza estado a `"Publicado"`, guarda `upload_post_id` y `publicado_at`
- También crea/actualiza `PropiedadPublica` (igual que el flujo existente en `/admin/publicar-ficha`)

### 6.4 El corredor ve el resultado
- Dashboard corredor: sección "Mis publicaciones" muestra estado actualizado
- Si `Publicado`: muestra fecha, redes, y enlace a la propiedad en el portal
- Si `Rechazado`: muestra comentario del admin en rojo con botón "Corregir y reenviar"

---

## 7. Integración UploadPost API

### 7.1 Nuevo servicio: `services/uploadpost_service.py`

```python
# Endpoint base: https://api.uploadpost.co/v1
# Auth: Bearer token via env var UPLOADPOST_API_KEY

def publicar_post(caption: str, imagen_path: str, redes: list[str]) -> dict:
    # Sube imagen a UploadPost
    # Publica en las redes especificadas
    # Retorna {"post_id": "...", "status": "published", "urls": {...}}
```

### 7.2 Variables de entorno requeridas
```
UPLOADPOST_API_KEY=tu_api_key_aqui
```

### 7.3 Caption generado automáticamente
El caption se arma a partir del `copy_instagram` generado por IA (ya existe), más:
- Precio y tipo de propiedad
- Dirección/ciudad
- Hashtags: `#InmersivaInmobiliaria #BienesRaices #InmobiliariaPeru #Propiedad`
- Handle del corredor si tiene Instagram configurado

### 7.4 Manejo de errores
- Si UploadPost falla: post queda en estado `"Aprobado"` (no `"Publicado"`), se loguea el error
- Admin ve indicador de error con botón "Reintentar publicación"
- No se revierte la aprobación — el contenido sigue apareciendo en el portal

---

## 8. Dashboard Admin — Actividad Completa

### 8.1 Secciones del dashboard empresa (mejoras a `dashboard_empresa.html`)

**Panel de estadísticas (top)**
- Total corredores activos
- Fichas creadas este mes
- Posts pendientes de aprobación (badge rojo si > 0)
- Posts publicados este mes

**Cola de aprobación** (prioridad visual alta)
- Tabla: imagen miniatura | corredor | tipo + ciudad | precio | fecha solicitud | acciones
- Ordenado por fecha (más antiguo primero)
- Filtros: Por corredor, por red social, por fecha

**Actividad de corredores**
- Tabla por corredor: nombre | fichas creadas | posts solicitados | posts publicados | último acceso
- Expandible: al hacer clic en un corredor, muestra sus fichas y posts con estado

**Propiedades publicadas**
- Lista de `PropiedadPublica` con opción de destacar/despublicar (ya existe, se mantiene)

**Solicitudes de registro**
- Tabla de `solicitudes_corredor` con estado Pendiente | Aprobado | Rechazado
- Botones aprobar/rechazar inline

### 8.2 Dashboard corredor (mejoras a `dashboard_corredor.html`)

**Mis fichas**
- Lista de fichas del corredor con acciones: Ver PDF, Ver imagen, Solicitar publicación
- Estado de publicación: Sin solicitar | Pendiente | Aprobado | Publicado | Rechazado

**Mis publicaciones**
- Historial de posts: imagen miniatura | redes | estado | fecha | comentario admin
- Si rechazado: comentario del admin + botón "Corregir y reenviar"

**Mi perfil**
- Formulario editable: foto, bio, instagram, whatsapp
- Ruta: `GET/POST /corredor/perfil`

---

## 9. Portal Público — Sin cambios estructurales

El portal ya funciona y muestra `PropiedadPublica`. El único cambio: al aprobar un post en el flujo de publicación, se crea automáticamente la `PropiedadPublica`, por lo que ya no es necesario que el admin haga este paso por separado. El portal se alimenta solo.

---

## 10. Archivos a Crear / Modificar

| Archivo | Acción | Descripción |
|---|---|---|
| `models/db_models.py` | Modificar | Agregar `SolicitudCorredor`, campos a `Corredor`, campos a `PostRRSS` |
| `services/image_service.py` | Reescribir | Imagen vertical 1080×1920 profesional con Pillow |
| `services/uploadpost_service.py` | Crear | Cliente UploadPost API |
| `main.py` | Modificar | Agregar ~15 rutas nuevas en secciones organizadas |
| `templates/dashboard_empresa.html` | Modificar | Cola aprobación, actividad corredores, solicitudes registro |
| `templates/dashboard_corredor.html` | Modificar | Mis publicaciones, estado posts, mi perfil |
| `templates/results.html` | Modificar | Agregar imagen vertical + botón solicitar publicación |
| `templates/registro_corredor.html` | Crear | Formulario auto-registro corredor |
| `static/fonts/` | Crear | Inter Bold + Regular para imagen vertical |
| `requirements.txt` | Modificar | Agregar `httpx` si no está (para UploadPost HTTP calls) |

---

## 11. Orden de Implementación

1. **DB:** Agregar modelos y migrar (`SolicitudCorredor`, campos nuevos)
2. **Image service:** Reescribir generador imagen vertical profesional + ruta
3. **UploadPost service:** Integrar API y probar con cuenta sandbox
4. **Flujo corredor:** Registro propio, solicitud publicación, dashboard actualizado
5. **Flujo admin:** Cola aprobación, aprobar/rechazar, publicación automática
6. **Dashboard admin:** Actividad completa, estadísticas, solicitudes
7. **Tests:** Actualizar suite existente para cubrir nuevos endpoints
8. **Deploy:** Push a main → Coolify redespliega automáticamente

---

## 12. Variables de Entorno Requeridas en Producción

```env
# Existentes
EMPRESA_USER=admin
EMPRESA_PASS=...
DATABASE_URL=postgresql://...
SESSION_SECRET=...
SECRET_KEY=...

# Nuevas
UPLOADPOST_API_KEY=...
```

---

## Criterios de Éxito

- [ ] Un corredor real puede registrarse, ser aprobado y acceder al sistema
- [ ] El corredor llena una ficha y genera una imagen vertical 1080×1920 profesional
- [ ] El corredor solicita publicación desde su dashboard
- [ ] El admin ve la cola de aprobación y puede aprobar con comentario
- [ ] Al aprobar, UploadPost publica en las redes seleccionadas automáticamente
- [ ] La propiedad aparece en el portal público inmediatamente
- [ ] El admin puede ver toda la actividad de todos los corredores desde su dashboard
