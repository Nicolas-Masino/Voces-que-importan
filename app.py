import chainlit as cl
from src.agent import ConversationalAgent
from src.config import AgentSettings, configure_logging
from src.empathy import EmpathyLab, format_empathy_evaluation
from src.journal import JournalSession, format_journal, generate_journal, journal_pdf
import logging

# Crear logger para la interfaz de usuario
configure_logging()
logger = logging.getLogger("App")

_STEP_LABELS = {
    "analysis": "Analizando la situación",
    "evidence": "Consultando evidencia",
    "resources": "Buscando recursos",
}

commands = [
    {"id": "Empatía", "icon": "heart", "description": "Iniciar laboratorio de empatía"},
    {"id": "Evaluar empatía", "icon": "check", "description": "Evaluar la práctica de empatía"},
    {"id": "Salir de empatía", "icon": "x", "description": "Salir del laboratorio de empatía"},
]

@cl.on_chat_start
async def start() -> None:
    cl.user_session.set("agent", ConversationalAgent())
    # accion de inicio de bitacora de hechos
    actions = [
        cl.Action(
            name="iniciar_bitacora",
            icon="file-text",
            payload={"value": "example_value"},
            label="Armar bitácora de un hecho"
        )
    ]
    await cl.Message(
        content=(
            "¡Hola! Soy **Elisa**, un espacio de escucha y orientación "
            "sobre bienestar docente y convivencia universitaria.\n\n"
            "¿Cómo te sentís hoy o sobre qué situación te gustaría conversar?"
        ),
        actions=actions
    ).send()
    await cl.context.emitter.set_commands(commands)

# callback para manejar la acción de iniciar bitácora
@cl.action_callback("iniciar_bitacora")
async def on_action(action: cl.Action):
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

@cl.on_message
async def main(msg: cl.Message) -> None:
    journal = cl.user_session.get("journal")
    if isinstance(journal, JournalSession):
        if journal.reviewing:
            if msg.content.strip().lower() in {"confirmar", "descargar"}:
                if journal.entry is None:
                    await cl.Message(content="No hay un resumen listo para descargar.").send()
                    return
                file = cl.File(
                    name="bitacora_hechos.pdf",
                    content=journal_pdf(journal.entry),
                    display="inline",
                )
                await cl.Message(
                    content="Tu bitácora está lista para descargar. No se guardó en el servidor.",
                    elements=[file],
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
                    return
                await cl.Message(content=format_journal(journal.entry)).send()
                return
            await cl.Message(
                content="Escribí `confirmar` para descargar o una corrección con el formato "
                        "`campo: corrección`."
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
            return
        journal.reviewing = True
        await cl.Message(content=format_journal(journal.entry)).send()
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
            await cl.Message(content=format_empathy_evaluation(evaluation)).send()
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
            await cl.Message(content=response).send()
        except Exception as e:
            logger.error(f"Error en el laboratorio de empatía: {e}")
            await cl.ErrorMessage(content="No pude continuar la práctica. Intentá nuevamente.").send()
        return

    agent = cl.user_session.get("agent")
    if not isinstance(agent, ConversationalAgent):
        logger.error("No se pudo inicializar la sesión del agente.")
        await cl.ErrorMessage(
            content="Hubo un error al iniciar la sesión del agente. Por favor, recargá la página."
        ).send()
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
        raise e

    elements = []
    if agent.last_sources:
        elements.append(cl.Text(content="**Fuentes y referencias:**\n" + "\n\n".join(agent.last_sources), name="fuentes", display="side"))

    await cl.Message(content=response, elements=elements).send()