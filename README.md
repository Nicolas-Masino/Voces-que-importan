# Voces que Importan

Es un prototipo Chainlit de orientación para estudiantes y docentes sobre convivencia universitaria y bienestar docente. La idea del proyecto es crear un agente conversacional centrado en dos temáticas principales: bullying/acoso y salud mental/prevención.

## Alcance y seguridad

El agente tiene por finalidad informar, acompañar y derivar a ayuda humana en caso de peligro inmediato o si es necesario. El mismo no diagnostica, no determina culpabilidad y mucho menos reemplaza atención clínica, institucional ni de emergencias. 

En el caso de peligro inmediato, autolesión, ideas suicidas, o violencia en curso, propias o de otra persona. El sistema de seguridad detiene el flujo normal de la conversación, derivan a ayuda humana y le piden al usuario que llame al 911 si es efectiva la emergencia. Dicho sistema consta de dos pruebas: 
1. Expresiones regulares: una primera prueba rápida y que no depende de ningún servicio API, evalúa peligro mediante expresiones regulares.
2. LLM: una segunda prueba más exhaustiva que integra información contextual del mensaje, evalúa mediante el LLM una situación de peligro.

Es condición suficiente que cualquiera de las dos pruebas fallen para detener el flujo normal del agente, y recomendar ayuda humana.

## Ejecutar

