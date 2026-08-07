from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from backend.decision.rules import classify_report
from backend.llm.service import GeminiResponder
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
        self.llm = GeminiResponder()

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
        remote_prompt = self._build_prompt(user_text=user_text, decision=decision, references=references)
        try:
            llm_response = self.llm.generate(remote_prompt)
            return llm_response.text
        except Exception:
            pass

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

    def _build_prompt(
        self,
        user_text: str,
        decision: dict[str, object],
        references: list[dict[str, object]],
    ) -> str:
        top_references = []
        for reference in references[:3]:
            metadata = reference.get("metadata", {}) if isinstance(reference, dict) else {}
            top_references.append(
                {
                    "filename": metadata.get("filename", "fuente"),
                    "category": metadata.get("category", "general"),
                    "excerpt": str(reference.get("text", ""))[:900],
                }
            )

        references_text = "\n".join(
            f"- {item['filename']} [{item['category']}]: {item['excerpt']}" for item in top_references
        ) or "- Sin referencias recuperadas"

        return (
            "Eres un agente clínico de seguimiento postoperatorio para pacientes colombianos. "
            "Responde en español, con tono breve, empático y claro. No inventes medicamentos, dosis ni diagnósticos. "
            "Usa solo el contexto recuperado y la decisión local. Si hay bandera roja, indica escalamiento inmediato. "
            "Si la evidencia no es suficiente, dilo y pide datos concretos. "
            "Mantén la respuesta en 2 o 3 frases, y termina con una pregunta corta para seguir la evaluación.\n\n"
            f"DECISIÓN LOCAL:\n{decision}\n\n"
            f"TURNO DEL PACIENTE:\n{user_text}\n\n"
            f"REFERENCIAS RECUPERADAS:\n{references_text}\n"
        )
