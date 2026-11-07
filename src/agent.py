import os
import logging
import chainlit as cl
from openai import OpenAI, safety
from .config import AgentSettings, LOGFILE, LOGFORMAT
from .metrics import Metrics
from .rag import EvidenceStore
from .safety import safety_from_llm, safety_from_re, assess_safety
from .tools import analizar_situacion, consultar_evidencia
from time import perf_counter
from langchain_core.runnables import RunnableParallel, RunnableLambda, RunnableBranch

# Crear logger para el agente conversacional
logging.basicConfig(filename=LOGFILE, level=logging.INFO, format=LOGFORMAT)
logger = logging.getLogger("Agent")

class ConversationalAgent:
    def __init__(self, settings: AgentSettings | None = None) -> None:
        self.settings = settings or AgentSettings.load()
        self.history: list[dict] = []  # Historial en formato de mensajes de OpenAI
        self.metrics = Metrics()
        
        # Inicializar el cliente de OpenAI
        self.client = OpenAI(api_key=self.settings.api_key)
        #self.client = OpenAI(base_url="https://ollama.com/v1", api_key=self.settings.api_key)

    async def respond(self, message: str) -> str:

        def _safe_response(safety) -> str:
            response = safety.response or "Buscá ayuda humana inmediata y comunicate con emergencias."
            # Guardar en historial
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": response})
            self.metrics.observe(started_at, urgent=True, evidence_hits=0)
            logger.warning(f"Mensaje marcado como urgente: {message} | Respuesta: {response} | Razón: {safety.reason}")
            logger.info(f"Metricas actualizadas: {self.metrics}")
            return response

        logger.info(f"Mensaje recibido: {message}")
        started_at = perf_counter()
        
        # 1. Validación de seguridad en paralelo: aplica un guardrail rapido y local basado
        # en regex y una segunda capa basado en el LLM para mayor análisis
        safety = safety_from_re(message)
        if safety.level == "urgent":
            _safe_response(safety)

        # 2. Realizar analisis de NLP y evaluar seguridad en contexto
        analysis = await analizar_situacion(message)
        logger.info(f"Análisis de la situación: {analysis}")
        safety = safety_from_llm(analysis=analysis)
        if safety.level == "urgent":
            _safe_response(safety)

        # 3. Ejecutar herramientas
        evidence = consultar_evidencia(message, analysis.get("topic"))
        logger.info(f"Evidencia encontrada: {evidence}")

        # 3. Construir el System Prompt ético y guía para el modelo
        system_prompt = f"""
        Eres "Voces que Importan", un agente conversacional de apoyo y orientación para estudiantes y docentes universitarios.
        El análisis preliminar detectó el eje temático: **{analysis.get("topic", "No especificado")}** con intención de **{analysis.get("intent", "No especificada")}**.

        REGLAS DE ORO ESTRICTAS QUE DEBES CUMPLIR:
        1. NUNCA diagnostiques condiciones médicas, psicológicas o psiquiátricas.
        2. Valida la emoción del usuario con absoluta empatía y tono humano.
        3. Si utilizas información de la evidencia provista a continuación, DEBES citar la fuente explícitamente (ej. [UNESCO-IESALC]). No inventes datos ni estadísticas.
        4. Orienta de forma constructiva hacia canales institucionales o pasos seguros.

        {evidence}
        """

        # 5. Armar la estructura de mensajes para la API (Sistema + Historial + Mensaje actual)
        messages = [{"role": "system", "content": system_prompt}]
        
        # Agregar los últimos turnos del historial para mantener memoria corta conversacional
        messages.extend(self.history[-6:])  # Mantiene los últimos 3 pares de mensajes
        
        # Agregar el mensaje actual del usuario
        messages.append({"role": "user", "content": message})

        try:
            # 6. Llamada oficial a la API de OpenAI
            completion = self.client.chat.completions.create(
                model=self.settings.model,  
                messages=messages,
                temperature=0.3      # Temperatura baja para mantener respuestas controladas y basadas en hechos
            )
            response = completion.choices[0].message.content

        except Exception as e:
            response = f"Disculpáme, ocurrió un error al comunicarme con el servicio de IA. Por favor, intentá nuevamente en unos instantes."
            logger.error(f"Error en la consulta: {e}")

        # 7. Actualizar historial de la sesión y métricas
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": response})
        self.metrics.observe(started_at, urgent=False, evidence_hits=len(evidence))
        logger.info(f"Respuesta generada: {response}")
        logger.info(f"Metricas actualizadas: {self.metrics}")

        return response