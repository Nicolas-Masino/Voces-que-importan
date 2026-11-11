import chainlit as cl
from src.agent import ConversationalAgent
from src.config import LOGFORMAT, LOGFILE
import logging

# Crear logger para la interfaz de usuario
logging.basicConfig(filename=LOGFILE, level=logging.INFO, format=LOGFORMAT)
logger = logging.getLogger("App")

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
        raise RuntimeError("No se pudo inicializar la sesión del agente.")
    
    # atrapar errores en el agente y responder con un mensaje genérico
    try:
        response = await agent.respond(msg.content)
    except Exception as e:
        logger.error(f"Error en la consulta: {e}")
        raise RuntimeError(f"Error en la consulta: {e}")
    await cl.Message(content=response).send()
