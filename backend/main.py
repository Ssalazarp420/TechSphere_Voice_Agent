from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="TechSphere Voice Agent")

# Verifica que las API keys cargaron (no las expone, solo confirma presencia)
@app.get("/health")
def health():
    return {
        "status": "ok",
        "gemini_key_loaded": bool(os.getenv("GEMINI_API_KEY")),
        "groq_key_loaded": bool(os.getenv("GROQ_API_KEY")),
    }

@app.get("/admin")
def admin_page():
    return FileResponse("frontend/admin.html")

@app.get("/call")
def call_page():
    return FileResponse("frontend/call.html")