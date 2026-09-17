# 06 - Autenticación y Seguridad (Auth & Security)

## Visión General

BrevioAI gestiona la identidad y el acceso a los recursos mediante un sistema **Stateless (sin estado) apoyado por Redis para revocaciones rápidas**. No depende de un proveedor de identidad externo pesado (como Auth0) en su capa principal, sino que utiliza JSON Web Tokens (JWT) generados y firmados asimétricamente o simétricamente en el Backend.

### Principios de Seguridad

1.  **Fallo Abierto vs Fallo Cerrado:**
    *   *Fallo Cerrado (Fail-Closed):* Al arrancar en Producción, si las contraseñas son débiles (`changeme`, nulas, cortas), el servidor rechaza el arranque lanzando un `RuntimeError` (`security_runtime.py`).
    *   *Fallo Abierto (Fail-Open) en Lecturas:* Si Redis se cae, la comprobación de tokens revocados asume que el token es válido para no dejar sin servicio a toda la plataforma, confiando en que el Refresh Token (en MongoDB) fue invalidado.
2.  **Hardening HTTP:** Se inyectan cabeceras de seguridad estrictas (HSTS, Anti-Sniffing, CSP implícito vía X-Frame-Options) en todas las respuestas para evitar ataques CSRF y Clickjacking.
3.  **No Persistencia Permanente de Sesión (Access):** Los JWT de acceso (Access Tokens) no se guardan en la base de datos. Solo los Refresh Tokens y las Familias de Tokens (para detectar rotaciones maliciosas) se persisten.

### Sub-módulos

*   [Tokens JWT (Access & Refresh)](jwt-tokens.md)
*   [Revocación de Sesiones (Redis)](session-revocation.md)
*   [Hardening y Cabeceras de Seguridad](security-headers.md)
