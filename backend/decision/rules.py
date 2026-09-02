from __future__ import annotations

import re
from dataclasses import dataclass, asdict


RED_FLAG_KEYWORDS = [
    "dificultad para respirar",
    "falta de aire",
    "me ahogo",
    "no puedo respirar",
    "dolor de pecho",
    "dolor en el pecho",
    "desmayo",
    "me desmaye",
    "me desmayé",
    "confusion",
    "confusión",
    "no reconozco",
    "sangrado abundante",
    "sangra mucho",
    "no para de sangrar",
    "herida abierta",
    "se me abrio la herida",
    "se me abrió la herida",
    "pus",
    "secrecion con mal olor",
    "secreción con mal olor",
    "mal olor",
    "olor fétido",
    "olor feo",
    "huele mal",
    "huele raro",
    "huele feo",
    "vomito persistente",
    "vómito persistente",
    "no para de vomitar",
    "veo borroso",
    "se me durmió medio cuerpo",
    "se me durmió la mitad",
]

YELLOW_FLAG_KEYWORDS = [
    "fiebre",
    "calentura",
    "enrojecimiento",
    "enrojecida",
    "colorada",
    "inflamacion",
    "inflamación",
    "hinchada",
    "hinchado",
    "hinchazon",
    "hinchazón hinchazón",
    "nausea",
    "náusea",
    "vomito",
    "vómito",
    "dolor moderado",
    "dolor fuerte",
    "dolor severo",
    "dolor muy fuerte",
    "duele mucho",
    "duele bastante",
    "poco apetito",
    "sin apetito",
    "no como nada",
    "debilidad",
    "muy débil",
    "muy debil",
    "mareo",
    "mareada",
    "mareado",
    "supura",
    "chorrea",
    "gotea",
    "arde mucho",
    "me arde bastante",
    "abultado",
    "abultada",
    "caliente al tacto",
    "caliente la herida",
]

# Frases que indican que el paciente reporta sentirse bien o sin síntomas.
# Necesarias para no penalizar como "ambiguo" un reporte tranquilizador
# genuino (evitaría convertir cada respuesta calmada en un falso amarillo).
REASSURANCE_PATTERNS = [
    "me siento bien",
    "estoy bien",
    "todo bien",
    "todo normal",
    "sin dolor",
    "no tengo dolor",
    "no me duele",
    "sin fiebre",
    "no tengo fiebre",
    "nada raro",
    "no tengo nada",
    "ningun sintoma",
    "ningún síntoma",
    "muy bien",
    "excelente",
    "de maravilla",
]

# Lenguaje vago/regional que en la práctica describe un síntoma real pero no
# calza con ninguna keyword clínica de las listas de arriba — el ejemplo del
# propio README del reto ("me duele como aquí abajito de la axila") es
# exactamente este caso. Si aparece sin que ninguna lista anterior lo capture
# y sin que el paciente se muestre tranquilo, el sistema no debe decidir
# "verde" en silencio: debe tratarlo como señal amarilla y pedir precisión.
AMBIGUOUS_MARKERS = [
    "como que",
    "como si",
    "medio raro",
    "algo raro",
    "se siente raro",
    "raro aqui",
    "raro aquí",
    "no se que es",
    "no sé qué es",
    "no se si es normal",
    "no sé si es normal",
    "no estoy seguro",
    "no estoy segura",
    "tal vez",
    "quizas",
    "quizás",
    "una cosa aqui",
    "una cosa aquí",
    "algo aqui abajo",
    "algo aquí abajo",
    "abajito",
    "por aqui",
    "por aquí",
    "se me sale",
    "no se explicarlo",
    "no sé explicarlo",
    "algo extraño",
    "algo raro cuando",
]


@dataclass(frozen=True)
class DecisionResult:
    label: str
    rationale: str
    score: int
    red_flags: list[str]
    yellow_flags: list[str]
    requires_clarification: bool = False
    follow_up_question: str | None = None
    # Se calculaban en classify_report() para el score y se descartaban al
    # construir el resultado — el resumen de la llamada (2.3) los necesita
    # como campos de primer nivel, no solo como insumo interno del score.
    pain_value: float | None = None
    temperature_value: float | None = None


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


# "sin fiebre" o "no tengo dolor" no pueden activar la keyword solo porque la
# palabra aparece en el texto: sin esto, cualquier negación explícita del
# síntoma se leía como si el síntoma estuviera presente (falso positivo). Se
# busca una señal de negación en una ventana corta inmediatamente antes de la
# keyword, en vez de un NLP completo — suficiente para el caso común de un
# turno de voz corto.
NEGATION_CUES = [
    "sin ",
    "no tengo",
    "no tiene",
    "no hay",
    "no presenta",
    "no ha tenido",
    "nada de",
    "ausencia de",
    "niega",
    "no siento",
    "no me duele",
]


