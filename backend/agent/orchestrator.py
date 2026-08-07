from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from backend.decision.rules import classify_report
from backend.rag.store import CorpusVectorStore


@dataclass(frozen=True)
class CallTurnResult:
    user_text: str
    assistant_text: str
    decision: dict[str, object]
    references: list[dict[str, object]]
    escalation_required: bool


class CallOrchestrator:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.store = CorpusVectorStore(root_dir=root_dir)

    def start_call(self) -> dict[str, object]:
        return {
            "assistant_text": (
                "Hola, soy el agente de seguimiento postoperatorio. "
                "Voy a hacerte preguntas cortas para revisar cómo vas y decidir si necesitas escalamiento."
            ),
            "expected_next": "describe_symptoms",
            "escalation_required": False,
        }

    def respond(self, user_text: str, limit: int = 3) -> dict[str, object]:
        decision = classify_report(user_text)
        references = self.store.search(user_text, limit=limit)

        assistant_text = self._compose_response(user_text=user_text, decision=decision, references=references)

        return asdict(
            CallTurnResult(
                user_text=user_text,
                assistant_text=assistant_text,
                decision=decision,
                references=references,
                escalation_required=decision["label"] == "rojo",
            )
        )

    def _compose_response(
        self,
        user_text: str,
        decision: dict[str, object],
        references: list[dict[str, object]],
    ) -> str:
        label = str(decision["label"])
        if label == "rojo":
            opening = "Veo signos de alarma y voy a escalar esto de inmediato."
            guidance = "Por favor busca atención humana ahora mismo o contacta al equipo clínico de inmediato."
        elif label == "amarillo":
            opening = "Hay síntomas que requieren seguimiento estrecho."
            guidance = "Voy a hacer una pregunta más para precisar si esto necesita escalamiento."
        else:
            opening = "No veo signos de alarma en lo que me cuentas."
            guidance = "Sigue las indicaciones de recuperación y avísame si aparece un síntoma nuevo o peor."

        if references:
            source_names = ", ".join(sorted({str(item["metadata"].get("filename", "fuente")) for item in references[:2]}))
            source_phrase = f"Estoy basando la orientación en: {source_names}."
        else:
            source_phrase = "No encontré una fuente suficientemente específica en el corpus para este punto."

        return " ".join(
            [
                opening,
                guidance,
                source_phrase,
                "Si quieres, dime desde cuándo empezó, qué tan fuerte es y si tienes fiebre o cambios en la herida.",
            ]
        )
