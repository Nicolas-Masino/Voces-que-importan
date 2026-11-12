import asyncio
from types import SimpleNamespace

from src.agent import ConversationalAgent
from src.config import AgentSettings
from src.empathy import EmpathyCriterion, EmpathyEvaluation, EmpathyLab
import app


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
    assert len(agent.last_sources) == 1
    assert "Evidencia de prueba" in agent.last_sources[0]
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


def test_empathy_lab_simulates_turns_and_evaluates(monkeypatch):
    lab = EmpathyLab(AgentSettings(api_key="", model="test"))
    lab.begin("Una conversación sobre una situación injusta")

    class FakeChain:
        async def ainvoke(self, _values):
            return SimpleNamespace(content="Me cuesta hablar de esto.")

    class FakeStructuredChain:
        async def ainvoke(self, _values):
            return SimpleNamespace(
                validation=SimpleNamespace(score=4, feedback="Bien"),
                reflection=SimpleNamespace(score=3, feedback="Puede parafrasear más"),
                open_questions=SimpleNamespace(score=4, feedback="Buena pregunta"),
                non_judgment=SimpleNamespace(score=5, feedback="No juzga"),
                guidance=SimpleNamespace(score=3, feedback="Orientación breve"),
                strengths=["Validó la emoción."],
                opportunities=["Profundizar la paráfrasis."],
                summary="Buen comienzo.",
            )

    class FakePrompt:
        def __or__(self, llm):
            return FakeChain() if isinstance(llm, FakeLLM) else FakeStructuredChain()

    class FakeLLM:
        def with_structured_output(self, *_args, **_kwargs):
            return object()

    monkeypatch.setattr("src.empathy.ChatOpenAI", lambda **_kwargs: FakeLLM())
    monkeypatch.setattr(
        "src.empathy.ChatPromptTemplate.from_messages",
        lambda _messages: FakePrompt(),
    )

    response = asyncio.run(lab.respond("Entiendo que esto te haya dolido."))
    evaluation = asyncio.run(lab.evaluate())

    assert response == "Me cuesta hablar de esto."
    assert len(lab.turns) == 2
    assert evaluation.validation.score == 4


def test_empathy_lab_feeds_previous_evaluation_into_next_simulation_turn(monkeypatch):
    lab = EmpathyLab(AgentSettings(api_key="", model="test"))
    lab.begin("Una conversación sobre una situación injusta")
    prompts = []
    criterion = EmpathyCriterion(score=2, feedback="Faltó reflejar la emoción.")
    evaluation = EmpathyEvaluation(
        validation=criterion,
        reflection=criterion,
        open_questions=criterion,
        non_judgment=criterion,
        guidance=criterion,
        strengths=[],
        opportunities=["Reflejar mejor lo que la otra persona siente."],
        summary="Hay espacio para practicar.",
    )

    class FakeChain:
        async def ainvoke(self, values):
            prompts.append(values)
            return SimpleNamespace(content="Me cierro un poco.")

    class FakeStructuredChain:
        async def ainvoke(self, _values):
            return evaluation

    class FakePrompt:
        def __or__(self, llm):
            return FakeChain() if isinstance(llm, FakeLLM) else FakeStructuredChain()

    class FakeLLM:
        def with_structured_output(self, *_args, **_kwargs):
            return object()

    monkeypatch.setattr("src.empathy.ChatOpenAI", lambda **_kwargs: FakeLLM())
    monkeypatch.setattr(
        "src.empathy.ChatPromptTemplate.from_messages",
        lambda _messages: FakePrompt(),
    )

    asyncio.run(lab.respond("Entiendo que esto te haya dolido."))
    asyncio.run(lab.respond("¿Querés contarme un poco más?"))

    assert prompts[0]["level"] == "cautelosa"
    assert prompts[0]["behavior"] == "Te animás a contar algo más, pero medís cada palabra."
    assert prompts[1]["level"] == "cerrada"
    assert prompts[1]["behavior"] == "Respondés poco, con cautela; todavía no confiás."


class FakeSession:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value


class FakeSentMessage:
    sent = []

    def __init__(self, content):
        self.content = content

    async def send(self):
        self.__class__.sent.append(self)


class FakeErrorMessage(FakeSentMessage):
    pass


class FakeIncomingMessage:
    def __init__(self, content, command=None):
        self.content = content
        self.command = command


def install_fake_chainlit(monkeypatch):
    session = FakeSession()
    FakeSentMessage.sent = []
    FakeErrorMessage.sent = []
    monkeypatch.setattr(app.cl, "user_session", session)
    monkeypatch.setattr(app.cl, "Message", FakeSentMessage)
    monkeypatch.setattr(app.cl, "ErrorMessage", FakeErrorMessage)
    class FakeEmitter:
        async def set_commands(self, _commands):
            return None

    monkeypatch.setattr(app.cl, "context", SimpleNamespace(emitter=FakeEmitter()))
    return session


