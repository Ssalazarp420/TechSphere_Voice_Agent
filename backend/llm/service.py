from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model_name: str
    used_remote_model: bool


class GeminiResponder:
    def __init__(self, model_name: str | None = None) -> None:
        # Gemini 1.5 (toda la familia) fue retirado por Google y devuelve 404 en
        # cualquier llamada — ver https://ai.google.dev/gemini-api/docs/deprecations.
        # La rúbrica del reto (G3) exige una FAMILIA permitida (Gemini Flash), no un
        # snapshot puntual, así que migramos a la generación Flash vigente en vez de
        # cambiar de familia de modelo.
        self.model_name = model_name or os.getenv("GEMINI_MODEL", os.getenv("MODEL_NAME", "gemini-2.5-flash"))
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.available = bool(self.api_key)
        self._model = None

        if self.available:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(self.model_name)

    def is_available(self) -> bool:
        return self.available and self._model is not None

    def generate(self, prompt: str) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError("Gemini no está disponible en este entorno")

        result = self._model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 220,
            },
        )
        text = getattr(result, "text", None) or ""
        if not text.strip():
            raise RuntimeError("Gemini devolvió una respuesta vacía")
        return LLMResponse(text=text.strip(), model_name=self.model_name, used_remote_model=True)
