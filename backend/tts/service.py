from __future__ import annotations

import io
import os
import wave
from pathlib import Path


class PiperSynthesizer:
    def __init__(self, root_dir: Path) -> None:
        self.model_path = Path(
            os.getenv(
                "PIPER_MODEL",
                str(root_dir / "backend" / "data" / "tts" / "es_MX-claude-high.onnx"),
            )
        )
        self.config_path = Path(
            os.getenv("PIPER_CONFIG", str(self.model_path.with_suffix(".onnx.json")))
        )
        self.available = self.model_path.is_file() and self.config_path.is_file()
        self._voice = None

    def is_available(self) -> bool:
        return self.available

    def synthesize(self, text: str) -> bytes:
        if not self.available:
            raise RuntimeError("Piper no está configurado: faltan el modelo o su configuración")
        if not text.strip():
            raise ValueError("El texto para sintetizar está vacío")

        if self._voice is None:
            from piper import PiperVoice

            self._voice = PiperVoice.load(self.model_path, self.config_path)

        output = io.BytesIO()
        with wave.open(output, "wb") as wav_file:
            self._voice.synthesize_wav(text.strip(), wav_file)
        return output.getvalue()