Para instalar el programa se debe crear un entorno virtual con todas las dependencias exhibidas en `requirements.txt`. 
Se debe crear un archivo `.env` similar a `.env.example` para especificar el modelo LLM que se utilizara y guardar la API key de su servicio de IA.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
chainlit run app.py
```

El comando anterior inicia la aplicación sin recarga automática. Si necesario la recarga automática durante el desarrollo, especifique `chainlit run app.py -w` en su lugar.

**NOTA**: Existe una incompatibilidad entre Python 3.14 y el watcher de Chainlit, por lo que se recomienda usar Python 3.12.

El adaptador de modelo está desacoplado para agregar un proveedor posteriormente sin modificar la interfaz Chainlit.

## Evaluación

Ejecuta todos los tests (unitarios y de integración) para evaluar contratos de las funciones y coherencia de la aplicación

```bash
pytest -q
```

## Funcionalidades

El core principal del agente se divide en dos instancias: (i) primero, un módulo de procesamiento de lenguaje natural potenciado con IA generativa que genera un análisis incluyendo, sentimiento (positivo, negativo o neutro), emoción (alegría, tristeza, enojo, miedo, sorpresa o disgusto), la intención (pedir consejo, desahogarse, buscar orientación o emergencia si se detecta situación de peligro), el tópico (bienestar docente, convivencia universitaria, bullying y acoso, xenofobia y discriminación, salud mental u otro), el ámbito (internacional, nacional, provincial, local o institucional) y la confianza (media, baja o alta); (ii) el agente en sí mismo que toma dicho análisis de NLP para enriquecer sus respuestas. 

El módulo de NLP resulta de gran importancia, ya que no solo sirve para guiar la generación de respuestas, sino que también alimenta a las demás funcionalidades del chatbot, y determina comportamientos. En este sentido, el tono del agente es determinado en función de la emoción detectada en el usuario, las herramientas de consultar evidencia y orientar recursos se habilitan si la intención detectada es «pedir consejo» o «buscar orientación», respectivamente. Además, representa la segunda capa de seguridad si se percibe una emergencia.

### Sistema de Recuperación de Información Aumentada (RAG)

Un objetivo importante del proyecto es construir un agente basado en conocimiento verificado y respaldado para evitar alucinaciones. Para ello se implementa un retrieval con embeddings basado en `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` y almacenado en una base vectorial ChromaDB.

La recuperación de información calcula la similitud de la consulta en el espacio de embeddings de los documentos y devuelve aquellas fuentes con similitud mayor a 0.3 (consideradas relevantes). Dichos documentos se deben almacenar en la carpeta `data/sources` sumado a un archivo `manifest.json` que guarda metadatos de los documentos, esenciales para que el agente pueda citar correctamente cada uno y además habilitar una búsqueda por tópicos. 

Aquí un ejemplo que debe contener obligatoriamente el `manifest.json`:

```json
MANIFEST_EJEMPLO = {
    "oit_violencia_educacion.pdf": {
        "fuente": "OIT - Violencia y acoso en educación",
        "anio": 2023,
        "pais": "Internacional",
        "region": "Global",
        "url": "https://...",
        "topicos": ["bullying y acoso", "bienestar docente", "convivencia universitaria"],
    }
}
```

El RAG solo se inicia si el módulo de NLP detecta que la intención es «pedir consejo».

El corpus RAG no se reconstruye automáticamente, es necesario generar el índice chroma mediante:

```bash
.venv/bin/python -m src.rag ingest
```

### Recursos institucionales y globales

Dentro del archivo `config.json` se almacena todos los recursos disponibles que tiene el agente para orientar al usuario si así lo desea. Dichos, pueden ser tanto institucionales como globales y no dependen de un sistema RAG, sino de una búsqueda jerárquica y por prioridades. 

Cuando el módulo de NLP detecta que la intención es «buscar orientación», se le habilita al agente las herramientas de buscar recursos, los cuales toman el tópico y alcance de la situación, y aplican un doble filtrado a los recursos: primero por tópicos y luego por orden de prioridad. Las jerarquías funcionan de la siguiente manera:

1. Si se detectó el ámbito, es decir, no es null y está dentro de la lista cerrada de scopes posibles, obtiene la prioridad del ámbito solicitado
2. Elimina los recursos con ámbitos menores al solicitado considerando que internacional>institucional, es decir, si se solicita un ámbito provincial, el local y el institucional quedan descartados
3. Revierte la lista de prioridades para que el solicitado tenga mayor prioridad, es decir, si se solicita un ámbito provincial, aquellos recursos provinciales tiene mayor prioridad, los nacionales son los siguientes y por último los internacionales.
4. Devuelve los primeros N recursos que prevalecieron (por default N=4)

Aquí un ejemplo de recurso almacenado en `config.json` con los campos obligatorios:

```json
{ "resources": {
"name":{
            "name": "Ejemplo", 
            "description": "Es un ejemplo de recurso", 
            "url": "https://www.ejemplo-recurso.com/", 
            "scope": "nacional",
            "topic": ["salud mental"]
        }
}
}
```

Cuando una respuesta usa evidencia RAG o recursos verificados, Chainlit muestra los fragmentos exactos y los recursos en el panel lateral llamado **Fuentes**. Se oculta el panel cuando la respuesta no tiene fuentes recuperadas.

### Laboratorio de empatía

El laboratorio de empatía fue desarrollado para que las personas practiquen una conversación difícil que deben tener, en un entorno seguro y simulado. Se inicializa bajo el comando `Empatía`.

Una vez comenzado, el agente le pedirá que describa la situación y los roles involucrados para interpretar a la otra persona, simular una charla real y obtener un personaje ficticio. El usuario debe indicar quién es y quién es la contraparte (por ejemplo, «soy docente y el coordinador me asignó una tarea»): el simulador responde como la contraparte, no en nombre del usuario. En función de cómo el usuario responda y plantee la conversación, el LLM lo estará evaluando mediante la siguiente rúbrica:

- Validación emocional
- Escucha y paráfrasis
- Ausencia de juicio o minimización
- Orientación o próximos pasos apropiados
- Nivel de preguntas abiertas

Cada aspecto se evalúa de 1 a 5. Por cada turno, el agente toma la evaluación, lo pondera siguiendo los pesos expuestos en el archivo `config.json`, y determina el comportamiento del personaje ficticio. De este modo, si se consigue un puntaje máximo, el personaje tendrá un comportamiento abierto (habla con más confianza y profundiza sobre lo que siente), si se consigue el puntaje mínimo tendrá un comportamiento cerrado (responde poco, con cautela; todavía no confía). En el primer turno se comienza con un comportamiento cauteloso (cuenta lo justo y necesario; mide cada palabra). 

En cada momento el usuario puede obtener la evaluación completa de toda la conversación, mas puntos de mejora y fortalezas con el comando `Evaluar empatía`. Para salir del laboratorio, se emplea el comando `Salir de empatía`.

### Bitácora de hechos

El comando `Bitácora` inicia una guía temporal con preguntas sobre fecha, lugar, hechos observables, personas presentes y observaciones para registrar una situación que le haya incomodado al usuario. La interacción con el LLM fue especificado para separar estrictamente hechos observables de interpretaciones o sensaciones subjetivas, ni mucho menos para determinar responsabilidades. 

Al finalizar con las respuestas, se le exhibe al usuario la bitácora final resumida, y se le da la posibilidad de corregir un campo mediante un mensaje en formato **campo: valor actualizado** o de confirmar la operación. Una vez confirmada, se entrega la bitácora en formato .docx para que pueda ser descargada y presentada ante un comité psicológico, oficina de convivencia o secretaria académica.

## Configuraciones

El agente tiene un módulo especializado para centralizar todas las configuraciones, ya sea del agente mismo (como modelo, api key, proveedor, etc), del RAG (directorio de Chroma, modelo de embeddings, chunks, etc.) y del laboratorio de empatía. Estas configuraciones se lee en gran parte desde el archivo `config.json` a excepción de las configuración del agente que se leen del archivo `.env`. 

Dentro del archivo `config.json` también se encuentra la lista de tópicos que el agente puede manejar y espera, además de los recursos.
