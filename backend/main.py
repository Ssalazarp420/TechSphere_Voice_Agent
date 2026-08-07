from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="TechSphere Voice Agent")

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "TechSphere Voice Agent"}


@app.get("/admin")
def admin_page() -> HTMLResponse:
    html = (FRONTEND_DIR / "admin.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.get("/call")
def call_page() -> HTMLResponse:
    html = (FRONTEND_DIR / "call.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)
