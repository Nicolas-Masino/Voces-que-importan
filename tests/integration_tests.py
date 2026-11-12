import asyncio
from types import SimpleNamespace

from src.agent import ConversationalAgent
from src.config import AgentSettings


def test_agent_short_circuits_urgent_messages_without_calling_the_llm(monkeypatch):
    agent = ConversationalAgent(AgentSettings(api_key="", context_window=2))

    async def fail_analysis(_message):
        raise AssertionError("NLP must not run after an urgent regex match")

    monkeypatch.setattr("src.agent.analizar_situacion", fail_analysis)
    response = asyncio.run(agent.respond("No quiero seguir viviendo"))

    assert "911" in response
    assert len(agent.history) == 2
    assert agent.metrics.messages == 1
    assert agent.metrics.urgent_messages == 1


def test_agent_orchestrates_analysis_tools_and_model(monkeypatch):
    agent = ConversationalAgent(AgentSettings(api_key="", context_window=2))
    analysis = {
        "emotion": "tristeza",
        "sentiment": "negativo",
        "intent": "pedir consejo",
        "scope": "institucional",
        "topic": "bienestar docente",
        "confidence": "alta",
    }
    calls = {}

    async def fake_analysis(_message):
        calls["analysis"] = True
        return analysis

    async def fake_evidence(values):
        calls["topic"] = values["topico"]
        return {
            "results": [{"texto": "Evidencia de prueba"}],
            "content": "Evidencia de prueba",
        }

    class FakePrompt:
        def __or__(self, _llm):
            return self

        async def ainvoke(self, values):
            calls["prompt"] = values
            return SimpleNamespace(content="Respuesta integrada")

    monkeypatch.setattr("src.agent.analizar_situacion", SimpleNamespace(ainvoke=fake_analysis))
    monkeypatch.setattr("src.agent.consultar_evidencia", SimpleNamespace(ainvoke=fake_evidence))
    monkeypatch.setattr(
        "src.agent.ChatPromptTemplate.from_messages",
        lambda _messages: FakePrompt(),
    )
    monkeypatch.setattr("src.agent.ChatOpenAI", lambda **_kwargs: object())

    response = asyncio.run(agent.respond("Me siento agotado y necesito consejo"))

    assert response == "Respuesta integrada"
    assert calls["analysis"] is True
    assert calls["topic"] == "bienestar docente"
    assert "Evidencia de prueba" in calls["prompt"]["system"]
    assert len(agent.history) == 2
    assert agent.metrics.messages == 1
    assert agent.metrics.evidence_hits == 1


def test_agent_reports_analysis_and_tool_progress(monkeypatch):
    agent = ConversationalAgent(AgentSettings(api_key="", context_window=2))
    events = []

    async def fake_analysis(_message):
        return {
            "emotion": "tristeza",
            "sentiment": "negativo",
            "intent": "pedir consejo",
            "scope": "institucional",
            "topic": "bienestar docente",
            "confidence": "alta",
        }

    async def fake_progress(stage, status):
        events.append((stage, status))

    class FakePrompt:
        def __or__(self, _llm):
            return self

        async def ainvoke(self, _values):
            return SimpleNamespace(content="Respuesta")

    async def fake_evidence(_values):
        return {"results": [], "content": "Sin evidencia"}

    monkeypatch.setattr("src.agent.analizar_situacion", SimpleNamespace(ainvoke=fake_analysis))
    monkeypatch.setattr("src.agent.consultar_evidencia", SimpleNamespace(ainvoke=fake_evidence))
    monkeypatch.setattr("src.agent.ChatPromptTemplate.from_messages", lambda _messages: FakePrompt())
    monkeypatch.setattr("src.agent.ChatOpenAI", lambda **_kwargs: object())

    asyncio.run(agent.respond("Necesito consejo", progress=fake_progress))

    assert events == [
        ("analysis", "started"),
        ("analysis", "completed"),
        ("evidence", "started"),
        ("evidence", "completed"),
    ]