# Tokens JWT (Access & Refresh)

El servicio `TokenService` implementa el estándar JWT (JSON Web Tokens) con una arquitectura dual.

## 1. Access Token (Token de Acceso)

*   **Ciclo de vida:** Corto (ej. 15-60 minutos).
*   **Almacenamiento:** Frontend (usualmente en memoria o en una cookie `HttpOnly`). NO se guarda en la base de datos del backend.
*   **Validación:** El Backend verifica matemáticamente la firma usando el `SECRET_TOKEN_KEY`. No hay peticiones a base de datos para validar un Access Token, lo que permite que el endpoint de estado o consultas rápidas escalen horizontalmente de forma masiva.
*   **Estructura (`payload`):** Contiene el `id` (del usuario), `typ` ("access") y un `jti` (JWT ID único).

## 2. Refresh Token (Token de Refresco)

*   **Ciclo de vida:** Largo (ej. 30-90 días).
*   **Almacenamiento:** Frontend (Cookie `HttpOnly` persistente) y en MongoDB (colección `User`).
*   **Validación:** Cuando el Access Token caduca (HTTP 401), el Frontend envía el Refresh Token al endpoint `/refresh`.
*   **Rotación y Familias (`fam`):** Por seguridad, cada vez que se usa un Refresh Token, este es invalidado y se entrega uno nuevo. Si un atacante roba un Refresh Token e intenta usarlo, el sistema detectará un re-uso en la misma "Familia" (`fam`) e **invalidará inmediatamente TODA la cadena de sesiones del usuario**, obligándolo a iniciar sesión con contraseña de nuevo.
