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
        # cualquier llamada. Gemini 2.5 Flash tampoco está disponible para API keys
        # nuevas ("no longer available to new users"), así que migramos directo a
        # Gemini 3.5 Flash (generación vigente, GA, sin fecha de retiro anunciada).
        # La rúbrica del reto (G3) exige una FAMILIA permitida (Gemini Flash), no un
        # snapshot puntual — ver https://ai.google.dev/gemini-api/docs/deprecations.
        self.model_name = model_name or os.getenv("GEMINI_MODEL", os.getenv("MODEL_NAME", "gemini-3.5-flash"))
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.available = bool(self.api_key)
        self._client = None

        if self.available:
            # El paquete google-generativeai está deprecado desde Gemini 2.0 en favor
            # del SDK unificado google-genai (ver
            # https://github.com/google-gemini/deprecated-generative-ai-python). Usamos
            # el SDK vigente para que los modelos Gemini 3.x funcionen de forma
            # confiable en vez de arriesgar incompatibilidades con el SDK legado.
            from google import genai

            self._client = genai.Client(api_key=self.api_key)

    def is_available(self) -> bool:
        return self.available and self._client is not None

    def generate(self, prompt: str) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError("Gemini no está disponible en este entorno")

        from google.genai import types

        result = self._client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=800,
                # Gemini 3.x razona internamente ("thinking") antes de responder, y ese
                # razonamiento consume parte del presupuesto de max_output_tokens. Con
                # el nivel por defecto, casi todo el presupuesto se iba en pensar y la
                # respuesta visible quedaba cortada a media frase. Para una respuesta
                # corta y conversacional como esta, "minimal" prioriza velocidad y deja
                # el presupuesto completo para el texto real — además baja bastante la
                # latencia, importante en una llamada de voz en tiempo real.
                thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
            ),
        )
        text = getattr(result, "text", None) or ""
        if not text.strip():
            raise RuntimeError("Gemini devolvió una respuesta vacía")
        return LLMResponse(text=text.strip(), model_name=self.model_name, used_remote_model=True)
