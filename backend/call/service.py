from __future__ import annotations

import json
import statistics
from time import perf_counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.agent.orchestrator import CallOrchestrator


@dataclass
class SessionTurn:
    role: str
    text: str
    timestamp: str
    decision: dict[str, object] | None = None
    references: list[dict[str, object]] = field(default_factory=list)
    latency_ms: float | None = None
    llm_model: str | None = None
    used_remote_model: bool | None = None


@dataclass
class CallSession:
    session_id: str
    created_at: str
    updated_at: str
    status: str
    turns: list[SessionTurn] = field(default_factory=list)


class CallSessionService:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.data_dir = root_dir / "backend" / "data"
        self.sessions_path = self.data_dir / "call_sessions.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.orchestrator = CallOrchestrator(root_dir=root_dir)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load_sessions(self) -> dict[str, object]:
        if not self.sessions_path.exists():
            return {"sessions": []}
        return json.loads(self.sessions_path.read_text(encoding="utf-8"))

    def _save_sessions(self, payload: dict[str, object]) -> None:
        self.sessions_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _serialize_session(self, session: CallSession) -> dict[str, object]:
        return {
            "session_id": session.session_id,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "status": session.status,
            "turns": [asdict(turn) for turn in session.turns],
            "summary": self._build_summary(session),
            "metrics": self._build_metrics(session),
        }

    def _build_summary(self, session: CallSession) -> dict[str, object]:
        decisions = [turn.decision or {} for turn in session.turns if turn.role == "assistant" and turn.decision]
        references = [ref for turn in session.turns for ref in turn.references]
        symptom_turns = [turn.text for turn in session.turns if turn.role == "user"]
        final_decision = decisions[-1] if decisions else {}

        return {
            "turn_count": len(session.turns),
            "symptom_turns": symptom_turns,
            "final_decision": final_decision,
            "reference_count": len(references),
            "reference_documents": sorted({str(ref.get("metadata", {}).get("filename", "")) for ref in references if ref}),
        }

    def _build_metrics(self, session: CallSession) -> dict[str, object]:
        user_turns = [turn for turn in session.turns if turn.role == "user"]
        assistant_turns = [turn for turn in session.turns if turn.role == "assistant"]
        total_references = sum(len(turn.references) for turn in assistant_turns)
        escalation = any((turn.decision or {}).get("label") == "rojo" for turn in assistant_turns)
        latencies = [turn.latency_ms for turn in assistant_turns if turn.latency_ms is not None]
        remote_turns = [turn for turn in assistant_turns if turn.used_remote_model]

        if latencies:
            avg_latency = round(sum(latencies) / len(latencies), 2)
            p95_latency = round(statistics.quantiles(latencies, n=20, method="inclusive")[-1], 2) if len(latencies) > 1 else round(latencies[0], 2)
        else:
            avg_latency = None
            p95_latency = None

        return {
            "user_turns": len(user_turns),
            "assistant_turns": len(assistant_turns),
            "total_references": total_references,
            "escalation_required": escalation,
            "avg_turn_latency_ms": avg_latency,
            "p95_turn_latency_ms": p95_latency,
            "remote_model_turns": len(remote_turns),
        }

    def create_session(self) -> dict[str, object]:
        session = CallSession(
            session_id=uuid4().hex,
            created_at=self._now(),
            updated_at=self._now(),
            status="active",
        )
        payload = self._load_sessions()
        payload["sessions"].append(self._serialize_session(session))
        self._save_sessions(payload)
        return self.get_session(session.session_id)

    def get_session(self, session_id: str) -> dict[str, object]:
        payload = self._load_sessions()
        for session in payload.get("sessions", []):
            if session.get("session_id") == session_id:
                return session
        raise ValueError("La sesión no existe")

    def list_sessions(self) -> list[dict[str, object]]:
        payload = self._load_sessions()
        return list(payload.get("sessions", []))

    def start_call(self) -> dict[str, object]:
        session = self.create_session()
        greeting = self.orchestrator.start_call()
        self.append_turn(session["session_id"], "assistant", greeting["assistant_text"], None, [])
        return {
            "session_id": session["session_id"],
            **greeting,
        }

    def append_turn(
        self,
        session_id: str,
        role: str,
        text: str,
        decision: dict[str, object] | None = None,
        references: list[dict[str, object]] | None = None,
        latency_ms: float | None = None,
        llm_model: str | None = None,
        used_remote_model: bool | None = None,
    ) -> dict[str, object]:
        payload = self._load_sessions()
        sessions = payload.get("sessions", [])
        for index, session in enumerate(sessions):
            if session.get("session_id") != session_id:
                continue

            turns = session.get("turns", [])
            turns.append(
                {
                    "role": role,
                    "text": text,
                    "timestamp": self._now(),
                    "decision": decision,
                    "references": references or [],
                    "latency_ms": latency_ms,
                    "llm_model": llm_model,
                    "used_remote_model": used_remote_model,
                }
            )
            session["turns"] = turns
            session["updated_at"] = self._now()
            payload["sessions"][index] = self._serialize_session(
                CallSession(
                    session_id=session["session_id"],
                    created_at=session["created_at"],
                    updated_at=session["updated_at"],
                    status=session.get("status", "active"),
                    turns=[SessionTurn(**turn) for turn in turns],
                )
            )
            self._save_sessions(payload)
            return payload["sessions"][index]

        raise ValueError("La sesión no existe")

    def turn(self, session_id: str, utterance: str) -> dict[str, object]:
        self.append_turn(session_id, "user", utterance)
        started_at = perf_counter()
        result = self.orchestrator.respond(utterance)
        latency_ms = round((perf_counter() - started_at) * 1000, 2)
        session = self.append_turn(
            session_id,
            "assistant",
            result["assistant_text"],
            result["decision"],
            result["references"],
            latency_ms=latency_ms,
            llm_model=result.get("llm_model"),
            used_remote_model=result.get("used_remote_model"),
        )

        return {
            "session_id": session_id,
            "user_text": utterance,
            "turn_latency_ms": latency_ms,
            **result,
            "session_summary": session["summary"],
            "session_metrics": session["metrics"],
        }

    def close_session(self, session_id: str) -> dict[str, object]:
        payload = self._load_sessions()
        for index, session in enumerate(payload.get("sessions", [])):
            if session.get("session_id") != session_id:
                continue

            turns = [SessionTurn(**turn) for turn in session.get("turns", [])]
            closed = CallSession(
                session_id=session_id,
                created_at=session["created_at"],
                updated_at=self._now(),
                status="closed",
                turns=turns,
            )
            payload["sessions"][index] = self._serialize_session(closed)
            self._save_sessions(payload)
            return payload["sessions"][index]

        raise ValueError("La sesión no existe")
