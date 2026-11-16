# Evaluación de Elisa

Este directorio contiene los datos ficticios, scripts y resultados de evaluación
del chatbot. La evaluación sigue el alcance definido en `plan.md`.

Todos los casos son inventados. No deben incorporarse conversaciones reales,
datos personales ni información sensible a los datasets.

## Alcance

La evaluación mide cuatro dimensiones:

- **NLP:** clasificación de tema, intención, sentimiento y emoción.
- **RAG:** recuperación de documentos y páginas esperadas entre los cuatro
  primeros resultados.
- **Seguridad:** detección de urgencias y falsas alarmas en la capa de reglas
  y, opcionalmente, en la capa de clasificación.
- **Latencia:** tiempos de NLP, RAG, recursos, LLM y flujo total.

También se incluyen:

- tres escenarios ficticios de punta a punta;
- siete reglas de oro complementarias;
- configuración de corrida con hashes del corpus y commit.

La evaluación no mide eficacia psicológica, validez clínica, utilidad real para
personas ni calidad de las citas más allá de los controles automáticos
disponibles. La fidelidad de las afirmaciones y la revisión de escenarios
requieren una revisión manual.

## Preparación

Ejecutar los comandos desde la raíz del repositorio:

```bash
.venv/bin/pip install -r requirements.txt
```

El índice de Chroma debe construirse una sola vez antes de medir:

```bash
PYTHONPATH=. .venv/bin/python -m src.rag ingest
```

La ingesta reconstruye la colección configurada en `config.json`. No debe
ejecutarse entre repeticiones de una misma evaluación.

## Ejecución

### NLP

Ejecuta los 48 casos y repite cada caso tres veces por defecto:

```bash
PYTHONPATH=. .venv/bin/python evaluacion/scripts/eval_nlp.py
```

Para cambiar la cantidad de repeticiones:

```bash
PYTHONPATH=. .venv/bin/python evaluacion/scripts/eval_nlp.py --repeticiones 1
```

Genera `resultados/nlp_resultados.json`.

El resultado incluye:

- Macro-F1 para tema, intención y sentimiento;
- reporte por clase;
- matriz de confusión;
- predicciones individuales;
- cantidad de casos ambiguos;
- latencia devuelta por el análisis NLP.

`Macro-F1` da el mismo peso a cada clase. Con solo 6 a 14 ejemplos por clase,
un error puede cambiar considerablemente el resultado. Deben informarse también
los conteos y no presentar el resultado como precisión general del sistema.

### RAG

Ejecuta las 15 consultas con el umbral productivo configurado y con umbral
cero para separar el comportamiento de ranking del filtrado por relevancia:

```bash
PYTHONPATH=. .venv/bin/python evaluacion/scripts/eval_rag.py
```

Para ejecutar un umbral específico:

```bash
PYTHONPATH=. .venv/bin/python evaluacion/scripts/eval_rag.py --threshold 0.3
```

Genera `resultados/rag_resultados.json`.

Se reportan:

- `hit_documento`: el documento esperado aparece entre los cuatro primeros;
- `hit_documento_pagina`: además, la página coincide con una tolerancia de
  ±1 página;
- `sin_evidencia_correcto`: las consultas sin evidencia no devuelven resultados;
- resultados completos, relevancia, filtro aplicado y metadatos de cada consulta.

Las consultas `sin_evidencia` son negativas: un resultado semánticamente
parecido no debe interpretarse automáticamente como evidencia válida. Si el
resultado esperado es cero y aparecen fragmentos, existe sobre-recuperación y
debe analizarse antes de usar el resultado como prueba de ausencia.

La página registrada es la página del PDF cargado por `PyPDFLoader`. Puede no
coincidir con la numeración editorial impresa dentro del documento. Esta
diferencia debe declararse cuando se comparan páginas, especialmente para el
caso de Resett y Putallaz.

### Seguridad

Para medir únicamente las reglas locales, sin llamadas al LLM:

```bash
PYTHONPATH=. .venv/bin/python evaluacion/scripts/eval_seguridad.py --no-llm
```

Para medir reglas más clasificación NLP:

```bash
PYTHONPATH=. .venv/bin/python evaluacion/scripts/eval_seguridad.py
```

La segunda modalidad requiere el modelo y credenciales configurados en `.env`.
Genera `resultados/seguridad_resultados.json`.

Interpretación:

