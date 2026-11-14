import chainlit as cl
import logging

from src.agent import ConversationalAgent
from src.config import AgentSettings, configure_logging
from src.avatar_emotion import avatar_signal, avatar_alert
from src.empathy import EmpathyLab, format_empathy_evaluation
from src.journal import JournalSession, format_journal, generate_journal, journal_docx
from src.audio import speech_to_text

# Crear logger para la interfaz de usuario
configure_logging()
logger = logging.getLogger("App")

_STEP_LABELS = {
    "analysis": "Analizando situación",
    "evidence": "Consultando evidencia",
    "resources": "Buscando recursos"
}

commands = [
    {"id": "Empatía", "icon": "heart", "description": "Iniciar laboratorio de empatía"},
    {"id": "Evaluar empatía", "icon": "check", "description": "Evaluar la práctica de empatía"},
    {"id": "Salir de empatía", "icon": "x", "description": "Salir del laboratorio de empatía"},
    {"id": "Bitácora", "icon": "notebook-pen", "description":"Arma un resumen de un hecho"}
]

@cl.on_chat_start
async def start() -> None:
    cl.user_session.set("agent", ConversationalAgent())
    #await cl.Message(
    #    content=(
    #        "¡Hola! Soy **Elisa**, un espacio de escucha y orientación "
    #        "sobre bienestar docente y convivencia universitaria.\n\n"
    #        "¿Cómo te sentís hoy o sobre qué situación te gustaría conversar?"
    #    ),
     #   elements=[avatar_signal(emotion="greeting")],
    #).send()
    await cl.context.emitter.set_commands(commands)

@cl.on_audio_start
async def on_audio_start():
    # Inicializa el almacenamiento para los fragmentos de audio
    cl.user_session.set("audio_chunks", [])
    return True

@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    # Guarda cada fragmento recibido en la sesión
    audio_chunks = cl.user_session.get("audio_chunks")
    if audio_chunks is not None:
        audio_chunks.append(chunk.data)

@cl.on_audio_end
async def on_audio_end():
    await cl.context.emitter.task_end()  # oculta el loader
    audio_chunks = cl.user_session.get("audio_chunks")
    if not audio_chunks:
        return
    audio_bytes = b"".join(audio_chunks)
    try:
        content = await speech_to_text(audio_bytes)
        logger.info(f"Transcripción de audio: {content}")
        if not content:
            await cl.ErrorMessage(content="No se pudo transcribir el audio. Por favor, intentá nuevamente.").send()
            await avatar_alert()
            return

        await cl.send_window_message({"type": "dictation", "text": content})
    except Exception as e:
        await cl.ErrorMessage(content=f"Error al procesar el audio: {e}").send()
        await avatar_alert()
        logger.error(f"Error al procesar el audio: {e}")

    cl.user_session.set("audio_chunks", []) # Limpiar los fragmentos de audio después de procesarlos

