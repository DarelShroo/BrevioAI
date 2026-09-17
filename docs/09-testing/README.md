# 09 - Testing y Calidad (Testing)

## Visión General

El entorno de pruebas de BrevioAI está diseñado para ser **hermético y predecible**. Se utiliza `pytest` como framework principal de pruebas para el Backend. 

El principal desafío al probar aplicaciones de IA (Inteligencia Artificial) es que hacer llamadas a modelos LLM reales en cada ejecución de test es lento, costoso, y no determinista (el modelo puede responder distinto cada vez). Por ello, el sistema bloquea activamente estas conexiones.

### Sub-módulos

*   [Tests Herméticos (Offline)](hermetic-tests.md)
*   [Mocking y Aislamiento](mocking.md)
