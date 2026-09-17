# Bring Your Own Key (BYOK)

BrevioAI permite a los usuarios avanzados utilizar la infraestructura y el pipeline de Map/Reduce de la plataforma sin consumir el saldo comercial (Créditos), usando sus propias claves de API de los proveedores (OpenAI, Anthropic). A esto se le llama Bring Your Own Key (BYOK).

## Flujo de Seguridad y Resolución

1.  **Encriptación en Reposo:** Las claves API introducidas por el usuario en el perfil NUNCA se guardan en texto plano. El `EncryptionService` utiliza AES-256-GCM para encriptar la clave en la base de datos de MongoDB. La semilla (salt) o clave maestra (`ENCRYPTION_KEY`) reside únicamente en las variables de entorno del servidor.
2.  **`CredentialResolver`:** Cuando el `SummaryService` necesita llamar a la API, no usa una clave global. Le pregunta al `CredentialResolver`: *"Dame las credenciales para el usuario X y el modelo Y"*.
3.  **Fallback de Políticas:** El Resolver comprueba:
    *   Si el usuario tiene BYOK activo y configurado, devuelve su clave.
    *   Si no, y el plan del usuario permite el modelo, devuelve la clave maestra de la Plataforma.
    *   Si no tiene BYOK y su plan no lo cubre (o se quedó sin saldo), deniega el acceso.

## Impacto en Billing (Facturación)

Cuando la petición fluye a través del modo BYOK (`BillingMode.BYOK`):
*   El usuario recibe el coste económico en la factura directa de su proveedor (OpenAI).
*   BrevioAI le "cobra" a nivel interno 0 créditos (o una tarifa plana mínima de infraestructura) por el resumen, dependiendo de la política comercial de BYOK configurada en el servidor.
*   **Nota Anti-Abuso:** Aunque el uso sea BYOK, el *ProductLimitService* y el *Fair Scheduler* siguen limitando cuántos trabajos en paralelo puede lanzar el usuario, para no saturar las CPUs del clúster de Celery.