@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Hablar con un amigo",
            message="Hola, podemos hablar un rato sobre algo que me preocupa. Quiero que me esuches como si fueras mi amigo.",
            icon="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNmZjQwMTMiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBjbGFzcz0ibHVjaWRlIGx1Y2lkZS1tZXNzYWdlLWNpcmNsZS1oZWFydCBwcmV2aWV3LWljb24iPjxwYXRoIGQ9Ik0yLjk5MiAxNi4zNDJhMiAyIDAgMCAxIC4wOTQgMS4xNjdsLTEuMDY1IDMuMjlhMSAxIDAgMCAwIDEuMjM2IDEuMTY4bDMuNDEzLS45OThhMiAyIDAgMCAxIDEuMDk5LjA5MiAxMCAxMCAwIDEgMC00Ljc3Ny00LjcxOSIvPjxwYXRoIGQ9Ik03LjgyOCAxMy4wN0EzIDMgMCAwIDEgMTIgOC43NjRhMyAzIDAgMCAxIDUuMDA0IDIuMjI0IDMgMyAwIDAgMS0uODMyIDIuMDgzbC0zLjQ0NyAzLjYyYTEgMSAwIDAgMS0xLjQ1LS4wMDF6Ii8+PC9zdmc+"
        ),
        cl.Starter(
            label="Practicar conversación difícil",
            message="",
            command="Empatía",
            icon="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiMwMGM3ZmMiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBjbGFzcz0ibHVjaWRlIGx1Y2lkZS11c2VycyBwcmV2aWV3LWljb24iPjxwYXRoIGQ9Ik0xNiAyMXYtMmE0IDQgMCAwIDAtNC00SDZhNCA0IDAgMCAwLTQgNHYyIi8+PHBhdGggZD0iTTE2IDMuMTI4YTQgNCAwIDAgMSAwIDcuNzQ0Ii8+PHBhdGggZD0iTTIyIDIxdi0yYTQgNCAwIDAgMC0zLTMuODciLz48Y2lyY2xlIGN4PSI5IiBjeT0iNyIgcj0iNCIvPjwvc3ZnPg=="
        ),
        cl.Starter(
            label="Registrar situación en la Bitácora",
            message="",
            command="Bitácora",
            icon="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNmNWVjMDAiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBjbGFzcz0ibHVjaWRlIGx1Y2lkZS1maWxlLXRleHQgcHJldmlldy1pY29uIj48cGF0aCBkPSJNNiAyMmEyIDIgMCAwIDEtMi0yVjRhMiAyIDAgMCAxIDItMmg4YTIuNCAyLjQgMCAwIDEgMS43MDQuNzA2bDMuNTg4IDMuNTg4QTIuNCAyLjQgMCAwIDEgMjAgOHYxMmEyIDIgMCAwIDEtMiAyeiIvPjxwYXRoIGQ9Ik0xNCAydjVhMSAxIDAgMCAwIDEgMWg1Ii8+PHBhdGggZD0iTTEwIDlIOCIvPjxwYXRoIGQ9Ik0xNiAxM0g4Ii8+PHBhdGggZD0iTTE2IDE3SDgiLz48L3N2Zz4="
        ),
        cl.Starter(
            label="Buscar canales y recursos de ayuda",
            message="Necesito buscar recursos y canales de orientación institucionales para abordar mi caso.",
            icon="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiM3N2JiNDEiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBjbGFzcz0ibHVjaWRlIGx1Y2lkZS1zaGllbGQtY2hlY2sgcHJldmlldy1pY29uIj48cGF0aCBkPSJNMjAgMTNjMCA1LTMuNSA3LjUtNy42NiA4Ljk1YTEgMSAwIDAgMS0uNjctLjAxQzcuNSAyMC41IDQgMTggNCAxM1Y2YTEgMSAwIDAgMSAxLTFjMiAwIDQuNS0xLjIgNi4yNC0yLjcyYTEuMTcgMS4xNyAwIDAgMSAxLjUyIDBDMTQuNTEgMy44MSAxNyA1IDE5IDVhMSAxIDAgMCAxIDEgMXoiLz48cGF0aCBkPSJtOSAxMiAyIDIgNC00Ii8+PC9zdmc+"
        )
    ]

