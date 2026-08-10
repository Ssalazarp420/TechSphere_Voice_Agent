from __future__ import annotations

import os


def _read_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return float(value)
    except ValueError:
        return default


# Tarifas de referencia para extrapolar costo de producción, tal como pide la
# rúbrica (§5: "si tu solución corre local, extrapola a precios de API de
# producción y explica el cálculo"). Se dejan configurables por variable de
# entorno porque las tarifas de los proveedores cambian; los valores por
# defecto son un orden de magnitud razonable para los tiers Flash/Whisper al
# momento de escribir esto, pero deben verificarse contra la página de precios
# vigente antes de reportarlos como definitivos en el informe final.
GEMINI_INPUT_PRICE_PER_1M_USD = _read_env_float("GEMINI_INPUT_PRICE_PER_1M_USD", 0.15)
GEMINI_OUTPUT_PRICE_PER_1M_USD = _read_env_float("GEMINI_OUTPUT_PRICE_PER_1M_USD", 0.60)
GROQ_STT_PRICE_PER_MINUTE_USD = _read_env_float("GROQ_STT_PRICE_PER_MINUTE_USD", 0.00463)

# No decodificamos el audio para medir su duración real, así que estimamos el
# costo de transcripción asumiendo una duración promedio por turno hablado.
# Es una aproximación explícita, no una medición — se documenta como tal en el
# README para no reportar una cifra que no se sostiene contra los logs.
AVG_AUDIO_TURN_SECONDS = _read_env_float("AVG_AUDIO_TURN_SECONDS", 8.0)


def estimate_llm_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000) * GEMINI_INPUT_PRICE_PER_1M_USD + (
        output_tokens / 1_000_000
    ) * GEMINI_OUTPUT_PRICE_PER_1M_USD


def estimate_stt_cost_usd(audio_turns: int) -> float:
    minutes = audio_turns * (AVG_AUDIO_TURN_SECONDS / 60)
    return minutes * GROQ_STT_PRICE_PER_MINUTE_USD


def pricing_assumptions() -> dict[str, float]:
    """Expone las tarifas activas para que /metrics y el README puedan citarlas
    junto con la cifra de costo, en vez de dejar el número sin trazabilidad."""
    return {
        "gemini_input_price_per_1m_usd": GEMINI_INPUT_PRICE_PER_1M_USD,
        "gemini_output_price_per_1m_usd": GEMINI_OUTPUT_PRICE_PER_1M_USD,
        "groq_stt_price_per_minute_usd": GROQ_STT_PRICE_PER_MINUTE_USD,
        "avg_audio_turn_seconds_assumed": AVG_AUDIO_TURN_SECONDS,
    }
