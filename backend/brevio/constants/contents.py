class Contents:
    PROGRAMMING_CONTENT = """
Genera un resumen detallado en formato Markdown del siguiente texto, con un enfoque técnico preciso, siguiendo estas directrices:

Mantén un balance entre concisión y profundidad, explicando los conceptos técnicos esenciales sin extenderte innecesariamente.
Excluye contenido promocional, enlaces, recomendaciones o recursos externos.
Utiliza una estructura clara con títulos jerárquicos (#, ##, ###) y listas.
Explica términos técnicos cuando sea necesario sin caer en redundancias.
Incluye ejemplos de código solo si son esenciales.
Evita explicaciones innecesarias.

Formato:

## Título Principal

Explicación técnica clara y precisa del tema.

### Características clave

**Concepto 1**: Explicación técnica breve.  
**Concepto 2**: Profundización técnica si es necesario.

### Detalles técnicos

**Aspecto relevante**: Explicación técnica sin redundancias.  
**Ejemplo de código (si es necesario)**:

```js
// Código relevante
```

Es importante asegurarse de que los términos técnicos utilizados sean correctos y estén basados en conceptos reales, evitando la creación de términos o definiciones no existentes.

Traducción:  
Traduce completamente todo el resumen al idioma [{}] (o al idioma que se especifique), asegurándote de que todas las secciones y detalles se presenten en dicho idioma.
"""

    SCIENTIFIC_CONTENT = """
Genera un resumen detallado en formato Markdown del siguiente texto, enfocado en el rigor científico, siguiendo estas directrices:

Mantén un balance entre claridad y precisión científica, explicando los conceptos fundamentales sin extenderte innecesariamente.
Excluye opiniones personales, especulaciones o recomendaciones externas.
Utiliza una estructura clara con títulos jerárquicos (#, ##, ###) y listas.
Define términos técnicos y conceptos clave cuando sea necesario.
Incluye fórmulas o ecuaciones solo si son esenciales.
Evita redundancias y repeticiones.

Formato:

## Título Principal

Explicación clara y precisa del tema científico.

### Conceptos Fundamentales

**Concepto 1**: Definición breve y exacta.  
**Concepto 2**: Explicación más detallada si es necesario.

### Resultados Principales

**Hallazgo relevante**: Descripción técnica sin redundancias.  
**Ecuación (si es necesaria)**:
```math
// Ecuación relevante
```
Es importante asegurarse de que los términos técnicos utilizados sean correctos y estén basados en conceptos reales, evitando la creación de términos o definiciones no existentes.

Traducción:  
Traduce completamente todo el resumen al idioma [{}] (o al idioma que se especifique), asegurándote de que todas las secciones y detalles se presenten en dicho idioma.
"""

    BUSINESS_CONTENT = """
Genera un resumen detallado en formato Markdown del siguiente texto, con un enfoque estratégico empresarial, siguiendo estas directrices:

Destaca los puntos clave relacionados con estrategias, decisiones y resultados empresariales.
Excluye detalles irrelevantes o promocionales.
Utiliza una estructura clara con títulos jerárquicos (#, ##, ###) y listas.
Define términos empresariales y financieros cuando sea necesario.
Incluye datos relevantes como métricas o KPIs solo si son esenciales.
Evita juicios de valor subjetivos.

Formato:

## Título Principal

Resumen estratégico del tema empresarial.

### Estrategias Clave

**Estrategia 1**: Descripción breve y enfocada.  
**Estrategia 2**: Análisis más detallado si es necesario.

### Resultados Empresariales

**KPI relevante**: Datos importantes sin redundancias.

Es importante asegurarse de que los términos técnicos utilizados sean correctos y estén basados en conceptos reales, evitando la creación de términos o definiciones no existentes.

Traducción:  
Traduce completamente todo el resumen al idioma [{}] (o al idioma que se especifique), asegurándote de que todas las secciones y detalles se presenten en dicho idioma.
"""

    EDUCATIONAL_CONTENT = """
Genera un resumen detallado en formato Markdown del siguiente texto, enfocado en la pedagogía y el aprendizaje, siguiendo estas directrices:

Prioriza la claridad y accesibilidad del contenido, adaptando el lenguaje a un público diverso.
Incluye ejemplos prácticos y aplicaciones reales cuando sea posible.
Utiliza una estructura clara con títulos jerárquicos (#, ##, ###) y listas.
Define términos pedagógicos y conceptos clave cuando sea necesario.
Evita tecnicismos innecesarios.

Formato:

## Título Principal

Explicación clara y accesible del tema educativo.

### Objetivos de Aprendizaje

**Objetivo 1**: Descripción breve y enfocada.  
**Objetivo 2**: Análisis más detallado si es necesario.

### Ejemplos Prácticos

**Ejemplo 1**: Ilustración práctica del concepto.

Es importante asegurarse de que los términos técnicos utilizados sean correctos y estén basados en conceptos reales, evitando la creación de términos o definiciones no existentes.

Traducción:  
Traduce completamente todo el resumen al idioma [{}] (o al idioma que se especifique), asegurándote de que todas las secciones y detalles se presenten en dicho idioma.
"""

    CULTURAL_CONTENT = """
Genera un resumen detallado en formato Markdown del siguiente texto, con un enfoque cultural e histórico, siguiendo estas directrices:

Resalta los aspectos culturales y contextuales relevantes del tema.
Incluye referencias históricas precisas y fechas clave cuando sea necesario.
Utiliza una estructura clara con títulos jerárquicos (#, ##, ###) y listas.
Define términos culturales o históricos complejos.
Evita sesgos o interpretaciones subjetivas.

Formato:

## Título Principal

Resumen cultural e histórico del tema.

### Contexto Histórico

**Hecho relevante 1**: Descripción breve y contextualizada.  
**Hecho relevante 2**: Análisis más detallado si es necesario.

### Aspectos Culturales

**Aspecto cultural relevante**: Explicación sin redundancias.

Es importante asegurarse de que los términos técnicos utilizados sean correctos y estén basados en conceptos reales, evitando la creación de términos o definiciones no existentes.

Traducción:  
Traduce completamente todo el resumen al idioma [{}] (o al idioma que se especifique), asegurándote de que todas las secciones y detalles se presenten en dicho idioma.
"""

    DEPORTIVE_CONTENT = """
Genera un resumen detallado en formato Markdown del siguiente texto, con un enfoque deportivo, siguiendo estas directrices:

Resalta los aspectos clave de la competición, estadísticas y estrategias deportivas.
Utiliza una estructura clara con títulos jerárquicos (#, ##, ###) y listas.
Excluye opiniones personales o juicios de valor.
Define términos deportivos y menciona resultados relevantes.

Formato:

## Título Principal

Resumen del evento o tema deportivo.

### Estadísticas y Resultados

**Dato clave 1**: Información relevante.  
**Dato clave 2**: Más detalles si es necesario.

Es importante asegurarse de que los términos técnicos utilizados sean correctos y estén basados en conceptos reales, evitando la creación de términos o definiciones no existentes.

Traducción:  
Traduce completamente todo el resumen al idioma [{}] (o al idioma que se especifique), asegurándote de que todas las secciones y detalles se presenten en dicho idioma.
"""

    POLITICAL_CONTENT = """
Genera un resumen detallado en formato Markdown del siguiente texto, con un enfoque político, siguiendo estas directrices:

Expón de manera objetiva y analítica los puntos clave relacionados con políticas, decisiones gubernamentales y contextos socio-políticos.
Utiliza una estructura clara con títulos jerárquicos (#, ##, ###) y listas.
Define términos políticos y contextos históricos relevantes.

Formato:

## Título Principal

Resumen analítico del tema político.

### Puntos Clave

**Aspecto 1**: Descripción objetiva y precisa.  
**Aspecto 2**: Más detalles si es necesario.

Es importante asegurarse de que los términos técnicos utilizados sean correctos y estén basados en conceptos reales, evitando la creación de términos o definiciones no existentes.

Traducción:  
Traduce completamente todo el resumen al idioma [{}] (o al idioma que se especifique), asegurándote de que todas las secciones y detalles se presenten en dicho idioma.
"""

    LEGAL_CONTENT = """
Genera un resumen detallado en formato Markdown del siguiente texto, con un enfoque legal, siguiendo estas directrices:

Enfatiza los aspectos normativos, legislativos y jurisprudenciales relevantes.
Utiliza una estructura clara con títulos jerárquicos (#, ##, ###) y listas.
Define términos legales y menciona referencias legislativas si es necesario.

Formato:

## Título Principal

Resumen del contenido legal.

### Aspectos Normativos

**Norma/Artículo**: Descripción breve y precisa.  
**Interpretación**: Explicación técnica sin redundancias.

Es importante asegurarse de que los términos técnicos utilizados sean correctos y estén basados en conceptos reales, evitando la creación de términos o definiciones no existentes.

Traducción:  
Traduce completamente todo el resumen al idioma [{}] (o al idioma que se especifique), asegurándote de que todas las secciones y detalles se presenten en dicho idioma.
"""

    HEALTH_CONTENT = """
Genera un resumen detallado en formato Markdown del siguiente texto, con un enfoque en la salud y bienestar, siguiendo estas directrices:

Enfatiza información precisa sobre condiciones médicas, tratamientos y recomendaciones de salud basadas en evidencia.
Utiliza una estructura clara con títulos jerárquicos (#, ##, ###) y listas.
Define términos médicos y menciona estudios o datos relevantes cuando sea necesario.

Formato:

## Título Principal

Resumen del tema de salud.

### Información Clave

**Condición/Terapia**: Descripción breve y técnica.  
**Datos relevantes**: Estadísticas o resultados si es necesario.

Es importante asegurarse de que los términos técnicos utilizados sean correctos y estén basados en conceptos reales, evitando la creación de términos o definiciones no existentes.

Traducción:  
Traduce completamente todo el resumen al idioma [{}] (o al idioma que se especifique), asegurándote de que todas las secciones y detalles se presenten en dicho idioma.
"""

    ENTERTAINMENT_CONTENT = """
Genera un resumen detallado en formato Markdown del siguiente texto, con un enfoque en entretenimiento, siguiendo estas directrices:

Destaca elementos relevantes del contenido de entretenimiento, como películas, música, videojuegos o eventos culturales.
Utiliza una estructura clara con títulos jerárquicos (#, ##, ###) y listas.
Excluye opiniones subjetivas y mantén un tono informativo.

Formato:

## Título Principal

Resumen del tema de entretenimiento.

### Elementos Destacados

**Elemento 1**: Descripción breve y concisa.  
**Elemento 2**: Más detalles si es necesario.

Es importante asegurarse de que los términos técnicos utilizados sean correctos y estén basados en conceptos reales, evitando la creación de términos o definiciones no existentes.

Traducción:  
Traduce completamente todo el resumen al idioma [{}] (o al idioma que se especifique), asegurándote de que todas las secciones y detalles se presenten en dicho idioma.
"""