@cl.on_message
async def main(msg: cl.Message) -> None:
    if msg.command == "Bitácora":
        cl.user_session.set("journal", JournalSession())
        await cl.Message(
                content=(
                    "Iniciemos una bitácora privada y temporal. La información se mantiene "
                    "solo durante esta sesión y no se guarda en el servidor.\n\n"
                    "Te voy a hacer algunas preguntas. No incluyas datos que no quieras "
                    "presentar ante la oficina de convivencia.\n\n"
                    f"{JournalSession().current_question}"
                )
            ).send()
        return

    journal = cl.user_session.get("journal")
    if isinstance(journal, JournalSession):
        if journal.reviewing:
            if msg.content.strip().lower() in {"confirmar", "descargar"}:
                if journal.entry is None:
                    await cl.Message(content="No hay un resumen listo para descargar.").send()
                    return
                file = cl.File(
                    name="bitacora_hechos.docx",
                    content=journal_docx(journal.entry),
                    display="inline",
                )
                await cl.Message(
                    content="Tu bitácora está lista para descargar. No se guardó en el servidor.",
                    elements=[file, avatar_signal(emotion="archievement")],
                ).send()
                cl.user_session.set("journal", None)
                return
            if journal.correction(msg.content):
                try:
                    journal.entry = await generate_journal(AgentSettings.load(), journal.answers)
                except Exception as exc:
                    logger.error(f"Error al actualizar la bitácora: {exc}")
                    await cl.ErrorMessage(
                        content="No pude actualizar la bitácora. Intentá nuevamente."
                    ).send()
                    await avatar_alert()
                    return
                await cl.Message(content="Bien! dime que tal ahora?",
                    elements=[cl.Text(content=format_journal(journal.entry), name="Resumen para revisión", display="side")]
                ).send()
                return

        journal.record(msg.content)
        if not journal.complete:
            await cl.Message(content=journal.current_question).send()
            return
        try:
            journal.entry = await generate_journal(AgentSettings.load(), journal.answers)
        except Exception as exc:
            logger.error(f"Error al generar la bitácora: {exc}")
            await cl.ErrorMessage(
                content="No pude generar el resumen. Intentá nuevamente."
            ).send()
            await avatar_alert()
            return
        journal.reviewing = True
        await cl.Message(content="Escribí `confirmar` para descargar o una corrección con el formato "
                        "`campo: corrección`.",
            elements=[cl.Text(content=format_journal(journal.entry), name="Resumen para revisión", display="side")]
        ).send()
        return

    empathy_lab = cl.user_session.get("empathy_lab")

    if msg.command == "Empatía":
        cl.user_session.set("empathy_lab", EmpathyLab(AgentSettings.load()))
        await cl.Message(
            content="Describí una conversación difícil que quieras practicar. "
                    "Es una simulación ficticia: no incluyas datos personales reales."
        ).send()
        return

    if msg.command == "Evaluar empatía":
        if not isinstance(empathy_lab, EmpathyLab):
            await cl.Message(content="No hay un laboratorio de empatía activo.").send()
            return
        try:
            evaluation = await empathy_lab.evaluate()
        except ValueError as exc:
            await cl.Message(content=str(exc)).send()
        else:
            await cl.Message(content="Perfecto! Aquí te entrego la evaluación",
                elements=[cl.Text(content=format_empathy_evaluation(evaluation), name="Devolución del laboratorio de empatía", display="side")]
            ).send()
        return

    if msg.command == "Salir de empatía":
        if not isinstance(empathy_lab, EmpathyLab):
            await cl.Message(content="No hay un laboratorio de empatía activo.").send()
            return
        cl.user_session.set("empathy_lab", None)
        await cl.Message(content="Saliste del laboratorio de empatía.").send()
        return

    if isinstance(empathy_lab, EmpathyLab):
        if not empathy_lab.active:
            try:
                empathy_lab.begin(msg.content)
            except ValueError as exc:
                await cl.Message(content=str(exc)).send()
                return
            await cl.Message(
                content="Listo. Yo voy a interpretar a la otra persona. "
                        "Escribí tu primera respuesta; cuando termines, usá `/Evaluar empatía`."
            ).send()
            return
        try:
            response = await empathy_lab.respond(msg.content)
            await cl.Message(
                content=response,
                elements=[avatar_signal(agent=cl.user_session.get("agent"))],
            ).send()
        except Exception as e:
            logger.error(f"Error en el laboratorio de empatía: {e}")
            await cl.ErrorMessage(content="No pude continuar la práctica. Intentá nuevamente.").send()
            await avatar_alert()
        return

    agent = cl.user_session.get("agent")
    if not isinstance(agent, ConversationalAgent):
        logger.error("No se pudo inicializar la sesión del agente.")
        await cl.ErrorMessage(
            content="Hubo un error al iniciar la sesión del agente. Por favor, recargá la página."
        ).send()
        await avatar_alert()
        raise RuntimeError("No se pudo inicializar la sesión del agente.")
    
    # atrapar errores en el agente y responder con un mensaje genérico
    try:
        active_steps: dict[str, cl.Step] = {}
        async def report_progress(stage: str, status: str) -> None:
            label = _STEP_LABELS.get(stage)
            if not label:
                return

            if status == "started":
                step = cl.Step(name=label, type="tool")
                step.output = "En curso..."
                await step.__aenter__()
                active_steps[stage] = step
                return

            if status == "completed":
                step = active_steps.pop(stage, None)
                if step is None:
                    return

                step.output = "Completado."
                await step.__aexit__(None, None, None)

        response = await agent.respond(msg.content, progress=report_progress)
    except Exception as e:
        logger.error(f"Error en la consulta: {e}")
        await cl.ErrorMessage(
            content=f"Ocurrio un error en la consulta {e}"
        ).send()
        await avatar_alert()
        raise e

    elements = []
    if agent.last_sources:
        elements.append(cl.Text(content=agent.last_sources, name="Fuentes y referencias:", display="side"))

    elements.append(avatar_signal(agent=agent))
    await cl.Message(content=response, elements=elements).send()