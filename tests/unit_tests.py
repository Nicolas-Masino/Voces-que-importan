import pytest

from src.config import AgentSettings, RAGSettings
from src.empathy import EmpathyCriterion, EmpathyEvaluation, EmpathyLab
from src.metrics import Metrics
from src.nlp import Analysis
from src.rag import flag, formatear_cita, slug
from src.resources import buscar_recursos
from src.safety import assess_safety, safety_from_llm, safety_from_re
from src.tools import consultar_evidencia, orientar_recursos

@pytest.mark.parametrize("texto", [
    "Un compañero me dijo que no quiere seguir viviendo. ¿Qué hago?",
    "a veces pienso en suicidarme",
    "quiero morirme",
    "no quiero seguir viviendo así",
    "Mi pareja me va a matar",
    "NO QUIERO SEGUIR VIVIENDO",            # mayúsculas
])
def test_danger_detected(texto):
    urgent = safety_from_re(texto)
    assert urgent.level == "urgent"
    assert "911" in urgent.response
 
 
@pytest.mark.parametrize("texto", [
    "¿Cuántos docentes se suicidan por año en el mundo?",   # pregunta estadística
    "Me muero de risa con mis compañeros",
    "Doy clases hace diez años y siento que nadie valora lo que hago.",
    "En mi grupo se burlan de mi acento porque soy venezolano.",
    "Necesito orientación sobre un conflicto"
])
def test_safe_to_ignore(texto):
    assert safety_from_re(texto).level == "normal"

def test_safety_detects_urgent_and_normal_messages():
    urgent = safety_from_re("Mi amiga piensa en suicidarse")
    normal = safety_from_re("Necesito orientación sobre un conflicto")

    assert urgent.level == "urgent"
    assert "911" in urgent.response
    assert normal.level == "normal"
    assert assess_safety(normal, safety_from_llm({"intent": "pedir consejo"})).level == "normal"


def test_safety_llm_result_is_prioritized_when_regex_is_normal():
    urgent = safety_from_llm({"intent": "emergencia"})
    normal = safety_from_re("Necesito orientación sobre un conflicto")

    assert "no dejes sola" in urgent.response.lower()
    assert assess_safety(normal, safety_from_llm({"intent": "pedir consejo"})).level == "normal"


def test_metrics_track_messages_and_average_latency():
    metrics = Metrics()
    metrics.observe(0, urgent=True, evidence_hits=2)
    metrics.observe(0, urgent=False, evidence_hits=1)

    assert metrics.messages == 2
    assert metrics.urgent_messages == 1
    assert metrics.evidence_hits == 3
    assert metrics.average_latency_ms > 0


def test_configuration_loads_topics_and_rag_paths():
    agent = AgentSettings.load()
    rag = RAGSettings.load()

    assert agent.provider
    assert rag.corpus_dir.name == "sources"
    assert rag.threshold == 0.3


def test_analysis_schema_rejects_unknown_topics():
    analysis = Analysis(
        emotion="tristeza",
        sentiment="negativo",
        intent="desahogarse",
        scope=None,
        topic="bienestar docente",
        confidence="alta",
    )

    assert analysis.topic == "bienestar docente"
    with pytest.raises(ValueError):
        Analysis(
            emotion="otro",
            sentiment="neutro",
            intent="desahogarse",
            scope=None,
            topic="tema inexistente",
            confidence="baja",
        )


def test_rag_helpers_normalize_accents_and_format_citations():
    assert slug("Xenofobia y discriminación") == "xenofobia_y_discriminacion"
    assert flag("salud mental") == "t_salud_mental"
    assert formatear_cita({"fuente": "OMS", "anio": 2023, "pagina": 4}) == "OMS (2023), p. 4"


def test_resources_filter_by_topic_and_scope():
    result = buscar_recursos("convivencia universitaria", "institucional")

    assert result["flag_topico"] is True
    assert result["flag_ambito"] is True
    assert result["resources"]
    assert all(resource.scope == "institucional" for resource in result["resources"])


def test_tools_format_evidence_and_resources(monkeypatch):
    monkeypatch.setattr(
        "src.tools.buscar_evidencia",
        lambda *_args: {
            "results": [
                {
                    "texto": "Un fragmento verificable.",
                    "fuente": "Fuente de prueba",
                    "anio": 2024,
                    "pagina": 2,
                    "pais": "Argentina",
                    "relevancia": 0.9,
                }
            ]
        },
    )
    evidence = consultar_evidencia.invoke({"consulta": "conflicto"})
    assert "Fuente de prueba (2024), p. 2" in evidence["content"]
    assert "Un fragmento verificable." in evidence["content"]
    assert len(evidence["results"]) == 1

    resources = orientar_recursos.invoke(
        {"topico": "convivencia universitaria", "ambito": "institucional"}
    )
    assert "Recursos verificados" in resources.get("content", "")
    assert "Universidad Católica Argentina" in resources.get("content", "")


def test_empathy_evaluation_requires_scores_between_one_and_five():
    criterion = EmpathyCriterion(score=4, feedback="Reflejó la emoción.")
    evaluation = EmpathyEvaluation(
        validation=criterion,
        reflection=criterion,
        open_questions=criterion,
        non_judgment=criterion,
        guidance=criterion,
        strengths=["Escuchó sin interrumpir."],
        opportunities=["Hacer una pregunta abierta."],
        summary="Práctica útil.",
    )

    assert evaluation.validation.score == 4
    with pytest.raises(ValueError):
        EmpathyCriterion(score=6, feedback="Puntaje inválido.")


def test_empathy_lab_begin_resets_previous_turns():
    lab = EmpathyLab(AgentSettings(api_key=""))
    lab.begin("Un conflicto con un colega")
    lab.turns.append(("Practicante", "Te entiendo."))
    lab.begin("Una conversación con un estudiante")

    assert lab.active is True
    assert lab.scenario == "Una conversación con un estudiante"
    assert lab.turns == []