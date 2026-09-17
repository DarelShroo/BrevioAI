# Límites y Anti-Abuso (Product Limit Service)

El `ProductLimitService` garantiza que los usuarios no consuman más recursos físicos o de licencias de los que sus planes (Subscriptions) permiten.

A diferencia del `CreditService` (que es contabilidad monetaria), este servicio maneja los **límites del producto**.

## Ciclo de Admisión (`admit`)

Antes de siquiera reservar créditos, el trabajo debe ser *admitido* a nivel de producto. Se envía un `AdmissionRequest` con el usuario y el peso de los documentos a procesar.

El servicio comprueba, basándose en la configuración del YAML (`commercial_plans.yaml`):
1.  **Límite de Trabajos (Documents per period):** ¿Ha resumido ya 50 documentos este mes y su límite es 50? Rechazado.
2.  **Límite de Volumen (Bytes per period / per document):** ¿El PDF pesa 500MB y su plan solo admite 10MB? Rechazado.
3.  **Páginas (Pages per document):** Si es un PDF o DOCX, se comprueba si el número de páginas excede el límite del plan.

### Medición de Documentos (`measure_documents`)
El backend extrae heurísticamente el número de páginas, palabras, o el tamaño en bytes de los binarios subidos antes de procesarlos para hacer cumplir estos límites con exactitud matemática.

## Protección contra Spam
Se acompaña del Rate Limiting basado en Redis (ej. 5 peticiones de creación por minuto por IP/Usuario) para asegurar que un script malicioso no llene la base de datos de MongoDB con trabajos fallidos intentando agotar el servicio (Denegación de Servicio - DoS).
