# Revocación de Sesiones (Denylist)

Si los Access Tokens no se validan contra la base de datos para ahorrar recursos, ¿qué ocurre si el usuario pulsa "Cerrar Sesión" o cambia su contraseña, y un atacante tiene su Access Token (que sigue siendo matemáticamente válido)?

Para solventar este agujero de seguridad, BrevioAI implementa `session_revocation.py`.

## El "Denylist" en Redis

1.  **Cierre de Sesión:** Cuando el usuario cierra sesión, el backend extrae el `jti` (Token ID) de su Access Token.
2.  **Inserción Rápida:** Escribe en Redis la clave `auth:deny:jti:<ID>` con un Tiempo de Vida (TTL) exactamente igual al tiempo que le quedara de vida natural al token (ej. 14 minutos).
3.  **Cambio de Contraseña (Invalidación Masiva):** Si el usuario cambia la contraseña, el sistema escribe en Redis `auth:deny:user:<USER_ID>` con el timestamp actual (Epoch).
4.  **Validación en cada Request:** El middleware / dependencia de autenticación lee el Token matemáticamente. SI es válido, hace un `GET` hiper-rápido a Redis (latencia < 1ms). Si el `jti` o el usuario están en la lista negra (o el token fue emitido antes del timestamp de revocación), el token es rechazado y se lanza un `401 Unauthorized`.
5.  **Limpieza Automática:** Gracias al TTL de Redis, el Denylist no crece de forma indefinida. Cuando el token pierde su validez matemática natural, se borra automáticamente de Redis.
