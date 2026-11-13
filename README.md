# Voces que Importan

Prototipo Chainlit de orientación para estudiantes y docentes sobre convivencia
universitaria, bienestar docente, bullying/acoso y salud mental/prevención.

## Alcance y seguridad

El agente informa, acompaña y deriva; no diagnostica, no determina culpabilidad y
no reemplaza atención clínica, institucional ni de emergencias. Ante señales de
peligro inmediato interrumpe el flujo normal y recomienda ayuda humana. Los canales
de la universidad se configuran con variables de entorno y no se inventan.

## Ejecutar

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
chainlit run app.py
```

El comando anterior inicia la aplicación sin recarga automática, que evita
errores de compatibilidad del watcher con Python 3.14. Si necesitas recarga
automática durante el desarrollo, puedes probar `chainlit run app.py -w`.

El modo `LLM_PROVIDER=demo` funciona sin credenciales y permite probar el flujo,
el RAG local y los guardrails. El adaptador de modelo está desacoplado para agregar
un proveedor posteriormente sin modificar la interfaz Chainlit.

## Evaluación

```bash
pytest -q
```

## Laboratorio de empatía

Escribí `/empatia` en el chat y describí una conversación difícil ficticia que
quieras practicar. El agente interpretará a la otra persona por turnos. La primera
respuesta se genera sin evaluación previa; desde el segundo turno, la evaluación
acumulada ajusta cuánto se abre o se cierra el personaje en la siguiente respuesta.
Para recibir una devolución completa sobre validación emocional, escucha, preguntas
abiertas, ausencia de juicio y orientación, escribí `/evaluar_empatia` o
`/salir_empatia`.
No incluyas datos personales reales. La práctica no reemplaza apoyo profesional,
institucional ni de emergencias.

La carpeta `data/sources/` contiene fuentes resumidas con URL para que cada respuesta
pueda citar evidencia. Antes de una demostración real deben verificarse vigencia,
jurisdicción y canales oficiales. La prueba urgente incluida usa un caso ficticio.

Cuando una respuesta usa evidencia RAG o recursos verificados, Chainlit muestra los
fragmentos exactos y los recursos en un mensaje separado llamado **Fuentes**. Se
omite cuando la respuesta no tiene fuentes recuperadas.

El botón **Armar bitácora de un hecho** inicia una guía temporal con preguntas sobre
fecha, lugar, hechos observables, personas presentes y observaciones. Antes de
descargar, podés revisar y corregir el resumen; el PDF separa hechos observables de
interpretaciones e impacto. El PDF se genera en memoria y la bitácora no se guarda en
el servidor.

Para la defensa, conservar capturas o un video de una ejecución demo como plan B si
falla la conexión.


# Requerimientos 
Las ultimas versiones de Python pueden generar comportamientos inesperados en Chainlit. El proyecto actual corre con Python 3.12