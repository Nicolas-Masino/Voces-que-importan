# Elisa

Es un agente conversacional diseñado para la orientación segura de estudiantes y docente sobre convivencia universitaria,
bullying/acoso y salud mental. El objetivo del agente es acompañar y derivar si es necesario: no diagnostica ni mucho menos reemplaza ayuda humana.

## Funcionalidades

Cuenta con una base de conocimientos de recursos universitarios y documentación científica basados en sistemas de retrieval (RAG), los cuales permiten que el modelo se sustente de información verificada. Además, incorpora técnicas de procesamiento del lenguaje natural (NLP) para el análisis de sentimiento, emoción, intención, entre otros; con evaluaciones de seguridad para detectar situaciones críticas y derivar con un profesional. 

Junto a ello se logra tener respuestas más ricas, seguras e informadas.

### Laboratorio de empatía

La idea del laboratorio de empatía es permitirle al usuario practicar una conversación difícil en un entorno seguro y simulado. De esta manera, entrena su empatía y habilidades blandas para comunicar mejor sus preocupaciones o deseos, sin herir a nadie.

Para activarlo se utiliza el comando `Empatía`. Una vez inicializado, el agente le pedirá que describa la situación y las personas involucradas para tener una mejor noción y elaborar respuestas como si fuera una charla real con la otra parte. Conviene indicar explícitamente el rol del usuario y el de la contraparte (por ejemplo, “soy docente y el coordinador me asignó una tarea”): el simulador interpreta la contraparte, no reescribe ni responde en nombre del usuario.

Cuenta con un sistema de penalización para medir prejuicios, paráfrasis y falta de compresión por parte del usuario. Así, el comportamiento del modelo se verá modificada dependiendo de esta puntuación. Dicho score es posible obtenerlo con el comando `Evaluar empatía`, junto a un resumen de fortalezas y oportunidades de mejora. 

Para salir del laboratorio y volver a la conversación normal del agente se utiliza el comando `Salir de empatía`.

### Bitácora de hechos

Una nueva funcionalidad que permite llevar un registro de alguna situación que al usuario le haya incomodado como para presentar a una oficina de convivencia institucional. 

Se inicializa la bitácora con el comando `Bitácora`, con lo cual el agente continuara haciendo una serie de preguntas sobre el evento: donde sucedió, cuando, con quienes, una descripción y observaciones adicionales. La interacción con el LLM fue especificado para separar estrictamente hechos observables de interpretaciones o sensaciones subjetivas, ni mucho menos de determinar responsabilidades. 

Al finalizar con las preguntas se ofrece al usuario la posibilidad de cambiar algún dato o de descargar la bitácora en formato .docx.