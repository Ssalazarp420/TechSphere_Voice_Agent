from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    root_dir = Path(__file__).resolve().parents[2]
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    from backend.admin.service import AdminDocumentService
    from backend.call.service import CallSessionService
    from backend.decision.rules import classify_report
    from backend.rag.store import CorpusVectorStore

    store = CorpusVectorStore(root_dir=root_dir)
    admin_service = AdminDocumentService(root_dir=root_dir)
    call_service = CallSessionService(root_dir=root_dir)

    payload = {
        "health": {
            "vector_index": store.status(root_dir / "dataset" / "textos"),
            "admin_documents": len(admin_service.list_documents()),
            "call_sessions": len(call_service.list_sessions()),
        },
        "decision_sample": classify_report("Tengo dolor 8/10, fiebre de 38.5 y la herida huele mal"),
    }

    session = call_service.start_call()
    turn = call_service.turn(session["session_id"], "Tengo dolor 8/10, fiebre de 38.5 y la herida huele mal")
    closed = call_service.close_session(session["session_id"])

    payload["call_flow"] = {
        "session_id": session["session_id"],
        "assistant_model": turn.get("llm_model"),
        "used_remote_model": turn.get("used_remote_model"),
        "turn_latency_ms": turn.get("turn_latency_ms"),
        "decision": turn.get("decision"),
        "summary": closed.get("summary"),
        "metrics": closed.get("metrics"),
    }

    output_path = root_dir / "backend" / "data" / "smoke_test_report.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Smoke test report written to: {output_path}")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
