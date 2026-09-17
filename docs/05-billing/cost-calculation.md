# Cálculo de Costes (Estimados vs Reales)

El motor de facturación debe manejar la incertidumbre: cuando el usuario sube un PDF de 500 páginas, no sabemos exactamente cuántos tokens va a consumir el resumen final (porque el LLM es no-determinista).

El proceso se divide en **Estimación (Máxima/Esperada)** y **Asentamiento Real**.

## 1. La Estimación y la Reserva (`reserve_for_job`)

Antes de enviar el trabajo a Celery, FastAPI pide una estimación al `EstimationService`.
El servicio cuenta los tokens del documento usando `tiktoken` (muy rápido y sin coste de API). Luego proyecta:
*   **Coste Esperado:** Lo que creemos que costará (ej. 30 créditos).
*   **Coste Máximo (Worst-case scenario):** Lo máximo que podría costar si el Map-Reduce necesita muchas rondas (ej. 50 créditos).

El `CreditService` aplica un multiplicador de seguridad (`CREDIT_RESERVATION_SAFETY_MARGIN`, por defecto 1.0) sobre el coste Máximo y **bloquea esa cantidad en el saldo del usuario**. Esto se conoce como la *Reserva* (`CreditReservation`).

*¿Por qué reservar el máximo?* Para garantizar que el usuario no empiece un trabajo que no pueda pagar a la mitad, o que lance 10 trabajos en paralelo teniendo saldo solo para 1.

## 2. El Asentamiento (`settle_job`)

Una vez el trabajo termina (con éxito o fallido), el Worker de Celery notifica cuántos tokens se consumieron en la realidad.
El servicio de Usage (`UsageBillingService`) agrega los `CostRecords` y se comunica con `CreditService` para el Asentamiento (`JobSettlement`).

1.  Se asume que el usuario reservó 50 créditos.
2.  El consumo real fue de 28 créditos.
3.  El `CreditService` consolida la transacción: marca los 28 como cobrados y **devuelve 22 créditos al saldo del usuario**.
4.  Si por algún error masivo el coste real superara el máximo reservado (overrun), BrevioAI tiene una política (`CREDIT_OVERRUN_POLICY`). Por defecto ("clamp"), perdona el exceso al usuario y cobra como máximo lo que se reservó inicialmente, asumiendo la pérdida comercial por un fallo de estimación del sistema.

## 3. Precios de Plataforma (Pricing Registry)

¿Cómo se convierte un Token a un Crédito?
El sistema consulta una tabla de precios dinámicos (`PricingRegistry`) que contiene el multiplicador de coste por cada 1M de tokens para Entrada y Salida, dependiendo del modelo exacto (`gpt-4o`, `claude-3-5-sonnet`, etc.). Esta conversión permite a BrevioAI ser rentable y escalar sin tener que tocar la lógica core.
