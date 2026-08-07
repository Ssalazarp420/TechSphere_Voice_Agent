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
    from backend.rag.store import CorpusVectorStore

    store = CorpusVectorStore(root_dir=root_dir)
    admin_service = AdminDocumentService(root_dir=root_dir)
    call_service = CallSessionService(root_dir=root_dir)
    sessions = call_service.list_sessions()
    assistant_turns = [turn for session in sessions for turn in session.get("turns", []) if turn.get("role") == "assistant"]
    latencies = [turn.get("latency_ms") for turn in assistant_turns if turn.get("latency_ms") is not None]

    payload = {
        "vector_index": store.status(root_dir / "dataset" / "textos"),
        "admin_documents": len(admin_service.list_documents()),
        "call_sessions": {
            "total": len(sessions),
            "active": len([session for session in sessions if session.get("status") == "active"]),
            "closed": len([session for session in sessions if session.get("status") == "closed"]),
            "assistant_turns": len(assistant_turns),
            "remote_model_turns": len([turn for turn in assistant_turns if turn.get("used_remote_model")]),
            "avg_turn_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
            "max_turn_latency_ms": round(max(latencies), 2) if latencies else None,
        },
    }

    output_path = root_dir / "backend" / "data" / "metrics_snapshot.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Metrics snapshot written to: {output_path}")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
