"""Flujo temporal para registrar hechos y preparar un resumen institucional."""

from dataclasses import dataclass, field
from io import BytesIO
from xml.sax.saxutils import escape

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


class JournalEntry(BaseModel):
    date: str = Field(..., description="Fecha aproximada del hecho.")
    location: str = Field(..., description="Espacio físico o virtual donde ocurrió.")
    description: str = Field(
        ...,
        description="Descripción estrictamente fáctica y verificable.",
    )
    participants: list[str] = Field(..., description="Personas presentes, roles o testigos.")
    observations: str = Field(..., description="Observaciones adicionales.")
    interpretations: str = Field(
        ...,
        description="Interpretaciones, sensaciones o impacto personal, separados de los hechos.",
    )


SYSTEM_PROMPT = """Ayudá a preparar un registro neutral para una oficina de convivencia.
Usá exclusivamente la información proporcionada. Separá estrictamente:
- hechos observables: conductas, acciones y citas textuales verificables;
- interpretaciones e impacto: sensaciones, conclusiones o intenciones atribuidas.
No determines responsabilidades, no diagnostiques y no des asesoramiento legal.
Si falta información, indicá "No informado" en vez de inventarla.
"""

JOURNAL_QUESTIONS = (
    ("date", "¿Cuándo ocurrió? Podés indicar una fecha aproximada o un período."),
    ("location", "¿Dónde ocurrió? Indicá el espacio físico o virtual."),
    ("description", "¿Qué pasó? Describí conductas, acciones o frases concretas."),
    ("participants", "¿Quiénes estaban presentes? Incluí roles o testigos si los conocés."),
    ("observations", "¿Hay alguna observación adicional que quieras registrar?"),
)


@dataclass
class JournalSession:
    answers: dict[str, str] = field(default_factory=dict)
    question_index: int = 0
    entry: JournalEntry | None = None
    reviewing: bool = False

    @property
    def complete(self) -> bool:
        return self.question_index >= len(JOURNAL_QUESTIONS)

    @property
    def current_question(self) -> str:
        return JOURNAL_QUESTIONS[self.question_index][1]

    def record(self, answer: str) -> None:
        field_name, _ = JOURNAL_QUESTIONS[self.question_index]
        self.answers[field_name] = answer.strip() or "No informado"
        self.question_index += 1

    def correction(self, message: str) -> bool:
        if ":" not in message:
            return False
        field_name, value = message.split(":", 1)
        aliases = {"fecha": "date", "lugar": "location", "qué pasó": "description",
                   "que paso": "description", "quiénes": "participants",
                   "quienes": "participants", "observaciones": "observations"}
        field_name = aliases.get(field_name.strip().lower(), field_name.strip().lower())
        if field_name not in {name for name, _ in JOURNAL_QUESTIONS}:
            return False
        self.answers[field_name] = value.strip() or "No informado"
        return True


async def generate_journal(settings, answers: dict[str, str]) -> JournalEntry:
    llm = ChatOpenAI(
        model=settings.model,
        api_key=settings.api_key,
        temperature=0.2,
    ).with_structured_output(JournalEntry, method="json_schema")
    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("human", "Registro aportado:\n{answers}")]
    )
    return await (prompt | llm).ainvoke({"answers": "\n".join(
        f"{field}: {value}" for field, value in answers.items()
    )})


def format_journal(entry: JournalEntry) -> str:
    participants = ", ".join(entry.participants) or "No informado"
    return (
        "### Resumen para revisión\n\n"
        f"**Fecha:** {entry.date}\n\n"
        f"**Lugar:** {entry.location}\n\n"
        f"**Personas presentes:** {participants}\n\n"
        f"**Hechos observables:**\n{entry.description}\n\n"
        f"**Observaciones:**\n{entry.observations}\n\n"
        f"**Interpretaciones e impacto:**\n{entry.interpretations}\n\n"
        "Revisá el contenido. Escribí `confirmar` para descargarlo o "
        "`campo: corrección` para corregir un dato."
    )


def journal_pdf(entry: JournalEntry) -> bytes:
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "JournalBody",
        parent=styles["BodyText"],
        alignment=TA_LEFT,
        leading=15,
        spaceAfter=8,
    )
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Bitácora de hechos",
    )
    participants = ", ".join(entry.participants) or "No informado"
    sections = [
        ("Bitácora de hechos", "Registro preparado para revisión por la persona usuaria."),
        ("Fecha", entry.date),
        ("Lugar", entry.location),
        ("Personas presentes", participants),
        ("Hechos observables", entry.description),
        ("Observaciones", entry.observations),
        ("Interpretaciones e impacto", entry.interpretations),
    ]
    story = []
    for title, content in sections:
        story.append(Paragraph(f"<b>{escape(title)}</b>", body))
        story.append(Paragraph(escape(content).replace("\n", "<br/>"), body))
        story.append(Spacer(1, 4))
    document.build(story)
    return buffer.getvalue()