def test_chainlit_start_initializes_session_and_sends_greeting(monkeypatch):
    session = install_fake_chainlit(monkeypatch)

    asyncio.run(app.start())

    assert isinstance(session.get("agent"), ConversationalAgent)
    assert "Hola" in FakeSentMessage.sent[0].content


def test_chainlit_normal_message_sends_agent_response(monkeypatch):
    session = install_fake_chainlit(monkeypatch)
    agent = ConversationalAgent(AgentSettings(api_key=""))
    calls = []

    async def fake_respond(message, progress=None):
        calls.append(message)
        return "Respuesta simulada"

    monkeypatch.setattr(agent, "respond", fake_respond)
    session.set("agent", agent)

    asyncio.run(app.main(FakeIncomingMessage("Necesito orientación")))

    assert calls == ["Necesito orientación"]
    assert FakeSentMessage.sent[-1].content == "Respuesta simulada"


def test_chainlit_shows_sources_in_side_panel(monkeypatch):
    session = install_fake_chainlit(monkeypatch)
    agent = ConversationalAgent(AgentSettings(api_key=""))
    agent.last_sources = ["Fuente exacta de prueba."]

    async def fake_respond(_message, progress=None):
        return "Respuesta con respaldo"

    monkeypatch.setattr(agent, "respond", fake_respond)
    session.set("agent", agent)

    asyncio.run(app.main(FakeIncomingMessage("Necesito orientación")))

    sources_message = FakeSentMessage.sent[-1]
    assert sources_message.content.startswith("### Fuentes")
    assert "Fuente exacta de prueba." in sources_message.content


def test_chainlit_hides_sources_panel_when_no_sources(monkeypatch):
    session = install_fake_chainlit(monkeypatch)
    agent = ConversationalAgent(AgentSettings(api_key=""))

    async def fake_respond(_message, progress=None):
        return "Respuesta sin fuentes"

    monkeypatch.setattr(agent, "respond", fake_respond)
    session.set("agent", agent)

    asyncio.run(app.main(FakeIncomingMessage("Necesito orientación")))

    assert all(
        not message.content.startswith("### Fuentes")
        for message in FakeSentMessage.sent
    )


def test_chainlit_emergency_message_uses_agent_safety_response(monkeypatch):
    session = install_fake_chainlit(monkeypatch)
    agent = ConversationalAgent(AgentSettings(api_key=""))

    async def fake_respond(_message, progress=None):
        return "Buscá ayuda humana inmediata."

    monkeypatch.setattr(agent, "respond", fake_respond)
    session.set("agent", agent)

    asyncio.run(app.main(FakeIncomingMessage("No quiero seguir viviendo")))

    assert "ayuda humana inmediata" in FakeSentMessage.sent[-1].content
    assert FakeErrorMessage.sent == []


def test_chainlit_empathy_commands_manage_session(monkeypatch):
    session = install_fake_chainlit(monkeypatch)

    asyncio.run(app.main(FakeIncomingMessage("", command="Empatía")))
    lab = session.get("empathy_lab")

    assert isinstance(lab, EmpathyLab)
    assert "Describí una conversación" in FakeSentMessage.sent[-1].content

    asyncio.run(app.main(FakeIncomingMessage("Un conflicto con un colega")))

    assert lab.scenario == "Un conflicto con un colega"
    assert "Listo" in FakeSentMessage.sent[-1].content


def test_chainlit_evaluate_empathy_command_sends_full_evaluation(monkeypatch):
    session = install_fake_chainlit(monkeypatch)
    lab = EmpathyLab(AgentSettings(api_key=""))
    lab.begin("Un conflicto con un colega")
    criterion = EmpathyCriterion(score=4, feedback="Buena validación.")
    evaluation = EmpathyEvaluation(
        validation=criterion,
        reflection=criterion,
        open_questions=criterion,
        non_judgment=criterion,
        guidance=criterion,
        strengths=["Escuchó con calidez."],
        opportunities=["Hacer una pregunta abierta."],
        summary="Práctica sólida.",
    )

    async def fake_evaluate():
        return evaluation

    lab.evaluate = fake_evaluate
    session.set("empathy_lab", lab)

    asyncio.run(app.main(FakeIncomingMessage("", command="Evaluar empatía")))

    output = FakeSentMessage.sent[-1].content
    assert "Validación emocional" in output
    assert "Escuchó con calidez." in output
    assert "Práctica sólida." in output


def test_chainlit_agent_errors_are_reported(monkeypatch):
    session = install_fake_chainlit(monkeypatch)
    agent = ConversationalAgent(AgentSettings(api_key=""))

    async def fail_respond(_message, progress=None):
        raise RuntimeError("fallo controlado")

    monkeypatch.setattr(agent, "respond", fail_respond)
    session.set("agent", agent)

    try:
        asyncio.run(app.main(FakeIncomingMessage("Mensaje")))
    except RuntimeError as error:
        assert str(error) == "fallo controlado"
    else:
        raise AssertionError("El handler debe propagar el error después de notificarlo")

    assert len(FakeErrorMessage.sent) == 1
    assert "fallo controlado" in FakeErrorMessage.sent[0].content