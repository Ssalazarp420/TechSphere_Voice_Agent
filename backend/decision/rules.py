from __future__ import annotations

import re
from dataclasses import dataclass, asdict


RED_FLAG_KEYWORDS = [
    "dificultad para respirar",
    "falta de aire",
    "dolor de pecho",
    "desmayo",
    "confusion",
    "confusión",
    "sangrado abundante",
    "herida abierta",
    "pus",
    "secrecion con mal olor",
    "secreción con mal olor",
    "mal olor",
    "olor fétido",
    "huele mal",
    "huele raro",
    "vomito persistente",
    "vómito persistente",
]

YELLOW_FLAG_KEYWORDS = [
    "fiebre",
    "enrojecimiento",
    "inflamacion",
    "inflamación",
    "nausea",
    "náusea",
    "vomito",
    "vómito",
    "dolor moderado",
    "dolor fuerte",
    "dolor severo",
    "poco apetito",
    "debilidad",
]


@dataclass(frozen=True)
class DecisionResult:
    label: str
    rationale: str
    score: int
    red_flags: list[str]
    yellow_flags: list[str]


def _extract_numeric_value(text: str, keyword_patterns: list[str]) -> float | None:
    lowered = text.lower()
    for pattern in keyword_patterns:
        match = re.search(pattern, lowered)
        if match:
            try:
                return float(match.group(1))
            except (IndexError, ValueError):
                continue
    return None


def classify_report(text: str) -> dict[str, object]:
    lowered = text.lower()
    red_flags = [keyword for keyword in RED_FLAG_KEYWORDS if keyword in lowered]
    yellow_flags = [keyword for keyword in YELLOW_FLAG_KEYWORDS if keyword in lowered]

    pain_value = _extract_numeric_value(
        lowered,
        [r"(?:dolor|pain)\s*(?:de\s*)?(?:es de|en|nivel)?\s*(\d+(?:[.,]\d+)?)", r"(\d+(?:[.,]\d+)?)\s*/\s*10"],
    )
    temperature_value = _extract_numeric_value(lowered, [r"(?:fiebre|temperatura|temp)\s*(\d+(?:[.,]\d+)?)"])

    score = 0
    if red_flags:
        score += 3
    if temperature_value is not None and temperature_value >= 38.0:
        score += 3
    if pain_value is not None and pain_value >= 8:
        score += 2
    if yellow_flags:
        score += 1
    if temperature_value is not None and 37.5 <= temperature_value < 38.0:
        score += 1

    if score >= 3:
        label = "rojo"
        rationale = "Se detectaron signos de alarma que requieren escalamiento inmediato."
    elif score >= 1:
        label = "amarillo"
        rationale = "Hay síntomas que ameritan seguimiento estrecho y posible escalamiento."
    else:
        label = "verde"
        rationale = "No se detectan signos de alarma en el texto reportado."

    return asdict(
        DecisionResult(
            label=label,
            rationale=rationale,
            score=score,
            red_flags=red_flags,
            yellow_flags=yellow_flags,
        )
    )
