**1.1 - ¿Qué es JavaScript?**  
JavaScript es un lenguaje de programación diseñado para crear páginas web interactivas (dinámicas), en contraste con las páginas estáticas, que muestran contenido fijo sin interacción. Este lenguaje se ejecuta en el lado del cliente (navegador), es interpretado (no compilado) y no debe confundirse con Java, aunque comparten nombre. Su uso principal se centra en la interactividad en páginas web, mientras que Java se emplea en aplicaciones empresariales y sistemas.  

**1.3 - Integración de JavaScript**  
JavaScript se integra en HTML mediante dos métodos principales:  
- **Uso directo de etiquetas `<SCRIPT>`**: Se inserta el código dentro de `<SCRIPT LANGUAGE="JavaScript">...</SCRIPT>`.  
- **Inclusión de archivos externos**: Se carga un archivo `.js` mediante `src="archivo.js"`.  
Ejemplo de uso:  
```html
<SCRIPT LANGUAGE="JavaScript">
document.write("Esto es JavaScript.");
</SCRIPT>
```  
Funciones clave como `alert()` (muestra mensajes) y `prompt()` (permite entrada de datos) son fundamentales para la interacción con el usuario.  

**1.4 - Comentarios en JavaScript**  
Los comentarios se escriben con `//` para líneas individuales o `/* ... */` para bloques. Para ocultar código a navegadores antiguos, se usan comentarios HTML:  
```html
<!-- Ocultar guión para navegadores
function vertexto() { document.write("Esto es JavaScript."); }
// Fin de ocultación del guión -->
```  

**1.5 - Elementos de un programa JavaScript**  
- **Declaraciones**: Se usan `var` para definir variables, como `var ImportePtas;`.  
- **Entrada/Salida**:  
  - `prompt("mensaje", valorpordefecto)`: Muestra una ventana con un campo de entrada. Retorna el valor ingresado (o `null` si se cancela).  
  - `alert("mensaje")`: Muestra un mensaje en una ventana emergente.  
- **Instrucciones de control**: Uso de `if-else` para decisiones. Ejemplo:  
```javascript
if (ImportePtas > 0) {
    ImporteEuros = ImportePtas / 166.33;
    alert(ImporteEuros);
} else {
    alert("Importe erróneo");
}
```  

**1.6 - Ejemplo práctico: Conversor de pesetas a euros**  
El programa solicita un valor en pesetas, lo convierte a euros (dividiendo entre 166.33) y muestra el resultado con `alert()` o un mensaje de error si el valor es inválido. Código completo:  
```html
<HTML>
<HEAD><TITLE>Conversor pesetas a euros</TITLE></HEAD>
<BODY>
<SCRIPT LANGUAGE="JavaScript">
var ImportePtas;
var ImporteEuros;
ImportePtas = prompt("Introduce el importe en pesetas:", 1);
if (ImportePtas > 0) {
    ImporteEuros = ImportePtas / 166.33;
    alert(ImporteEuros);
} else {
    alert("Importe erróneo");
}
</SCRIPT>
</BODY>
</HTML>
```  

**1.7 - Consideraciones sobre seguridad y compatibilidad**  
- **Navegadores antiguos**: Se requiere ocultar comentarios JavaScript con sintaxis HTML para evitar errores.  
- **Compatibilidad**: Algunos navegadores pueden no soportar funciones como `prompt()` o `alert()`, lo que requiere pruebas adicionales.  
- **Recomendación**: Es conveniente especificar siempre un valor por defecto en `prompt()`, incluso si es `0` o una cadena vacía (`""`).  

**1.8 - Modelo tradicional de entrada/salida**  
Los datos de entrada se procesan mediante algoritmos (en este caso, JavaScript) para generar datos de salida. Ejemplo: El programa convierte pesetas a euros (procesamiento) y muestra el resultado (salida).  

**1.9 - Comparación entre JavaScript y Java**  
| Característica         | JavaScript                          | Java                                  |  
|------------------------|-------------------------------------|---------------------------------------|  
| **Ejecución**          | En el cliente (navegador)           | En el servidor o aplicaciones         |  
| **Compilación**        | Interpretado                        | Compilado (JVM)                       |  
| **Uso principal**      | Interactividad en páginas web     | Aplicaciones empresariales            |  
| **Sintaxis**           | Basado en objetos                   | Orientado a objetos                   |  
| **Compatibilidad**     | Depende del navegador              | Plataforma Java (JVM)                 |  

**1.10 - Inspiración de ActionScript**  
ActionScript fue inspirado por JavaScript, según se menciona en el texto.  

**1.11 - Cierre de script**  
La etiqueta `</SCRIPT>` indica el final de un bloque de script en HTML.  

**1.12 - Entrada y salida en JavaScript**  
- **Salida**:  
  - `document.write("mensaje")`: Escribe texto directamente en el documento actual.  
  - `alert("mensaje")`: Muestra un mensaje en una ventana emergente con un botón "Aceptar".  
- **Entrada**:  
  - `prompt("mensaje", valorpordefecto)`: Muestra una ventana con un mensaje, un campo de entrada y botones "Aceptar" y "Cancelar". Retorna el valor ingresado (o `null` si se cancela).  

**1.13 - Comportamiento de `prompt`**  
- Al pulsar "Aceptar": Se asigna el valor ingresado (o el valor por defecto si no se modifica).  
- Al pulsar "Cancelar": Se asigna `null` como valor de retorno.
