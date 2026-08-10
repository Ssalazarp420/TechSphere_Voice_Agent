from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    model_name: str
    language: str


class GroqWhisperTranscriber:
    """Transcripción de voz a texto usando Groq Whisper Large V3.

    Reemplaza el reconocimiento de voz del navegador (Web Speech API), que solo
    funciona de forma confiable en Chrome/Edge y no da control sobre el modelo
    usado. Corre en el backend, así que funciona igual sin importar el navegador
    del paciente o del evaluador.
    """

    def __init__(self, model_name: str | None = None, language: str | None = None) -> None:
        self.model_name = model_name or os.getenv("GROQ_STT_MODEL", "whisper-large-v3")
        self.language = language or os.getenv("GROQ_STT_LANGUAGE", "es")
        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.available = bool(self.api_key)
        self._client = None

        if self.available:
            from groq import Groq

            self._client = Groq(api_key=self.api_key)

    def is_available(self) -> bool:
        return self.available and self._client is not None

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> TranscriptionResult:
        if not self.is_available():
            raise RuntimeError(
                "Groq STT no está disponible: falta configurar GROQ_API_KEY en el entorno."
            )

        if not audio_bytes:
            raise ValueError("El audio recibido está vacío.")

        response = self._client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model=self.model_name,
            language=self.language,
            response_format="text",
        )

        # El SDK de Groq devuelve un string plano cuando response_format="text",
        # o un objeto con atributo .text para otros formatos; cubrimos ambos casos.
        text = response if isinstance(response, str) else getattr(response, "text", "")
        return TranscriptionResult(text=text.strip(), model_name=self.model_name, language=self.language)