def _is_negated(lowered: str, keyword: str, window: int = 25) -> bool:
    index = lowered.find(keyword)
    if index == -1:
        return False
    preceding = lowered[max(0, index - window):index]
    return any(cue in preceding for cue in NEGATION_CUES)


def classify_report(text: str) -> dict[str, object]:
    lowered = text.lower()
    red_flags = [keyword for keyword in RED_FLAG_KEYWORDS if keyword in lowered and not _is_negated(lowered, keyword)]
    yellow_flags = [
        keyword for keyword in YELLOW_FLAG_KEYWORDS if keyword in lowered and not _is_negated(lowered, keyword)
    ]

    pain_value = _extract_numeric_value(
        lowered,
        [r"(?:dolor|pain)\s*(?:de\s*)?(?:es de|en|nivel)?\s*(\d+(?:[.,]\d+)?)", r"(\d+(?:[.,]\d+)?)\s*/\s*10"],
    )
    # Antes exigía que el número siguiera inmediatamente a la palabra clave
    # ("fiebre 39"), sin permitir "de" en medio como sí lo permite el patrón
    # de dolor arriba. "Fiebre de 39" es la forma más natural de decirlo en
    # español y no se capturaba: el score no sumaba los 3 puntos de fiebre
    # alta y una fiebre de 39°C sola podía clasificar como amarillo en vez de
    # rojo — exactamente el tipo de falso negativo que la rúbrica marca como
    # la falla catastrófica en salud.
    temperature_value = _extract_numeric_value(
        lowered, [r"(?:fiebre|temperatura|temp)\s*(?:es de\s*|de\s*)?(\d+(?:[.,]\d+)?)"]
    )

    has_reassurance = any(pattern in lowered for pattern in REASSURANCE_PATTERNS)
    ambiguous_hits = [marker for marker in AMBIGUOUS_MARKERS if marker in lowered]

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

    # Asimetría clínica (rúbrica: el falso negativo es la falla catastrófica).
    # Si el paciente describe algo con lenguaje vago/regional que ninguna
    # keyword clínica captura, y no se está mostrando explícitamente tranquilo,
    # no hay base para decidir "verde" con confianza. Se trata como señal
    # amarilla — obliga a indagar en vez de tranquilizar por defecto.
    is_ambiguous_signal = bool(ambiguous_hits) and not red_flags and not yellow_flags and not has_reassurance
    if is_ambiguous_signal:
        score += 1
        yellow_flags = yellow_flags + ["lenguaje ambiguo sin síntoma clínico identificado"]

    # Un reporte sin ninguna palabra reconocible (ni de alarma, ni ambigua, ni
    # de tranquilidad) tampoco es evidencia de que todo esté bien — es
    # simplemente falta de información. Se marca para que el agente indague
    # antes de tranquilizar, sin forzar el score hacia amarillo (podría ser un
    # "hola" o un turno de apertura, no un síntoma negado).
    is_uninformative = not (red_flags or yellow_flags or has_reassurance or ambiguous_hits or pain_value is not None or temperature_value is not None)

    requires_clarification = is_ambiguous_signal or is_uninformative
    follow_up_question = (
        "¿Puedes contarme con más detalle qué sientes exactamente, en qué parte del cuerpo y desde cuándo?"
        if requires_clarification
        else None
    )

    if score >= 3:
        label = "rojo"
        rationale = "Se detectaron signos de alarma que requieren escalamiento inmediato."
    elif score >= 1:
        label = "amarillo"
        rationale = (
            "El reporte usa lenguaje ambiguo o regional que no se puede clasificar con confianza; "
            "se requiere indagar más antes de descartar riesgo."
            if is_ambiguous_signal
            else "Hay síntomas que ameritan seguimiento estrecho y posible escalamiento."
        )
    else:
        label = "verde"
        rationale = (
            "No hay suficiente información para clasificar el reporte; se requiere indagar antes de tranquilizar."
            if is_uninformative
            else "No se detectan signos de alarma en el texto reportado."
        )

    return asdict(
        DecisionResult(
            label=label,
            rationale=rationale,
            score=score,
            red_flags=red_flags,
            yellow_flags=yellow_flags,
            requires_clarification=requires_clarification,
            follow_up_question=follow_up_question,
            pain_value=pain_value,
            temperature_value=temperature_value,
        )
    )
