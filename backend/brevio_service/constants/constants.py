class Constants:
    TRANSCRIPTION_FILE = "transcription.txt"
    SUMMARY_FILE = "summary.txt"
    ALL_TRANSCRIPTIONS = "all_transcriptions.txt"
    ALL_SUMMARIES = "all_summaries.txt"
    DESTINATION_FOLDER = "audios"

    CONTENT = """
    Por favor, analiza el siguiente texto y genera un contenido breve y conciso en formato Markdown, orientado al contexto de Terraform y su ecosistema. El resultado debe cumplir con las siguientes características:
    Exposición clara y breve de las ideas principales: Evita profundizar en los detalles; presenta únicamente los conceptos clave de manera directa y precisa.
    Incluye ejemplos de código solo si son esenciales para comprender el concepto, manteniéndolos extremadamente cortos y claros.
    Usa un tono profesional y accesible, adecuado para estudiantes y profesores universitarios, asegurándote de que el contenido sea fácil de entender.
    Organiza la información de forma fluida y compacta, evitando explicaciones extensas o superfluas.
    Verifica la precisión de términos y conceptos relacionados con Terraform. Corrige errores comunes y usa la terminología estándar, por ejemplo:
    Usa "Terraform" correctamente en lugar de "terra form" o "Terraformer".
    Asegúrate de emplear términos como resources, providers, state, y modules de manera precisa.
    Además, organiza el texto con títulos y estilos en Markdown siguiendo estas directrices:

    Títulos jerárquicos (#, ##, ###) para estructurar las secciones principales del contenido.
    Listas (- o 1.) para elementos relacionados o enumeraciones.
    Resalta palabras clave o conceptos importantes utilizando negritas o cursivas.
    Incluye fragmentos de código relevantes utilizando bloques de código con backticks (`) o triples backticks (```).

Ejemplo de salida esperada:

Texto original:

    Terraform utiliza configuraciones en HCL para gestionar infraestructura como código. Los recursos son elementos clave que definen objetos gestionados, como instancias EC2 o buckets S3. Un proveedor conecta Terraform con el servicio deseado, como AWS o Google Cloud. Los estados permiten rastrear los cambios realizados en la infraestructura.
    Texto transformado:
    ## Introducción a Terraform

Terraform permite gestionar la **infraestructura como código** mediante configuraciones en HCL.

### Elementos principales
- **Recursos**: Representan objetos gestionados, como:
  - Una instancia EC2.
  - Un bucket S3.
- **Proveedores**: Conectan Terraform con servicios específicos, como AWS o Google Cloud.
- **Estado**: Rastrean cambios realizados en la infraestructura, asegurando coherencia.

### Ejemplo básico de configuración

```hcl
provider "aws" {
  region = "us-west-1"
}

resource "aws_instance" "example" {
  ami           = "ami-123456"
  instance_type = "t2.micro"
}


Este ejemplo define un proveedor de AWS y crea una instancia EC2 simple.

Aplica este enfoque al texto proporcionado, asegurando que la presentación sea profesional, coherente y adecuada para un entorno universitario.
"""


    