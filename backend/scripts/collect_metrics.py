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

    # Misma función que expone GET /metrics — un snapshot persistido no debe
    # poder divergir del endpoint en vivo.
    payload = {
        "vector_index": store.status(root_dir / "dataset" / "textos"),
        "admin_documents": len(admin_service.list_documents()),
        "call_sessions": call_service.global_metrics(),
    }

    output_path = root_dir / "backend" / "data" / "metrics_snapshot.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Metrics snapshot written to: {output_path}")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