- `recall_urgencias`: urgencias detectadas correctamente sobre las 12 urgencias;
- `falsas_alarmas`: controles clasificados erróneamente como urgentes sobre los
  12 controles;
- `por_capa`: capa que detectó cada urgencia;
- `llm_ejecutado`: permite verificar si se llamó o no a la segunda capa.

Una urgencia no detectada es una falla grave de seguridad. No debe compensarse
con buenos resultados de NLP, RAG o latencia.

### Cobertura de citas

La cobertura de citas se puede medir automáticamente sobre las consultas que
requieren evidencia:

```bash
PYTHONPATH=. .venv/bin/python evaluacion/scripts/eval_citas.py
```

El script ejecuta el flujo completo para cada consulta, extrae citas de la
respuesta con una expresión regular y las compara con los resultados recuperados
en ese mismo turno. Para contar como cubierta, una respuesta debe contener:

- el nombre de la fuente;
- un año de cuatro dígitos;
- una página;
- una coincidencia con fuente, año y página de un fragmento recuperado.

El resultado se guarda en `resultados/citas_resultados.json`. La métrica
`cobertura` es la proporción de respuestas exitosas que cumplen todo lo anterior.
Las respuestas con error se cuentan aparte y no se incluyen en el denominador.

Este control verifica presencia y correspondencia de metadatos, no fidelidad
semántica. Una cita puede tener fuente, año y página correctos y aun así no
respaldar la afirmación concreta. Esa revisión sigue siendo manual.

### Latencia

Ejecuta las 15 consultas RAG y los tres escenarios, tres veces cada uno por
defecto, para un total esperado de 54 corridas:

```bash
PYTHONPATH=. .venv/bin/python evaluacion/scripts/eval_latencia.py
```

Genera `resultados/latencia_resultados.json`.

Para una prueba rápida:

```bash
PYTHONPATH=. .venv/bin/python evaluacion/scripts/eval_latencia.py --repeticiones 1
```

Se calculan mediana y p95 para cada componente. Las corridas con error se
cuentan en `n_fallos` y no se incluyen en las estadísticas de latencia.
La latencia depende de red, proveedor, modelo, carga del equipo, cachés y
arranque en frío; por eso los valores solo son comparables bajo condiciones
similares.

## Archivos de resultados

Los scripts escriben en `evaluacion/resultados/`:

```text
nlp_resultados.json
rag_resultados.json
seguridad_resultados.json
latencia_resultados.json
citas_resultados.json
```

También generan `evaluacion/config_corrida.json`, que registra fecha, modelo,
embeddings, parámetros del índice, hashes SHA-256 del corpus, equipo y commit.
Este archivo debe conservarse junto con los resultados de una corrida que se
quiera reportar.

Los resultados generados no deben mezclarse entre corridas. Antes de una nueva
medición, archivar o limpiar los JSON anteriores y conservar su
`config_corrida.json` correspondiente.

## Orden recomendado

1. Congelar y revisar los CSV de `datos/`.
2. Construir Chroma una sola vez.
3. Ejecutar NLP.
4. Ejecutar RAG.
5. Ejecutar seguridad local y luego seguridad con LLM.
6. Ejecutar latencia.
7. Revisar manualmente citas y los tres escenarios.
8. Guardar resultados, configuración y observaciones.

Si se modifica el código, los prompts, el corpus, los metadatos o el umbral
después de una medición, la evaluación deja de ser independiente. Debe
conservarse el resultado anterior y reportarse por separado como `antes` y
`después`.

## Limitaciones conocidas

- Los datasets son pequeños y fueron redactados por una sola persona.
- No hay acuerdo entre revisores ni kappa inter-anotador.
- Las clases ambiguas pueden producir variación legítima en el análisis NLP.
- El LLM no es completamente determinista y el proveedor puede cambiar.
- Hit@4 mide si aparece al menos un acierto; no mide Recall@4.
- La recuperación semántica puede devolver resultados para consultas sin
  evidencia; el umbral actual no garantiza por sí solo `SIN_EVIDENCIA`.
- La validación automática de citas todavía no determina si una afirmación está
  realmente respaldada por el fragmento citado.
- La numeración de páginas puede ser la del PDF y no la impresa.
- Los escenarios requieren inspección manual de tono, alcance y citas.
- No se evalúan eficacia psicológica, resultados clínicos ni impacto en usuarios.
- Los resultados de latencia no son generalizables a otras redes, equipos o
  proveedores.
