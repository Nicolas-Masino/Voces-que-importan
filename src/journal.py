"""Flujo temporal para registrar hechos y preparar un resumen institucional."""

from dataclasses import dataclass, field
from datetime import date

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

import io
from docx import Document
from docx.shared import Pt, RGBColor


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

def journal_docx(entry: JournalEntry) -> bytes:
    doc = Document()
    participants = ", ".join(entry.participants) or "No informado"

    # Título principal
    doc.add_heading("Bitácora de hechos", level=0)

    # Subtítulo en cursiva
    p_fecha = doc.add_paragraph()
    run_fecha = p_fecha.add_run(
        f"Registro personal elaborado el {date.today().strftime('%d/%m/%Y')} a partir del relato de la persona."
    )
    run_fecha.italic = True

    # Sección 1
    doc.add_heading("1. Qué ocurrió (según relata la persona)", level=2)
    doc.add_paragraph(entry.description or "No indicado")

    # Sección 2 (con viñetas y negritas)
    doc.add_heading("2. Cuándo y dónde", level=2)
    p_cuando = doc.add_paragraph(style="List Bullet")
    p_cuando.add_run("Cuándo: ").bold = True
    p_cuando.add_run(entry.date or "No indicado")

    p_donde = doc.add_paragraph(style="List Bullet")
    p_donde.add_run("Dónde / medio: ").bold = True
    p_donde.add_run(entry.location or "No indicado")

    # Sección 3
    doc.add_heading("3. Personas", level=2)
    p_pers = doc.add_paragraph()
    p_pers.add_run("Señaladas por quien relata:\n").bold = True
    p_pers.add_run(participants)

    # Sección 4 (numerada correlativamente)
    doc.add_heading("4. Cómo lo vivió la persona", level=2)
    doc.add_paragraph(entry.interpretations or "No indicado")

    # Sección 5
    doc.add_heading("5. Observaciones adicionales", level=2)
    doc.add_paragraph(entry.observations or "No indicado")

    # Aviso legal al pie
    doc.add_paragraph("—" * 35)
    p_aviso = doc.add_paragraph()
    run_bold = p_aviso.add_run("Aviso: ")
    run_bold.bold = True
    run_texto = p_aviso.add_run(
        "este documento refleja lo que la persona relató y no fue verificado. No es una denuncia, "
        "no constituye prueba ni establece responsabilidades. Una denuncia, una investigación y un "
        "hecho probado son cosas distintas: solo el canal institucional competente puede determinarlo. "
        "Conviene guardarlo en un lugar seguro y compartirlo únicamente con quien la persona decida."
    )
    run_texto.font.size = Pt(9)
    run_texto.font.color.rgb = RGBColor(100, 100, 100)

    # Guardar en buffer de memoria RAM
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
