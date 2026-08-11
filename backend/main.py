from functools import lru_cache
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
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
from backend.call.service import CallSessionService
from backend.rag.store import CorpusVectorStore
from backend.stt.service import GroqWhisperTranscriber


# @lru_cache(maxsize=1) convierte cada get_*() en un singleton perezoso: la
# primera petición que lo necesite construye la instancia (y con ella carga el
# modelo de embeddings, ~470MB, desde disco); todas las peticiones siguientes
# reciben la misma instancia ya en memoria. Antes cada función creaba una
# instancia nueva EN CADA PETICIÓN — y CorpusVectorStore recarga el modelo de
# SentenceTransformer completo en su constructor — así que cada llamada a
# /admin/documents, /rag/search, /call/session/turn, etc. repetía esa carga
# desde cero. En Linux con el archivo ya en caché de página no se notaba tanto;
# en Windows (sin ese caché "caliente", con Windows Defender escaneando cada
# lectura) esto se sentía como que la subida de un documento se quedaba
# colgada, cuando en realidad estaba recargando el modelo en cada request.
@lru_cache(maxsize=1)
def get_vector_store() -> CorpusVectorStore:
    return CorpusVectorStore(root_dir=ROOT_DIR)


@lru_cache(maxsize=1)
def get_admin_service() -> AdminDocumentService:
    return AdminDocumentService(root_dir=ROOT_DIR, vector_store=get_vector_store())


@lru_cache(maxsize=1)
def get_call_orchestrator() -> CallOrchestrator:
    return CallOrchestrator(root_dir=ROOT_DIR, vector_store=get_vector_store())


@lru_cache(maxsize=1)
def get_call_session_service() -> CallSessionService:
    return CallSessionService(root_dir=ROOT_DIR, orchestrator=get_call_orchestrator())


@lru_cache(maxsize=1)
def get_transcriber() -> GroqWhisperTranscriber:
    return GroqWhisperTranscriber()


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, description="Texto a recuperar desde el corpus clínico")
    limit: int = Field(default=5, ge=1, le=20)


class DecisionRequest(BaseModel):
    report: str = Field(min_length=1, description="Texto libre con síntomas o hallazgos del paciente")


class CallTurnRequest(BaseModel):
    utterance: str = Field(min_length=1, description="Turno del paciente transcrito o escrito")


class CallStartResponse(BaseModel):
    session_id: str
    assistant_text: str
    expected_next: str
    escalation_required: bool


class CallTurnWithSessionRequest(BaseModel):
    session_id: str = Field(min_length=1)
    utterance: str = Field(min_length=1, description="Turno del paciente transcrito o escrito")


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
    service = get_call_session_service()
    return service.start_call()


@app.post("/call/turn")
def call_turn(payload: CallTurnRequest):
    orchestrator = get_call_orchestrator()
    return orchestrator.respond(payload.utterance)


@app.post("/call/session/turn")
def call_turn_with_session(payload: CallTurnWithSessionRequest):
    service = get_call_session_service()
    try:
        return service.turn(payload.session_id, payload.utterance)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/stt/status")
def stt_status():
    transcriber = get_transcriber()
    return {
        "available": transcriber.is_available(),
        "model": transcriber.model_name,
        "language": transcriber.language,
    }


@app.post("/call/session/turn/audio")
async def call_turn_with_audio(
    session_id: str = Form(...),
    audio: UploadFile = File(...),
):
    transcriber = get_transcriber()
    if not transcriber.is_available():
        raise HTTPException(
            status_code=503,
            detail="Groq STT no está configurado (falta GROQ_API_KEY). Usa el texto manual mientras tanto.",
        )

    audio_bytes = await audio.read()
    stt_started_at = perf_counter()
    try:
        transcription = transcriber.transcribe(audio_bytes, filename=audio.filename or "audio.webm")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"Error al transcribir con Groq: {exc}") from exc
    stt_latency_ms = round((perf_counter() - stt_started_at) * 1000, 2)

    if not transcription.text:
        raise HTTPException(status_code=422, detail="No se detectó texto en el audio enviado.")

    service = get_call_session_service()
    try:
        result = service.turn(session_id, transcription.text, stt_latency_ms=stt_latency_ms)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        **result,
        "stt_model": transcription.model_name,
        "stt_language": transcription.language,
    }


@app.get("/call/session/{session_id}")
def get_call_session(session_id: str):
    service = get_call_session_service()
    try:
        return service.get_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/call/session/{session_id}/close")
def close_call_session(session_id: str):
    service = get_call_session_service()
    try:
        return service.close_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/metrics")
def metrics():
    store = get_vector_store()
    call_service = get_call_session_service()
    admin_service = get_admin_service()

    return {
        "vector_index": store.status(DATASET_DIR),
        "admin_documents": len(admin_service.list_documents()),
        "call_sessions": call_service.global_metrics(),
    }


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