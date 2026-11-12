import chainlit as cl
from src.agent import ConversationalAgent
from src.config import configure_logging
import logging

# Crear logger para la interfaz de usuario
configure_logging()
logger = logging.getLogger("App")

_STEP_LABELS = {
    "analysis": "Analizando la situación",
    "evidence": "Consultando evidencia",
    "resources": "Buscando recursos",
}

@cl.on_chat_start
async def start() -> None:
    cl.user_session.set("agent", ConversationalAgent())
    await cl.Message(
        content=(
            "¡Hola! Soy **Elisa**, un espacio de escucha y orientación "
            "sobre bienestar docente y convivencia universitaria.\n\n"
            "¿Cómo te sentís hoy o sobre qué situación te gustaría conversar?"
        )   
    ).send()

@cl.on_message
async def main(msg: cl.Message) -> None:
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
    await cl.Message(content=response).send()
