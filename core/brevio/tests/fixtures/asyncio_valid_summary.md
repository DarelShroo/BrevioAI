**Guía: Uso de asyncio en Python**  
El libro *Using Asyncio in Python* (O'Reilly, ISBN 978-1-492-07533-2), escrito por Caleb Hattingh, un desarrollador con más de 20 años de experiencia, se enfoca en enseñar a los programadores Python a aplicar la programación asincrónica para manejar concurrencia en aplicaciones de red. El libro incluye un ejemplo didáctico sobre un restaurante automatizado con robots (ThreadBots) para ilustrar problemas de concurrencia y la necesidad de asyncio. Se publica en inglés, con edición en español disponible, y tiene un precio de USD 39.99.  

**Asyncio vs. Threading**  
Asyncio se destaca por su capacidad para manejar miles de conexiones simultáneas y evitar condiciones de carrera mediante programación explícita de tareas, a diferencia de threading, que sufre limitaciones por el GIL (Global Interpreter Lock) en Python, limitando el paralelismo a un solo núcleo. Threading es más adecuado para cargas de trabajo CPU-bound con memoria compartida, pero sufre problemas de sincronización y no determinismo. Asyncio, en cambio, es ideal para cargas I/O-bound, como WebSockets o MQTT, pero no elimina todos los desafíos, como la gestión de tareas prolongadas.  

**Ejemplos y Analogías**  
- **ThreadBots:** Robots en un restaurante que generan colisiones al recoger platos o bebidas, causando daños. La solución propuesta, LoopBot, reduce colisiones pero requiere que las tareas sean breves.  
- **Cutlery:** Un ejemplo de condición de carrera en hilos donde el método `change` de la clase `Cutlery` usa `+=`, permitiendo que hilos interrumpidos alteren el estado compartido. La solución es usar un `threading.Lock`.  
- **Asyncio:** En aplicaciones I/O-bound, asyncio evita condiciones de carrera mediante `async/await` y permite manejar miles de conexiones simultáneas.  

**Limitaciones y Consideraciones Técnicas**  
- **Memoria en sistemas de 32 bits:** La asignación previa de memoria virtual para pilas de hilos puede consumir hasta 80 GB en sistemas de 32 bits, aunque la memoria residente sea solo ~130 MB. En sistemas de 64 bits, el espacio de memoria virtual es mayor, reduciendo la presión.  
- **Inflexibilidad de hilos:** El sistema operativo comparte tiempo de CPU con todos los hilos, incluso si no están listos para trabajar. En sistemas asincrónicos, como `select()` en Unix, se evita el costo de conmutación de contexto.  
- **Asyncio y ejecutores:** Para ejecutar funciones bloqueantes en aplicaciones asincrónicas, se requiere usar `run_in_executor()`, evitando bloquear el bucle de eventos. Ejemplo: `loop.run_in_executor(None, blocking)`.  

**APIs y Funcionalidades Clave de Asyncio**  
- **Coroutines:** Se definen con `async def` y se invocan con `await`. Ejemplo: `async def main(): await asyncio.sleep(1)`.  
- **Event Loop:** Se inicia con `asyncio.run(main())`, que encapsula el manejo de tareas pendientes, cancelaciones y cierre del bucle.  
- **Tasks y Futures:**  
  - **Task:** Subclase de `Future`, creada con `asyncio.create_task(coro)`.  
  - **Future:** Representa un estado futuro de una actividad. Ejemplo: `f = asyncio.Future(); f.set_result('I have finished.')`.  
- **Manejo de excepciones:** Se puede inyectar excepciones en coroutines con `coro.throw()`, útil para cancelar tareas (ej.: `asyncio.CancelledError`).  
- **Async context managers:** Se basan en `__aenter__()` y `__aexit__()` definidos como `async def`. Ejemplo:  
  ```python  
  class Connection:  
      async def __aenter__(self):  
          self.conn = await get_conn(...)  
          return self.conn  
      async def __aexit__(self, exc_type, exc, tb):  
          await self.conn.close()  
  async with Connection(...) as conn:  
      # Usar conn  
  ```  
- **Async iterators y generadores:** Implementan `__aiter__()` y `__anext__()` para permitir iteración asincrónica. Ejemplo:  
  ```python  
  class OneAtATime:  
      async def __aiter__(self):  
          return self  
      async def __anext__(self):  
          if self.index >= len(self.data):  
              raise StopAsyncIteration  
          await asyncio.sleep(0.1)  
          return self.data[self.index]  
  ```  
- **Async comprehensions:** Permiten listas, diccionarios y conjuntos asincrónicos con `async for`. Ejemplo: `[x async for x in doubler(3)]`.  

**Prácticas Recomendadas**  
- **Evitar condiciones de carrera:** Usar `threading.Lock` en hilos o `async/await` en asyncio.  
- **Manejo de tareas pendientes:** Usar `asyncio.gather()` con `return_exceptions=True` para evitar que excepciones interrumpan el cierre.  
- **Cierre del bucle de eventos:** `asyncio.run(main())` maneja automáticamente la recopilación, cancelación y finalización de tareas.  
- **Compatibilidad con bibliotecas de terceros:** La mayoría no son compatibles con `async/await`, por lo que se recomienda usar `run_in_executor()` para funciones bloqueantes.  

**Manejo de señales, cierre grácil y soluciones en asyncio**  
- **`asyncio.gather(*pending, return_exceptions=True)`** permite evitar que errores como `ZeroDivisionError` detengan la ejecución de otras tareas.  
- **Cierre grácil:** En aplicaciones de red, se recomienda incluir pruebas específicas para escenarios de cierre en suites automatizadas. El paquete `aiorun` (publicado en PyPI) ofrece herramientas para experimentar con escenarios de cierre.  
- **Manejo de señales (SIGINT y SIGTERM):**  
  - **SIGINT (Ctrl-C):** En `asyncio.run()`, el `KeyboardInterrupt` desbloquea `run_until_complete()` y permite el cierre.  
  - **SIGTERM:** Más común en servicios de red. El envío de `SIGTERM` permite un cierre controlado, mientras que `SIGKILL` fuerza el cierre sin recuperación.  
- **Ejemplo 3-33 (shell_signal01.py):** Captura `KeyboardInterrupt` para cancelar tareas y usar `asyncio.all_tasks()` con `gather(*tasks, return_exceptions=True)`.  
- **Ejemplo 3-34 (shell_signal02.py):** Maneja ambas señales, deteniendo el bucle solo una vez y eliminando manejadores de señales para evitar reacciones múltiples.  
- **Ejemplo 3-35 (shell_signal02b.py):** Usa `loop.add_signal_handler(sig, handler, sig)` dentro de `asyncio.run()` para manejar señales.  
- **Problemas con tareas del executor:**  
  - **Ejemplo 3-36 (quickstart.py):** Si una tarea del executor (`run_in_executor()`) tarda más que las tareas pendientes, se genera un `RuntimeError` ("Event loop is closed").  
  - **`run_in_executor()`** devuelve un `Future`, no un `Task`, por lo que no se incluye en la limpieza automática de `asyncio.run()`.  

**Soluciones para `asyncio.run()` en Python 3.8:**  
- **Opción A:** Usar `try/finally` para esperar explícitamente el `Future` dentro de una coroutine:  
  ```python  
  future = loop.run_in_executor(None, blocking)  
  try:  
      ...  
  finally:  
      await future  
  ```  
- **Opción B:** Envolver el `Future` en un `Task` con `create_task()`:  
  ```python  
  asyncio.create_task(make_coro(future))  
  async def make_coro(future):  
      try:  
          return await future  
      except asyncio.CancelledError:  
          return await future  
  ```  
- **Opción C:** Usar un bucle de eventos personalizado y un executor personalizado:  
  ```python  
  loop = asyncio.get_event_loop()  
  executor = Executor()  
  loop.set_default_executor(executor)  
  ...  
  executor.shutdown(wait=True)  
  loop.close()  
  ```  

**Protocolo de mensajes:**  
- Cada mensaje comienza con un prefijo de 4 bytes (tamaño en big-endian).  
- **Ejemplo de lectura:**  
  ```python  
  async def read_msg(stream: StreamReader) -> bytes:  
      size_bytes = await stream.readexactly(4)  
      size = int.from_bytes(size_bytes, byteorder='big')  
      data = await stream.readexactly(size)  
      return data  
  ```  

**Servidor (mq_server.py):**  
- Usa `asyncio` para manejar conexiones concurrentes.  
- Almacena suscriptores en `DefaultDict[bytes, Deque]` (clave: nombre del canal, valor: cola de `StreamWriter`).  
- Para canales `/queue`, se distribuyen mensajes a suscriptores mediante rotación de `deque`.  

**Clientes:**  
- **Escuchador (`mq_client_listen.py`):** Se suscribe a un canal especificado por `--listen`.  
- **Emisor (`mq_client_sender.py`):** Envía mensajes a un canal con `--channel`, usando `itertools.count()` para generar mensajes secuenciales.  
- **Problemas en el código:**  
  - `gather(*[send_msg(c, data)])` bloquea la distribución si hay un suscriptor lento.  
  - La remoción de suscriptores de `SUBSCRIBERS` es O(n), ineficiente para `n` grande.  

**Mejoras en el diseño del broker:**  
- **Desacoplamiento:** Introducción de `SEND_QUEUES` (por cliente) y `CHAN_QUEUES` (por canal).  
- **`send_client()`** maneja el envío desde una cola independiente, permitiendo procesamiento paralelo.  
- **`chan_sender()`** distribuye mensajes a suscriptores, con rotación de colas para canales `/queue`.  
- **Ejemplo de código en `mq_server_plus.py`:**  
  ```python  
  from asyncio import Queue  
  chan_sender() espera datos en `CHAN_QUEUES[name]` y los distribuye.  
  Al cerrar la conexión, se coloca `None` en `SEND_QUEUES[writer]` para finalizar tareas.  
  ```  

**Comparación con Twisted:**  
- Twisted usa `Deferred` y `@inlineCallbacks` para manejar callbacks lineales.  
- **Ejemplo:**  
  ```python  
  @defer.inlineCallbacks  
  def f():  
      yield  
      defer.returnValue(123)  
  ```  
- Desde Python 3.5, `asyncioreactor` permite integrar Twisted con `asyncio`:  
  ```python  
  from twisted.internet import asyncioreactor  
  asyncioreactor.install()  
  ```  
- `defer.ensureDeferred(main())` es equivalente a `asyncio.create_task()`.  

**Janus Queue:**  
- Soluciona comunicación entre hilos y coroutines.  
- Proporciona APIs `async_q` (asincrónica) y `sync_q` (bloqueante).  
- **Ejemplo:**  
  ```python  
  queue = janus.Queue(loop=loop)  
  future = loop.run_in_executor(None, data_source, queue)  
  ```  

**aiohttp:**  
- Framework para HTTP en `asyncio`.  
- **Ejemplo "Hello World":**  
  ```python  
  async def hello(request):  
      return web.Response(text="Hello, world")  
  ```  
- Caso de uso: scraper de noticias con `Splash` para renderizado de JavaScript.  
- **Ejemplo de integración con `BeautifulSoup` y `asyncio.gather()`.**  

**Detalles técnicos:**  
- `defer.returnValue()` es necesario en `@inlineCallbacks`.  
- `async def` en Twisted permite usar `await` directamente, reemplazando `yield from`.  
- `task.deferLater(reactor, 1, ...)` es equivalente a `asyncio.sleep(1)`.  

**Consideraciones de rendimiento:**  
- La cola `CHAN_QUEUES[name]` puede llenarse si no hay suscriptores activos.  
- Si una cola de envío (`SEND_QUEUES[writer]`) se llena, los mensajes se pierden.  
- El uso de `back-pressure` en `CHAN_QUEUES[name].put(data)` comunica al cliente la necesidad de reducir la tasa de envío.  

**Ejemplos de uso:**  
- El servidor se ejecuta con `mq_server.py`.  
- Los clientes se ejecutan con `mq_client_sender.py` (emisor) o `mq_client_listen.py` (escuchador), especificando host, puerto y canal.  
- Al detener el servidor con `Ctrl-C`, se cierran todas las conexiones.  

**Casos de uso técnicos:**  
- **Protocolo de mensajes personalizado:** Cada mensaje tiene un encabezado de 4 bytes.  
- **Servidor de cola de mensajes:** Gestiona canales `/topic` y `/queue` con `DefaultDict[bytes, Deque]`.  
- **Ejemplo de salida de clientes:**  
  - Ejemplo 4-6: Cliente emisor envía mensajes a `/queue/blah` con identificadores como `('127.0.0.1', 55390)`.  
  - Ejemplo 4-7 y 4-8: Dos clientes receptores reciben mensajes alternados (`Msg 1, 3, 5` y `Msg 0, 2, 4`).  
  - El servidor cierra conexiones tras finalizar la transmisión.  

**Web scraping con aiohttp y BeautifulSoup**  
Las funciones `cnn_articles()` y `aljazeera_articles()` emplean `BeautifulSoup` para extraer enlaces y títulos de noticias, aplicando filtros específicos (`tag.text`, `tag['href']` que comienzan con `/news` y terminan con `.html`). La función `news()` maneja la ruta `/news` de un servidor web, devolviendo una página HTML con resultados de noticias. Se usa `asyncio.gather()` para procesar múltiples tareas asincrónicas (scraping de CNN y Al Jazeera), cada una con su función de postprocesamiento personalizada. El servidor web utiliza `aiohttp` para manejar solicitudes, con un ejemplo de conexión al API de Splash (puerto 8050) mediante `aiohttp.ClientSession()`. Las funciones de postprocesamiento devuelven listas de tuplas en formato `<URL>, <título>, <origen>`.  

**ZeroMQ con asyncio**  
Ejemplo de código tradicional con `zmq.Poller()` para manejar múltiples sockets (`PULL` y `SUB`) en hilos, requiriendo un bucle de selección explícito. Implementación asincrónica con `asyncio` usando `zmq.asyncio.Context()` y coroutines (`do_receiver()`, `do_subscriber()`), eliminando la necesidad de `Poller` y permitiendo manejar sockets en coroutines separadas. Ventaja de asyncio: estructura más limpia, evitando problemas de seguridad en hilos y permitiendo encapsular lógica por socket. En ZeroMQ, los sockets `PULL` (receptores) y `PUSH`/`PUB` (emisores) son gestionados asincrónicamente con `await receiver.recv_json()`.  

**Arquitectura de tres capas para monitoreo distribuido**  
- **Capa de aplicación:** Microservicios con sockets ØMQ PUB que envían métricas (CPU, memoria) a un servidor central.  
- **Capa de recolección:** Servidor con socket ØMQ SUB que recibe datos, usa `aiohttp` para servir una página web y `aiohttp_sse` para transmitir datos en tiempo real a clientes.  
- **Capa de visualización:** Página web con `Smoothie Charts` que muestra gráficos en tiempo real, usando eventos `Server-Sent Events (SSE)` para recibir datos.  

**Implementación técnica clave**  
- **Uso de `asyncio` y `zmq.asyncio`:** Corrutinas para manejar sockets asincrónicos, con `await` para enviar/recibir datos.  
- **Serialización JSON:** Datos transmitidos en formato JSON (ejemplo: `send_json()` en la capa de aplicación, `recv_json()` en la capa de recolección).  
- **Manejo de conexiones:** `WeakSet()` para rastrear clientes conectados, con `Queue()` para distribuir datos a cada cliente.  
- **Ejemplo de código destacado:** Función `stats_reporter()`: Corrutina que usa `psutil` para recopilar métricas y las envía al servidor cada segundo. Servidor con `aiohttp`: Rutas `/` (página HTML) y `/feed` (transmisión SSE), con `start_collector()` y `stop_collector()` para iniciar/detener la recolección de datos.  

**Visualización en el navegador**  
El "visualization layer" se refiere al navegador, que conecta mediante `EventSource("/feed")` a un servidor (`metric_server.py`) para recibir eventos en tiempo real. Manejo de eventos en JavaScript:  
```javascript
var evtSource = new EventSource("/feed");
evtSource.onmessage = function(e) {
    var obj = JSON.parse(e.data);
    // Lógica para actualizar gráficos de CPU y memoria
};
```  
Se parsea datos JSON y se actualizan series temporales (`TimeSeries()`) para gráficos.  

**Servidor de métricas**  
El script `metric_server.py` inicia un servidor en `http://127.0.0.1:8088` que recibe métricas de microservicios. Microservicios con fugas de memoria:  
```bash
$ backend-app.py --color red &
$ backend-app.py --color blue --leak 10000 &
$ backend-app.py --color green --leak 100000 &
```  
Se especifican colores y parámetros de fuga de memoria (`--leak`). Reconexión automática: ØMQ y `EventSource()` manejan reconexiones automáticas si se pierde la conexión.  

**asyncpg y PostgreSQL**  
- **Conexión asincrónica:**  
```python
async with Database('test', owner=True) as conn:
    await demo(conn)
```  
- **Operaciones CRUD:** Creación de tabla `users`, inserción, actualización y eliminación de registros.  
- **Tipos de datos mapeados:** `asyncpg` convierte tipos SQL a Python (ej. `datetime.date`).  
- **Ejemplo de utilidad (`util.py`):** Clase `Database` como contexto manager para crear/eliminar bases de datos, con métodos `connect()` y `disconnect()`.  

**Estudio de caso: Invalidación de caché**  
Uso de notificaciones de eventos en PostgreSQL para sincronizar caché, citando el famoso dicho de Phil Karlton sobre la dificultad de la invalidación de caché.  

**Problema de invalidación de caché**  
En aplicaciones web, cuando una instancia actualiza datos en la base de datos, otras instancias pueden devolver datos obsoletos del caché, generando inconsistencias. Solución con PostgreSQL: PostgreSQL permite usar `LISTEN` y `NOTIFY` para enviar notificaciones de eventos (como actualizaciones) a todas las instancias conectadas, permitiendo actualizar el caché en tiempo real.  

**Implementación con asyncpg y Sanic**  
- **asyncpg** soporta directamente `LISTEN/NOTIFY` para suscribirse a canales de eventos.  
- **Sanic** actúa como servidor web asincrónico que maneja solicitudes CRUD (create, read, update, delete) para una tabla `patron` (campos: `name`, `fav_dish`).  
- **Ejemplo práctico:** Al actualizar un registro en la base de datos (ej.: cambiar `fav_dish` de "Gravy on Toast" a "SPAM on toast"), PostgreSQL notifica a todas las instancias conectadas. Las instancias actualizan su caché in-memory, evitando devolver datos obsoletos.  

**Logs de rendimiento**  
- La primera solicitud a un recurso genera un *cache miss* (tiempo: ~4 ms), mientras que la segunda (misma URL) obtiene datos del caché (tiempo: ~0.04 ms).  
- Al actualizar un registro en una instancia (puerto 8000), la otra instancia (puerto 8001) recibe la notificación y actualiza su caché sin necesidad de una solicitud explícita.  

**Arquitectura del servidor API**  
El servidor API (basado en Sanic) se ejecuta en múltiples instancias y utiliza caché en memoria para datos obtenidos de la base de datos. Suscripción a eventos de actualización en tablas específicas de la base de datos mediante `asyncpg`, permitiendo notificaciones en tiempo real para actualizar el caché.  

**Ejemplo de código (Sanic)**  
- Uso de decoradores personalizados (`@aelapsed`, `@aprofiler`) para medir tiempos de ejecución y perfilado de métodos.  
- Rutas definidas con `add_route()`, como `/patron` para `POST` y `/patron/<id:int>` para `GET`, `PUT`, `DELETE`.  
- Conexión a la base de datos mediante `Database('restaurant')` y manejo de pools de conexiones (`app.pool`).  

**Módulo `model.py`**  
- Consultas SQL para operaciones CRUD (INSERT, SELECT, UPDATE, DELETE) usando sintaxis nativa de PostgreSQL (`$1`, `$2`).  
- Uso de `LRU` (de `boltons`) para caché local, con actualización automática mediante eventos de base de datos (`db_event`).  
- Creación de triggers en la base de datos para notificaciones en canal `chan_patron` (con `create_notify_trigger`, `add_table_triggers`).  

**Manejo de eventos**  
- Función `db_event()` deserializa payloads JSON de notificaciones y actualiza el caché según el tipo de evento (INSERT, UPDATE, DELETE).  
- La caché solo se actualiza en `GET`, no en operaciones de escritura (INSERT/UPDATE/DELETE), dependiendo de notificaciones asincrónicas.  

**Herramientas y dependencias**  
- Librerías mencionadas: `asyncpg`, `Sanic`, `boltons` (para `LRU`), `triggers` (para creación de triggers en base de datos).  
- Uso de `fetchval()` en lugar de `execute()` para obtener el `id` de registros insertados.  

**Consideraciones técnicas**  
- La base de datos PostgreSQL requiere triggers para notificaciones asincrónicas.  
- El código incluye funciones para crear tablas si no existen (`create_table_if_missing`).  
- Se menciona compatibilidad con ORMs como SQLAlchemy (vía `asyncpgsa`, `GINO`) y `aiopeewee` para `Peewee`.  

**Conclusión**  
Asyncio es una herramienta poderosa para aplicaciones I/O-bound, permitiendo manejar miles de conexiones simultáneas y evitando condiciones de carrera. Sin embargo, no elimina todos los desafíos, como la gestión de tareas prolongadas. La comparación con threading muestra que cada enfoque tiene sus ventajas y limitaciones, dependiendo del contexto. El libro *Using Asyncio in Python* proporciona una guía completa para dominar estos conceptos, con ejemplos prácticos y estudios de caso.

**asyncio y bibliotecas complementarias para concurrencia en Python**  

**asyncio** es una biblioteca clave para manejar operaciones asincrónicas en Python, enfocada principalmente en programación de red. Fue introducida en Python 3.4 (PEP 3156) y ampliada con soporte para coroutines mediante `async/await` (PEP 492 en Python 3.5). Recomienda estudiar "Socket Programming HOWTO" de Gordon McMillan para casos de uso avanzados. **aiofiles** permite operaciones de disco sin bloquear el bucle de eventos, aprovechando que Python libera el GIL durante operaciones de archivo. **asyncore**, introducido en Python 1.5.2, se considera obsoleto, con advertencias en Python 3.6 de usar **asyncio** en su lugar.  



El ejemplo de código en `CoroBot` utiliza `asyncio` para gestionar concurrencia sin bloqueos, evitando condiciones de carrera mediante `await` y `asyncio.Queue`. Pruebas con 10 instancias de `CoroBot` en un solo hilo confirman que el inventario de utensilios no cambia (`knives=100, forks=100`), demostrando la eficacia de `asyncio` en entornos concurrentes. Sin embargo, su API granular requiere que los desarrolladores aprendan qué componentes son relevantes, lo que se espera que bibliotecas como **aiohttp** o **Sanic** simplifiquen en el futuro.  

En estudios de caso destacados, **aiohttp** se integra en `index.html` y `charts.html` para web scraping, combinado con `smoothie.min.js` para gráficos de rendimiento y `EventSource` para recibir datos en tiempo real desde `/feed`. En PostgreSQL, la función `create_notify_trigger()` genera un trigger que notifica cambios en tablas mediante `pg_notify()`, usando `hstore` para calcular diferencias entre datos antiguos y nuevos. En **Sanic**, los decoradores `aelapsed()` y `aprofiler()` miden el tiempo de ejecución de funciones asincrónicas y aplican `aelapsed()` a todos los métodos asincrónicos de una clase, respectivamente, con ejemplos en `perf.py`.

**Bibliotecas y herramientas mencionadas:**  
- **aiohttp** (caso de estudio de scraper de noticias).  
- **asyncpg** (gestión de disparadores de base de datos en PostgreSQL).  
- **aioredis**, **aiorun**, **Janus queue**, **ZeroMQ**, **Twisted**, **asyncore**, **Cython**.  
- **Herramientas adicionales:** `uvloop`, `Trio`, `Twisted`.  

**Funciones y módulos clave:**  
- `asyncio.run()`, `asyncio.gather()` (con `return_exceptions=True`), `asyncio.create_task()`, `asyncio.get_event_loop()`, `asyncio.get_running_loop()`.  
- `@asynccontextmanager`, `@contextmanager`, `@defer.inlineCallbacks`, `@inlineCallbacks`.  



**Conceptos técnicos:**  
- Coroutines nativas en Python 3.5 (sintaxis `async def` y `await`).  
- Comparación entre `ensure_future()` y `create_task()` en `asyncio`.  
- Manejo de excepciones `CancelledError` y `KeyboardInterrupt` (Ctrl-C).  
- Uso de `async with` para gestores de contexto asincrónicos, `async for` para iteradores asincrónicos, y `async comprehensions` para generadores asincrónicos.  



**Casos de uso y aplicaciones:**  
- **ZeroMQ:** Estudio de monitoreo de rendimiento de aplicaciones (archivos `charts.html`).  
- **Multiple sockets:** Estudio de caso con ZeroMQ (sección 99-102).  
- **Message queue:** Mejora del caso de estudio (sección 84-88).  
- **News scraper:** Uso de `aiohttp` (sección 93-98).  
- **Database trigger handling:** Modelo de base de datos `patron` y manejo de disparadores de base de datos.  



**Contexto tecnológico y recursos:**  
- Recursos de aprendizaje: Charla de Robert Smallshire en NDC London (2017), diapositivas de Nikolay Novik en PyCon UA 2016, y experimentación en Python REPL.  
- **Funciones de eventos:** `get_event_loop` y `get_running_loop` (págs. 24, 38), con ventajas de la última sobre la primera (pág. 38).  
- **GIL (Global Interpreter Lock):** Problemas con `asyncio` (pág. 7) y efectos secundarios (pág. 10).  
- **Variables globales:** Prevención de acceso o escritura en código multihilo (pág. 11).  
- **Tareas agrupadas:** Manejo de excepciones con `run_until_complete` (pág. 62).  



**Diseño del libro y contexto del autor:**  
- **Contexto temporal:** Caleb trabajaba con MATLAB y Delphi en 2001; Python 2.0 recién lanzado; Java en 1.3, C# 1.0 no disponible, YouTube aún no existía.  
- **Aplicaciones de Python por Caleb:** Modelado químico, reservas hoteleras, CRM, sitios web, software financiero, simulación de reactores, seguimiento GPS, capacitación en programación, redes definidas por software.  
- **Publicaciones:** *Using Asyncio in Python* (tercera obra para O’Reilly), *Learning Cython* (video), *20 Python Libraries You Aren’t Using (But Should)*.  
- **Diseño del libro:** Ilustración de Karen Montgomery basada en grabado en blanco y negro; fuentes Gilroy Semibold, Guardian Sans, Adobe Minion Pro, Adobe Myriad Condensed, Ubuntu Mono.  
- **Promoción de O’Reilly:** Enlaces a cursos en línea, libros, videos y partners (oreilly.com/online-learning).  


- **Aviso legal:** ©2019 O’Reilly Media, Inc. | 175.
