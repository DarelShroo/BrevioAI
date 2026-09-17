# Hardening y Cabeceras de Seguridad (Runtime)

BrevioAI incluye medidas activas para evitar despliegues inseguros, concentradas en `security_runtime.py`.

## 1. Guardias de Arranque (Startup Guards)

Si la aplicación detecta que está en modo producción (`is_production_environment()`), aborta el arranque (`RuntimeError`) si:

*   Las claves `API_KEY` o `SECRET_TOKEN_KEY` son obvias (ej. `changeme`, `secret`) o demasiado cortas.
*   Falta la clave maestra de encriptación `CREDENTIAL_ENCRYPTION_KEY`.
*   Los orígenes CORS (`CORS_ORIGINS`) contienen un comodín inseguro `*` en lugar de una lista explícita.
*   El Proxy de confianza (`TRUSTED_PROXY`) está configurado para confiar en toda la internet (ej. `0.0.0.0/0`), lo cual rompería la validación real de IPs cliente para el Rate Limiting.
*   Redis no tiene configurada una contraseña ACL fuerte (`REDIS_PASSWORD`).

## 2. `SecurityHeadersMiddleware`

Inyecta cabeceras de respuesta HTTP (Response Headers) para forzar a los navegadores a aplicar políticas de seguridad:

*   `X-Content-Type-Options: nosniff` (Evita inyecciones de MIME-types).
*   `X-Frame-Options: DENY` (Previene Clickjacking). *Excepción temporal: `/examples/pdf` para demostraciones embebidas.*
*   `Referrer-Policy: strict-origin-when-cross-origin` (No filtra URLs sensibles a terceros).
*   `Strict-Transport-Security` (HSTS): Fuerza HTTPS estricto durante al menos 1 año.
*   `Permissions-Policy`: Apaga el acceso a cámara, micrófono y geolocalización desde el contexto del dominio de la API.
