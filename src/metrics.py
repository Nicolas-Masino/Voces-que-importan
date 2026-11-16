from dataclasses import dataclass, field
from time import perf_counter


@dataclass
class Metrics:
    messages: int = 0
    urgent_messages: int = 0
    evidence_hits: int = 0
    total_latency_ms: float = 0.0
    nlp_latency_ms: float = 0.0
    rag_latency_ms: float = 0.0
    resources_latency_ms: float = 0.0
    llm_latency_ms: float = 0.0
    trace_state: dict[str, bool] = field(
        default_factory=lambda: {
            "rag": False,
            "resources": False,
            "nlp": False,
            "llm": False,
        }
    )

    def observe(self, started_at: float, *, urgent: bool, evidence_hits: int) -> None:
        self.messages += 1
        self.urgent_messages += int(urgent)
        self.evidence_hits += evidence_hits
        self.total_latency_ms += (perf_counter() - started_at) * 1000

    def observe_tool(self, started_at: float, tool_name: str) -> None:
        latency_ms = (perf_counter() - started_at) * 1000
        if tool_name == "nlp":
            self.nlp_latency_ms += latency_ms
        elif tool_name == "rag":
            self.rag_latency_ms += latency_ms
        elif tool_name == "resources":
            self.resources_latency_ms += latency_ms
        elif tool_name == "llm":
            self.llm_latency_ms += latency_ms

    def mark_trace(self, tool: str) -> None:
        if tool in self.trace_state:
            self.trace_state[tool] = True


    @property
    def average_latency_ms(self) -> float:
        return self.total_latency_ms / self.messages if self.messages else 0.0
