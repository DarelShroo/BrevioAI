# Créditos y Libro Mayor (Ledger)

BrevioAI utiliza una economía interna basada en "Créditos" para abstraer la volatilidad de los precios en dólares de los LLMs.

El módulo `CreditService` es el "Banco" de BrevioAI.

## 1. El Saldo (CreditAccount)
Cada usuario tiene un `CreditAccount` que almacena su saldo (`balance`). Ninguna operación en el sistema puede dejar este saldo en negativo. El código utiliza un operador `$gte: amount` en MongoDB durante el `find_one_and_update` para garantizar que la retirada atómica de fondos es segura bajo alta concurrencia (condiciones de carrera).

## 2. El Libro Mayor (CreditLedgerEntry)
El sistema financiero de BrevioAI es *append-only* (solo inserción).
Si ocurre un error y hay que devolver dinero, no se borra la transacción original. Se crea una nueva transacción de "compensación".
Razones contables (`LedgerReason`):
*   `RESERVE`: Dinero bloqueado al iniciar un trabajo.
*   `RELEASE`: Devolución parcial (o total) del dinero reservado una vez se asienta el coste final del trabajo.
*   `MIGRATE`: Ajustes iniciales o migraciones de saldo antiguo.

## 3. Modos de Facturación (`BillingMode`)

Dependiendo de cómo interactúe el usuario, el servicio de créditos opera bajo uno de estos modos:

1.  **PLATFORM:** El usuario consume saldo de su plan/billetera de Brevio. La plataforma paga la factura de OpenAI.
2.  **BYOK (Bring Your Own Key):** El usuario puso su API Key. OpenAI le cobra a él en su tarjeta. Sin embargo, BrevioAI puede cobrar una tasa o registrar el coste como $0 créditos de plataforma, aunque sigan operando los límites de infraestructura.
3.  **LOCAL:** Modelos locales o sin coste por API (ej. Ollama local).
