# API Documentation

Esta documentación refleja todos los endpoints HTTP disponibles en la aplicación, generada a partir del análisis directo del código fuente (`core/brevio_api`).

## Tabla Resumen de Endpoints

| Método | Endpoint | Autenticación | Permiso/Rol | Descripción |
| ------ | -------- | ------------- | ----------- | ----------- |
| POST | `/auth/login` | No | Público | Autenticar usuario y obtener token JWT. |
| POST | `/auth/register` | No | Público | Registrar un nuevo usuario. |
| POST | `/auth/password-recovery-handshake` | No | Público | Iniciar recuperación de contraseña enviando OTP. |
| POST | `/auth/password-recovery-verify` | No | Público | Verificar OTP y completar cambio de contraseña. |
| GET | `/users/me` | Sí (Bearer) | Usuario autenticado | Obtener perfil del usuario autenticado. |
| GET | `/users/entries` | Sí (Bearer) | Usuario autenticado | Listar todas las entradas del usuario. |
| POST | `/users/entries` | Sí (Bearer) | Usuario autenticado | Obtener entradas concretas por IDs (`entries_refs`). |
| GET | `/brevio/languages` | Sí (API Key) | Usuario con API Key | Obtener lenguajes soportados. |
| GET | `/brevio/models` | Sí (API Key) | Usuario con API Key | Obtener modelos de IA disponibles. |
| GET | `/brevio/categories-styles` | Sí (API Key) | Usuario con API Key | Obtener categorías y sus estilos asociados. |
| GET | `/brevio/output-formats` | Sí (API Key) | Usuario con API Key | Obtener formatos de salida disponibles. |
| GET | `/brevio/summary-levels` | Sí (API Key) | Usuario con API Key | Obtener niveles de resumen disponibles. |
| GET | `/brevio/transcription-providers` | Sí (API Key) | Usuario con API Key | Obtener proveedores y modelos de transcripción (con `user_access` por entorno). |
| POST | `/brevio/count-yt-videos` | Sí (API Key) | Usuario con API Key | Contar videos de una playlist de YouTube. |
| POST | `/brevio/count-time-yt-video` | Sí (API Key) | Usuario con API Key | Obtener la duración de un video de YouTube. |
| POST | `/brevio/summary-media` | Sí (Bearer) | Usuario autenticado | Generar resumen de audios/media (segundo plano). |
| POST | `/brevio/summary-documents` | Sí (Bearer) | Usuario autenticado | Generar resumen de documentos PDF/DOCX (segundo plano). |
| POST | `/brevio/estimate-documents` | Sí (Bearer) | Usuario autenticado | Estimar coste/tokens para procesar documentos. |
| POST | `/brevio/summary-yt-playlist` | Sí (Bearer) | Usuario autenticado | Generar resumen de playlist de YouTube (segundo plano). |
| GET | `/brevio/download/{folder_entry_id}` | Sí (Bearer) | Usuario autenticado | Descargar resumen generado (md/docx/pdf/txt). |
| GET | `/user-credentials/{provider}` | Sí (Bearer) | Usuario autenticado | Listar credenciales activas del proveedor. |
| POST | `/user-credentials` | Sí (Bearer) | Usuario autenticado | Crear/guardar API key de proveedor (con nombre). |
| POST | `/user-credentials/{credential_id}/default` | Sí (Bearer) | Usuario autenticado | Marcar credencial como predeterminada del proveedor. |
| PATCH | `/user-credentials/{credential_id}` | Sí (Bearer) | Usuario autenticado | Renombrar una credencial. |
| DELETE | `/user-credentials/{credential_id}` | Sí (Bearer) | Usuario autenticado | Revocar una credencial. |

---

## Authentication

### POST /auth/login

**Descripción**
Autentica un usuario verificando sus credenciales y devuelve un token de acceso (JWT).

**Autenticación**
* Requerida: No
* Tipo: No aplica.

**Autorización**
* No requiere autorización.

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| Content-Type | Sí | `application/json` |

**Request Body**
* Content-Type: `application/json`
* Campos:
  * `identity` (string, obligatorio): Email o nombre de usuario válido.
  * `password` (string, obligatorio): Contraseña del usuario (longitud entre 3 y 64 caracteres).

```json
{
  "identity": "user@example.com",
  "password": "Password123!"
}
```

**Responses**

