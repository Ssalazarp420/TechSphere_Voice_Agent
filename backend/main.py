from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
import sys

load_dotenv()

app = FastAPI(title="TechSphere Voice Agent")

ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT_DIR / "frontend"
DATASET_DIR = ROOT_DIR / "dataset" / "textos"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.decision.rules import classify_report
from backend.agent.orchestrator import CallOrchestrator
from backend.admin.service import AdminDocumentService
from backend.rag.store import CorpusVectorStore


def get_vector_store() -> CorpusVectorStore:
    return CorpusVectorStore(root_dir=ROOT_DIR)


def get_admin_service() -> AdminDocumentService:
    return AdminDocumentService(root_dir=ROOT_DIR)


def get_call_orchestrator() -> CallOrchestrator:
    return CallOrchestrator(root_dir=ROOT_DIR)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, description="Texto a recuperar desde el corpus clínico")
    limit: int = Field(default=5, ge=1, le=20)


class DecisionRequest(BaseModel):
    report: str = Field(min_length=1, description="Texto libre con síntomas o hallazgos del paciente")


class CallTurnRequest(BaseModel):
    utterance: str = Field(min_length=1, description="Turno del paciente transcrito o escrito")


class CallStartResponse(BaseModel):
    assistant_text: str
    expected_next: str
    escalation_required: bool


def _files_response(payload: list[dict[str, object]]) -> dict[str, object]:
    return {
        "count": len(payload),
        "documents": payload,
    }

@app.get("/health")
def health():
    store = get_vector_store()
    return {
        "status": "ok",
        "gemini_key_loaded": bool(os.getenv("GEMINI_API_KEY")),
        "groq_key_loaded": bool(os.getenv("GROQ_API_KEY")),
        "vector_index": store.status(DATASET_DIR),
    }


@app.get("/rag/status")
def rag_status():
    store = get_vector_store()
    return store.status(DATASET_DIR)


@app.post("/rag/search")
def rag_search(payload: SearchRequest):
    store = get_vector_store()
    matches = store.search(payload.query, limit=payload.limit)
    return {
        "query": payload.query,
        "limit": payload.limit,
        "match_count": len(matches),
        "matches": matches,
    }


@app.post("/decision/preview")
def decision_preview(payload: DecisionRequest):
    return {
        "input": payload.report,
        "decision": classify_report(payload.report),
    }


@app.get("/call/start", response_model=CallStartResponse)
def call_start():
    orchestrator = get_call_orchestrator()
    return orchestrator.start_call()


@app.post("/call/turn")
def call_turn(payload: CallTurnRequest):
    orchestrator = get_call_orchestrator()
    return orchestrator.respond(payload.utterance)


@app.get("/admin/documents")
def list_admin_documents():
    service = get_admin_service()
    return _files_response(service.list_documents())


@app.post("/admin/documents")
def upload_admin_document(file: UploadFile = File(...)):
    service = get_admin_service()
    try:
        uploaded = service.upload_document(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return uploaded


@app.delete("/admin/documents/{document_id}")
def delete_admin_document(document_id: str):
    service = get_admin_service()
    try:
        return service.delete_document(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/admin")
def admin_page():
    return FileResponse(FRONTEND_DIR / "admin.html")


@app.get("/call")
def call_page():
    return FileResponse(FRONTEND_DIR / "call.html")