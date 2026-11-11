import chainlit as cl
from src.agent import ConversationalAgent


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
        raise RuntimeError("No se pudo inicializar la sesión del agente.")
    await cl.Message(content=await agent.respond(msg.content)).send()