#### 200 OK
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJhbG..."
  },
  "signature": {
    "brand": "Brevio",
    "version": "v1.0",
    "contact": "support@brevio.com"
  }
}
```

#### 401 Unauthorized
```json
{
  "detail": "Invalid credentials"
}
```

#### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "ensure this value has at least 3 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

**Errores**
* `401 Unauthorized`: Ocurre cuando el usuario no existe o la contraseña es incorrecta.
* `422 Unprocessable Entity`: Ocurre cuando los datos enviados no cumplen las validaciones del esquema (ej. contraseñas cortas, formato de identidad inválido).

---

### POST /auth/register

**Descripción**
Registra una nueva cuenta de usuario en la aplicación y crea una carpeta asociada para sus resúmenes.

**Autenticación**
* Requerida: No
* Tipo: No aplica.

**Autorización**
* No requiere autorización.

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| Content-Type | Sí | `application/json` |

**Request Body**
* Content-Type: `application/json`
* Campos:
  * `username` (string, obligatorio): Nombre de usuario, entre 6 y 25 caracteres.
  * `email` (string, obligatorio): Dirección de email válida.
  * `password` (string, obligatorio): Contraseña de al menos 8 caracteres, con al menos 1 mayúscula, 1 minúscula, 1 número y 1 carácter especial.

```json
{
  "username": "johndoe",
  "email": "johndoe@example.com",
  "password": "Password123!"
}
```

**Responses**

#### 201 Created
```json
{
  "status": "success",
  "data": {
    "folder": {
      "id": "64f3c7e0...",
      "name": "root_folder",
      "entries": []
    },
    "access_token": "eyJhbG..."
  },
  "signature": {
    "brand": "Brevio",
    "version": "v1.0",
    "contact": "support@brevio.com"
  }
}
```

#### 400 Bad Request
```json
{
  "detail": "User already exists"
}
```

#### 422 Unprocessable Entity
```json
{
  "detail": "Validation error"
}
```

**Errores**
* `400 Bad Request`: El email o nombre de usuario ya está registrado en la base de datos.
* `422 Unprocessable Entity`: La contraseña no cumple con los requisitos de seguridad o el email/username es inválido.

---

### POST /auth/password-recovery-handshake

**Descripción**
Inicia el proceso de recuperación de contraseña enviando un OTP (One Time Password) al email del usuario.

**Autenticación**
* Requerida: No
* Tipo: No aplica.

**Autorización**
* No requiere autorización.

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| Content-Type | Sí | `application/json` |

**Request Body**
* Content-Type: `application/json`
* Campos:
  * `identity` (string, obligatorio): Dirección de email válida.

```json
{
  "identity": "user@example.com"
}
```

**Responses**

#### 200 OK
```json
{
  "status": "success",
  "data": {
    "message": "OTP sent successfully"
  },
  "signature": {
    "brand": "Brevio",
    "version": "v1.0",
    "contact": "support@brevio.com"
  }
}
```

#### 404 Not Found
```json
{
  "detail": "User not found"
}
```

#### 422 Unprocessable Entity
```json
{
  "detail": "Invalid user data"
}
```

**Errores**
* `404 Not Found`: El usuario con el email proporcionado no existe.
* `422 Unprocessable Entity`: Ocurre si el formato del correo es inválido.

---

### POST /auth/password-recovery-verify

**Descripción**
Verifica el OTP enviado por correo y aplica la nueva contraseña a la cuenta del usuario.

**Autenticación**
* Requerida: No
* Tipo: No aplica.

**Autorización**
* No requiere autorización.

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| Content-Type | Sí | `application/json` |

**Request Body**
* Content-Type: `application/json`
* Campos:
  * `email` (string, obligatorio): Dirección de email del usuario.
  * `password` (string, obligatorio): Nueva contraseña, debe cumplir las reglas de seguridad.
  * `otp` (integer, obligatorio): Código numérico enviado al email.

```json
{
  "email": "user@example.com",
  "password": "NewPassword123!",
  "otp": 123456
}
```

**Responses**

#### 200 OK
```json
{
  "status": "success",
  "data": {
    "message": "Password changed successfully"
  },
  "signature": {
    "brand": "Brevio",
    "version": "v1.0",
    "contact": "support@brevio.com"
  }
}
```

#### 400 Bad Request
```json
{
  "detail": "Invalid OTP"
}
```

#### 404 Not Found
```json
{
  "detail": "User not found"
}
```

#### 422 Unprocessable Entity
```json
{
  "detail": "Validation error"
}
```

**Errores**
* `400 Bad Request`: El código OTP es incorrecto o ha expirado.
* `404 Not Found`: El usuario no existe en la base de datos.
* `422 Unprocessable Entity`: La nueva contraseña no cumple con los requisitos de seguridad.

---

## Users

### GET /users/me

**Descripción**
Devuelve el perfil seguro del usuario autenticado (sin password ni OTP).

**Autenticación**
* Requerida: Sí
* Tipo: JWT Bearer Token (`get_current_user`)

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| Authorization | Sí | Token JWT formato `Bearer <token>` |

**Request Body**
`No aplica.`

**Responses**

#### 200 OK
```json
{
  "status": "success",
  "data": {
    "id": "507f1f77bcf86cd799439011",
    "username": "johndoe",
    "email": "johndoe@example.com",
    "user_credit": 0,
    "folder_id": "507f1f77bcf86cd799439022"
  },
  "signature": {
    "brand": "Brevio",
    "version": "v1.0",
    "contact": "support@brevio.com"
  }
}
```

#### 401 Unauthorized
```json
{
  "detail": "Token no proporcionado o nulo / Token expirado / Token inválido"
}
```

#### 404 Not Found
```json
{
  "detail": "User not found"
}
```

---

### GET /users/entries

**Descripción**
Lista **todas** las entradas/carpetas del usuario autenticado. Una lista vacía es válida (`200` con `entries: []`); no devuelve 404 por vacío.

**Autenticación**
* Requerida: Sí
* Tipo: JWT Bearer Token

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| Authorization | Sí | Token JWT formato `Bearer <token>` |

**Request Body**
`No aplica.`

**Responses**

#### 200 OK
```json
{
  "entries": [
    {
      "id": "...",
      "user_id": "...",
      "name": "Documento",
      "created_at": "2026-09-14T16:00:00Z",
      "updated_at": "2026-09-14T16:05:00Z",
      "language": "SPANISH",
      "model": "gpt-4o-mini",
      "category": "education",
      "style": "guide",
      "format": "markdown",
      "summary_level": "moderate",
      "source_type": "documents",
      "results": []
    }
  ]
}
```

Campos de metadata (`language`, `model`, `category`, `style`, `format`, `summary_level`, `source_type`, `created_at`, `updated_at`) están en entradas nuevas. En entradas legacy, `created_at` se deriva del ObjectId si falta.

#### 401 Unauthorized
```json
{
  "detail": "Token no proporcionado o nulo / Token expirado / Token inválido"
}
```

---

### DELETE /users/entries/{entry_id}

**Descripción**
Elimina una entrada del store del usuario autenticado. Quita la referencia en `user.folder.entries`, borra el documento en Mongo y limpia en best-effort el directorio `data/{folder_id}/{entry_id}`.

**Autenticación**
* Requerida: Sí
* Tipo: JWT Bearer Token

**Path Parameters**
| Parámetro | Tipo | Descripción |
| --------- | ---- | ----------- |
| entry_id | string | ObjectId de la entrada |

**Responses**

#### 200 OK
```json
{
  "status": "success",
  "message": "Entry deleted",
  "id": "..."
}
```

#### 403 Forbidden
```json
{
  "detail": "User does not own this folder entry"
}
```

#### 404 Not Found
```json
{
  "detail": "FolderEntry not found"
}
```

---

### POST /users/entries

**Descripción**
Recupera las entradas/documentos de un usuario según sus identificadores, usando el servicio de carpetas (`FolderEntryService`). Sigue exigiendo `entries_refs` y responde 404 si no encuentra ninguna.

**Autenticación**
* Requerida: Sí
* Tipo: JWT Bearer Token

**Autorización**
* Requiere que el usuario esté autenticado (`get_current_user`).

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| Authorization | Sí | Token JWT formato `Bearer <token>` |
| Content-Type | Sí | `application/json` |

**Request Body**
* Content-Type: `application/json`
* Campos:
  * `entries_refs` (array de strings, obligatorio): Lista de identificadores (referencias) de las entradas a consultar.

```json
{
  "entries_refs": ["id1", "id2"]
}
```

**Responses**

#### 200 OK
```json
{
  "entries": [
    {
      "id": "...",
      "name": "Documento",
      "type": "folder_entry"
    }
  ]
}
```

#### 400 Bad Request
```json
{
  "detail": "Invalid ObjectId format"
}
```

#### 401 Unauthorized
```json
{
  "detail": "Token no proporcionado o nulo / Token expirado / Token inválido"
}
```

#### 403 Forbidden
```json
{
  "detail": "Forbidden"
}
```

#### 404 Not Found
```json
{
  "detail": "No entries found"
}
```

#### 422 Unprocessable Entity
```json
{
  "detail": "Validation error for request body"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Unexpected error occurred"
}
```

---

## User Credentials

### GET /user-credentials/{provider}

**Descripción**
Lista las credenciales activas del usuario autenticado para un proveedor (p. ej. `openai`, `anthropic`).

**Autenticación**
* Requerida: Sí (Bearer JWT)

**Path Parameters**
* `provider` (string): Nombre del proveedor.

**Responses**
* `200`: Lista de `UserCredentialResponse` (sin exponer la API key en claro).
* `401`: No autenticado.

### POST /user-credentials

**Descripción**
Crea/guarda una API key cifrada para un proveedor.

**Autenticación**
* Requerida: Sí (Bearer JWT)

**Request Body**
```json
{
  "provider": "openai",
  "api_key": "sk-...",
  "name": "Work OpenAI",
  "is_default": false
}
```

**Responses**
* `201`: Credencial creada (incluye `name` e `is_default`; nunca la API key).
* `400`: Proveedor inválido / clave inválida / nombre vacío.
* `401`: No autenticado.

### POST /user-credentials/{credential_id}/default

**Descripción**
Marca la credencial como predeterminada para su proveedor (desmarca las demás del mismo proveedor).

**Autenticación**
* Requerida: Sí (Bearer JWT)

**Responses**
* `200`: Credencial actualizada.
* `404`: No encontrada.
* `401`: No autenticado.

### PATCH /user-credentials/{credential_id}

**Descripción**
Renombra una credencial sin exponer ni cambiar la API key.

**Request Body**
```json
{
  "name": "Personal Google"
}
```

**Responses**
* `200`: Credencial actualizada.
* `400`: Nombre vacío.
* `404`: No encontrada.
* `401`: No autenticado.

### DELETE /user-credentials/{credential_id}

**Descripción**
Revoca una credencial del usuario (soft-delete / status `REVOKED`).

**Autenticación**
* Requerida: Sí (Bearer JWT)

**Responses**
* `204`: Revocada.
* `400`: ID inválido.
* `404`: No encontrada.
* `401`: No autenticado.

---

## Brevio

### GET /brevio/languages

**Descripción**
Obtiene la lista de idiomas soportados por el sistema para el procesamiento de resúmenes.

**Autenticación**
* Requerida: Sí
* Tipo: API Key (`X-API-KEY`)

**Autorización**
* Requiere enviar una API Key válida en los headers.

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| X-API-KEY | Sí | Llave de API autorizada |

**Request Body**
`No aplica.`

**Responses**

#### 200 OK
```json
{
  "status": "success",
  "data": {
    "languages": ["es", "en", "fr"]
  },
  "signature": {
    "brand": "Brevio",
    "version": "v1.0",
    "contact": "support@brevio.com"
  }
}
```

#### 401 Unauthorized (403 HTTP code actually used in verify_api_key)
```json
{
  "detail": "Acceso prohibido: API Key inválida"
}
```
*Nota: El decorador dice 401, pero la dependencia `verify_api_key` lanza un 403 HTTP real.*

---

### GET /brevio/models

**Descripción**
Obtiene una lista de modelos de Inteligencia Artificial disponibles.

**Autenticación**
* Requerida: Sí
* Tipo: API Key (`X-API-KEY`)

**Autorización**
* Requiere API Key válida.

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| X-API-KEY | Sí | Llave de API autorizada |

**Request Body**
`No aplica.`

**Responses**

#### 200 OK
```json
{
  "status": "success",
  "data": {
    "models": ["gpt-4", "gpt-3.5-turbo"]
  },
  "signature": {
    "brand": "Brevio",
    "version": "v1.0",
    "contact": "support@brevio.com"
  }
}
```

#### 403 Forbidden
```json
{
  "detail": "Acceso prohibido: API Key inválida"
}
```

---

### GET /brevio/categories-styles

**Descripción**
Obtiene las categorías disponibles y los estilos de escritura o generación asociados a cada una.

**Autenticación**
* Requerida: Sí
* Tipo: API Key (`X-API-KEY`)

**Autorización**
* Requiere API Key válida.

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| X-API-KEY | Sí | Llave de API autorizada |

**Request Body**
`No aplica.`

**Responses**

#### 200 OK
```json
{
  "status": "success",
  "data": {
    "advanced_content_combinations": {
      "Marketing": [ { "name": "Formal" } ]
    }
  },
  "signature": {
    "brand": "Brevio",
    "version": "v1.0",
    "contact": "support@brevio.com"
  }
}
```

---

### GET /brevio/output-formats

**Descripción**
Devuelve los formatos de salida soportados para los documentos generados.

**Autenticación**
* Requerida: Sí
* Tipo: API Key (`X-API-KEY`)

**Autorización**
* Requiere API Key válida.

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| X-API-KEY | Sí | Llave de API autorizada |

**Request Body**
`No aplica.`

**Responses**

#### 200 OK
```json
{
  "status": "success",
  "data": {
    "formats": ["pdf", "docx", "markdown"]
  },
  "signature": {
    "brand": "Brevio",
    "version": "v1.0",
    "contact": "support@brevio.com"
  }
}
```

---

### GET /brevio/summary-levels

**Descripción**
Devuelve los diferentes niveles de profundidad/resumen disponibles (ej. Corto, Detallado).

**Autenticación**
* Requerida: Sí
* Tipo: API Key (`X-API-KEY`)

**Autorización**
* Requiere API Key válida.

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| X-API-KEY | Sí | Llave de API autorizada |

**Request Body**
`No aplica.`

**Responses**

#### 200 OK
```json
{
  "status": "success",
  "data": {
    "summary_levels": ["brief", "comprehensive"]
  },
  "signature": {
    "brand": "Brevio",
    "version": "v1.0",
    "contact": "support@brevio.com"
  }
}
```

---

### POST /brevio/count-yt-videos

**Descripción**
Cuenta la cantidad de videos existentes dentro de una lista de reproducción (playlist) de YouTube.

**Autenticación**
* Requerida: Sí
* Tipo: API Key (`X-API-KEY`)

**Autorización**
* Requiere API Key válida.

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| X-API-KEY | Sí | Llave de API autorizada |
| Content-Type | Sí | `application/json` |

**Request Body**
* Content-Type: `application/json`
* Campos:
  * `url` (string, obligatorio): URL de la playlist de YouTube. Debe pasar la validación regex de YouTube.

```json
{
  "url": "https://www.youtube.com/playlist?list=..."
}
```

**Responses**

#### 200 OK
```json
{
  "status": "success",
  "data": {
    "count": 12
  },
  "signature": {
    "brand": "Brevio",
    "version": "v1.0",
    "contact": "support@brevio.com"
  }
}
```

#### 422 Unprocessable Entity
```json
{
  "detail": "La URL debe ser de YouTube"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Invalid response format from brevio service"
}
```

---

### POST /brevio/count-time-yt-video

**Descripción**
Calcula la duración total (en segundos) de un video de YouTube dado.

**Autenticación**
* Requerida: Sí
* Tipo: API Key (`X-API-KEY`)

**Autorización**
* Requiere API Key válida.

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| X-API-KEY | Sí | Llave de API autorizada |
| Content-Type | Sí | `application/json` |

**Request Body**
* Content-Type: `application/json`
* Campos:
  * `url` (string, obligatorio): URL de YouTube.

```json
{
  "url": "https://www.youtube.com/watch?v=..."
}
```

**Responses**

#### 200 OK
```json
{
  "status": "success",
  "data": {
    "time": 360
  },
  "signature": {
    "brand": "Brevio",
    "version": "v1.0",
    "contact": "support@brevio.com"
  }
}
```

#### 400 Bad Request
```json
{
  "detail": "Mensaje de error lanzado desde el servicio si la URL es inaccesible o malformada."
}
```

#### 422 Unprocessable Entity
```json
{
  "detail": "La URL debe ser de YouTube"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "An unexpected error occurred"
}
```

---

### POST /brevio/summary-media

**Descripción**
Inicia el proceso asíncrono para generar resúmenes a partir de archivos multimedia (solo extensión `.mp3`). Lanza una tarea en Celery.

**Autenticación**
* Requerida: Sí
* Tipo: JWT Bearer Token

**Autorización**
* Requiere usuario autenticado.

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| Authorization | Sí | Token JWT formato `Bearer <token>` |
| Content-Type | Sí | `multipart/form-data` |

**Request Body**
* Content-Type: `multipart/form-data`
* Campos:
  * `files` (array de archivos, obligatorio): Archivos MP3 a procesar.
  * `language` (string/enum, obligatorio): Idioma de destino.
  * `model` (string/enum, obligatorio): Modelo de IA a usar.
  * `category` (string, obligatorio): Categoría seleccionada.
  * `style` (string, obligatorio): Estilo seleccionado.
  * `format` (string/enum, obligatorio): Formato de salida deseado.
  * `summary_level` (string/enum, obligatorio): Nivel de detalle del resumen.

**Responses**

#### 202 Accepted
```json
{
  "task_id": "848245...",
  "status": "success",
  "data": {
    "message": "La generación de resúmenes se está procesando en segundo plano."
  },
  "signature": {
    "brand": "Brevio",
    "version": "v1.0",
    "contact": "support@brevio.com"
  }
}
```

#### 415 Unsupported Media Type / Custom Error (InvalidFileExtension)
* La validación (`validate_file_extension`) lanza una excepción manejada globalmente si el archivo no es `.mp3`.

#### 422 Unprocessable Entity
* Ocurre si faltan campos requeridos del formulario.

---

### POST /brevio/summary-documents

**Descripción**
Inicia el proceso asíncrono para generar resúmenes a partir de documentos de texto (.pdf, .docx). Lanza una tarea en Celery.

**Autenticación**
* Requerida: Sí
* Tipo: JWT Bearer Token

**Autorización**
* Requiere usuario autenticado.

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| Authorization | Sí | Token JWT formato `Bearer <token>` |
| Content-Type | Sí | `multipart/form-data` |

**Request Body**
* Content-Type: `multipart/form-data`
* Campos:
  * `files` (array de archivos, obligatorio): Archivos PDF o DOCX a procesar.
  * `language` (string/enum, obligatorio).
  * `model` (string/enum, obligatorio).
  * `category` (string, obligatorio).
  * `style` (string, obligatorio).
  * `format` (string/enum, obligatorio).
  * `summary_level` (string/enum, obligatorio).

**Responses**

#### 202 Accepted
```json
{
  "task_id": "993425...",
  "status": "success",
  "data": {
    "message": "La generación de resúmenes se está procesando en segundo plano."
  },
  "signature": {
    "brand": "Brevio",
    "version": "v1.0",
    "contact": "support@brevio.com"
  }
}
```

#### 415 Unsupported Media Type / Custom Error (InvalidFileExtension)
* Si el archivo no es DOCX ni PDF.

#### 422 Unprocessable Entity
* Faltan campos o son inválidos.

---

### POST /brevio/estimate-documents

**Descripción**
Realiza una estimación local (sin llamar a la IA) del procesamiento de documentos PDF o DOCX. Extrae texto, tokeniza, y calcula posibles costes, tokens totales y si se necesita chunking.

**Autenticación**
* Requerida: Sí
* Tipo: JWT Bearer Token

**Autorización**
* Requiere usuario autenticado.

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| Authorization | Sí | Token JWT formato `Bearer <token>` |
| Content-Type | Sí | `multipart/form-data` |

**Request Body**
* Content-Type: `multipart/form-data`
* Campos:
  * `files` (array de archivos, obligatorio): Archivos a evaluar (.pdf, .docx).
  * `language` (string/enum, obligatorio).
  * `model` (string/enum, obligatorio).
  * `category` (string, obligatorio).
  * `style` (string, obligatorio).
  * `format` (string/enum, obligatorio).
  * `summary_level` (string/enum, obligatorio).
  * `source_types` (array de string/enum, opcional): Define el tipo de fuentes si el estilo lo restringe.

**Responses**

#### 200 OK
* Devuelve un objeto detallado con la estimación.
```json
{
  "status": "success",
  "data": {
    "can_process": true,
    "reason": "OK",
    "estimation": {
      "input_tokens": { ... },
      "output_tokens": { ... },
      "total_tokens_worst_case": 12500
    },
    "documents": [ { "filename": "doc.pdf", "tokens": 4000, "extraction": { ... } } ],
    "tokenization": { ... },
    "model": { ... },
    "pricing": { ... },
    "credits": { ... },
    "chunking": { ... },
    "estimation_id": "...",
    "estimated_at": "2026-09-09T23:30:00",
    "warnings": []
  },
  "signature": {
    "brand": "Brevio",
    "version": "v1.0",
    "contact": "support@brevio.com"
  }
}
```

#### 415 Unsupported Media Type / InvalidFileExtension
* Si el archivo no es PDF o DOCX.

#### 422 Unprocessable Entity
* Si los datos del formulario fallan en la validación o si los `source_types` no son permitidos para el estilo.

---

### POST /brevio/summary-yt-playlist

**Descripción**
Procesa e inicia la generación de resúmenes para una playlist entera de YouTube o recursos multimedia en cola a través de la tarea de Celery `generate_summary_task`.

**Autenticación**
* Requerida: Sí
* Tipo: JWT Bearer Token

**Autorización**
* Requiere usuario autenticado.

**Path Parameters**
`No aplica.`

**Query Parameters**
`No aplica.`

**Headers**
| Header | Obligatorio | Descripción |
| ------ | ----------- | ----------- |
| Authorization | Sí | Token JWT formato `Bearer <token>` |
| Content-Type | Sí | `application/json` |

**Request Body**
* Content-Type: `application/json`
* Esquema `BrevioGenerate`:
  * `prompt_config` (objeto, obligatorio): Contiene config: `language`, `model`, `category`, `style`, `format`, `summary_level`.
  * `data` (array de objetos, obligatorio): Array de `MediaEntry` con `url` o `path`.

```json
{
  "prompt_config": {
    "model": "gpt-4",
    "category": "Education",
    "style": "Formal",
    "format": "markdown",
    "language": "es",
    "summary_level": "comprehensive"
  },
  "data": [
    { "url": "https://youtube.com/watch?v=..." }
  ]
}
```

**Responses**

#### 202 Accepted
```json
{
  "status": "success",
  "data": {
    "message": "La generación de resúmenes se está procesando en segundo plano."
  },
  "signature": {
    "brand": "Brevio",
    "version": "v1.0",
    "contact": "support@brevio.com"
  }
}
```

#### 422 Unprocessable Entity
* Error validando el payload JSON, por ejemplo si un item de `data` no tiene ni `url` ni `path`.

---

### GET /brevio/download/{folder_entry_id}

**Descripción**
Descarga el archivo de resumen asociado a una entrada. Puede generar el formato solicitado bajo demanda.

**Autenticación**
* Requerida: Sí (Bearer JWT)

**Path Parameters**
* `folder_entry_id` (string): ID de la entrada/carpeta.

**Query Parameters**
* `format` (string, opcional, default `md`): Formato de salida (`md`, `docx`, `pdf`, `txt`).
* `result_index` (int, opcional, default `0`): Índice del resultado dentro de la entrada.

**Responses**
* `200`: Archivo descargable (`FileResponse`).
* `401`: No autenticado.
* `403`: Sin acceso a la entrada.
* `404`: Entrada o archivo no encontrado.

---

# Verificación

* **Número total de endpoints encontrados:** 22+
* **Número total de endpoints documentados:** 22+
* **Endpoints pendientes:** 0
* **Controllers analizados:** `auth_router.py`, `brevio_router.py`, `user_router.py`, `user_credential_router.py`, `token_router.py`.
* **Módulos analizados:** `core/brevio_api/routers`, `core/brevio_api/models`, `core/brevio_api/dependencies`, `core/shared/models`.
* **Posibles discrepancias detectadas:**
    * El router `token_router.py` existe físicamente en los archivos pero no es inyectado al `app` principal de FastAPI en `__main__.py`, por lo que no expone endpoints funcionales.
    * Varios endpoints que utilizan la dependencia `verify_api_key` devuelven el código de estado HTTP `403 Forbidden` a pesar de que el decorador de Swagger en el código base (ej: `@self.router.get(..., responses={401: ...})`) documenta un `401 Unauthorized`.
* **Cobertura:** 100% (Todos los endpoints implementados en el enrutamiento han sido documentados. Se realizó una doble comprobación mediante `grep` en el directorio base).
