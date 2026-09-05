from __future__ import annotations

import re
from dataclasses import dataclass, asdict


# Día de postoperatorio hasta el cual se considera "ventana temprana", donde
# los signos leves son parte de la recuperación esperada y no de una
# complicación.
#
# Se probaron tres ventanas contra el gold-set. Extenderla al día 3 da la mejor
# accuracy (0.650 / 0.600 frente a 0.594 / 0.531), pero hace que se escapen 8
# casos amarillo más: `amarillo -> verde` pasa de 3 a 11 en ambas capas. El día
# 3 es precisamente donde la etiqueta real tiene más amarillos (30%), así que
# descontar ahí los pierde.
#
# Se elige la ventana conservadora porque el criterio declarado del proyecto es
# que el falso negativo es la falla grave, y tranquilizar a un paciente que
# necesitaba seguimiento estrecho es un falso negativo. Cambiar 8 de ésos por
# unos puntos de accuracy iría en contra de la asimetría que el resto del motor
# aplica de forma deliberada.
EARLY_POSTOP_DAYS = 2

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
    # Agregadas tras el eval contra el gold-set del reto: "la pierna como que
    # no responde, muy incapacitada me siento" no calzaba con ninguna
    # keyword existente y caía al genérico "lenguaje ambiguo" (solo +1),
    # perdiendo una señal neuro/motora real que en combinación con fiebre y
    # dolor debía escalar el caso.
    "no responde",
    "no me responde",
    "no puedo mover",
    "no puedo levantarme",
    "muy incapacitada",
    "muy incapacitado",
    # También agregadas tras el eval: "escalofríos" ni siquiera estaba en la
    # lista pese a ser una señal de fiebre muy directa; "afiebrada"/"cuerpo
    # caliente" son formas comunes de reportar fiebre sin decir la palabra
    # "fiebre". (Se probó también agregar mal-dormir y enrojecimiento en
    # diminutivo ["rojita", "duermo mal", etc.] pero el eval mostró que
    # tumbaban el accuracy general de 42% a 31%: ambas frases aparecen igual
    # de seguido en casos genuinamente verdes donde el paciente agrega "pero
    # es normal" — son síntomas de muy baja especificidad para esta señal en
    # particular, y se revirtieron.)
    "escalofrios",
    "escalofríos",
    "escalofrio",
    "escalofrío",
    "afiebrada",
    "afiebrado",
    "cuerpo caliente",
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


_PAIN_WORD_VALUES = {
    "cero": 0.0,
    "un": 1.0,
    "una": 1.0,
    "uno": 1.0,
    "dos": 2.0,
    "tres": 3.0,
    "cuatro": 4.0,
    "cinco": 5.0,
    "seis": 6.0,
    "siete": 7.0,
    "ocho": 8.0,
    "nueve": 9.0,
    "diez": 10.0,
}
# Conectores que pueden preceder a un nivel de dolor escrito en palabras.
# Antes solo se aceptaba "un/uno/una" ("el dolor está en un ocho"), así que
# las demás formas naturales de decirlo en voz —"dolor de nueve", "el dolor
# es de nueve", "dolor nivel nueve", "me duele como nueve"— no extraían
# ningún valor y el turno caía a verde pese a ser un dolor severo. Medido
# antes del arreglo: de seis formas de decir "dolor de nueve", cinco daban
# pain_value=None y label=verde.
_PAIN_WORD_CONNECTORS = r"(?:un[oa]?|de|en|como|nivel|sobre|es)"

# Un número escrito en palabras seguido de una unidad de tiempo es una
# DURACIÓN, no una intensidad: "me duele hace tres días" no es un dolor de 3.
# Sin esta guarda, ampliar los conectores introduce ese falso positivo.
_PAIN_TIME_UNIT = r"(?:d[ií]as?|semanas?|horas?|meses|mes|minutos?|noches?|veces|a[nñ]os?)"

# "un"/"una" quedan fuera de la alternancia de VALORES aunque valgan 1: en
# "el dolor está en un nueve" hacen de artículo, no de cifra, y al estar en la
# lista el motor casaba "en un" y devolvía 1.0 en vez de seguir hasta "nueve".
# Por eso el artículo se admite aparte, como paso opcional entre el conector y
# el valor. "uno" sí se conserva: como numeral no es ambiguo.
_PAIN_WORD_NUMERALS = sorted(
    (word for word in _PAIN_WORD_VALUES if word not in {"un", "una"}),
    key=len,
    reverse=True,
)

_PAIN_WORD_PATTERN = re.compile(
    r"\b" + _PAIN_WORD_CONNECTORS + r"\s+(?:un[oa]?\s+)?("
    + "|".join(_PAIN_WORD_NUMERALS)
    + r")\b(?!\s+" + _PAIN_TIME_UNIT + r")"
)
# Separador de cláusulas que NO corta dentro de un número decimal: sin el
# lookaround, "38.1°C" se partía en cláusulas "38" y "1°c" por el punto
# decimal, y el regex de número solo veía "38" — perdiendo el decimal (no
# afecta el umbral de fiebre aquí, pero sí sería un problema en otros casos).
# El lookbehind original, `(?<!\d)[.,;!?¿()]+(?!\d)`, buscaba proteger los
# decimales ("38.1" no debe partirse en "38" y "1"), pero al exigir que NO
# hubiera un dígito delante impedía cortar tras cualquier número: "el dolor
# está en un 6, sin fiebre" quedaba como UNA sola cláusula, y como contenía la
# palabra "fiebre" y el número 6, la temperatura se extraía como 6.0. Ahora se
# protege solo el caso real: un punto o coma con dígitos a AMBOS lados.
_CLAUSE_SPLIT_PATTERN = re.compile(r"(?:(?<!\d)[.,]|[.,](?!\d)|[;!?¿()])+")


# Ningun numero suelto vale como medida clinica: una escala de dolor vive en
# 0-10 y una temperatura corporal en 35-42. Sin acotar el rango, cualquier
# cifra de la misma clausula servia — "me operaron hace 40 dias y no he tenido
# fiebre" daba temperatura 40.0 y, con ello, ROJO. Verificado que ya ocurria
# antes de estos cambios, en el commit 9c80a1d.
_DURATION_GUARD = r"(?!\s*(?:a[nñ]os?|d[ií]as?|semanas?|meses|mes|horas?|minutos?|noches?|veces))"
_PAIN_DIGIT_PATTERN = re.compile(r"\b(10|[0-9])(?:[.,]\d+)?\b" + _DURATION_GUARD)
_GENERIC_NUMBER_PATTERN = re.compile(r"(\d+(?:[.,]\d+)?)")


def _extract_numeric_value(
    text: str,
    keywords: list[str],
    allow_pain_words: bool = False,
    value_pattern: re.Pattern[str] | None = None,
) -> float | None:
    """Busca el primer número que aparece en la MISMA cláusula que alguna
    keyword, sin exigir que el número siga inmediatamente a la palabra.

    Antes: un regex rígido tipo `(?:dolor)\\s*(?:de\\s*)?(\\d+)`, que exigía que
    el número apareciera casi pegado a la keyword con un set fijo de
    conectores ("de", "es de", "en", "nivel"). Fallaba con cualquier frase
    intermedia natural: "el dolor está como en un 5" o "me tomé la
    temperatura y marcó 38.1°C" no calzaban con ningún conector permitido,
    pese a que la keyword clínica sí estaba presente en la oración. El eval
    contra el gold-set del reto (dataset_final.xlsx) mostró que esto no era
    un caso raro: era la causa de la mayoría de los falsos negativos en rojo.

    Ahora: el texto se separa en cláusulas por puntuación, y si la keyword
    aparece en una cláusula, se toma el primer número de ESA cláusula (en
    cualquier posición relativa a la keyword). Acotar a la cláusula evita
    cruzar hacia un número de un tema distinto en la misma oración larga
    (p.ej. "hace 3 días" en otra cláusula no se confunde con el nivel de
    dolor). allow_pain_words habilita reconocer números de dolor escritos en
    palabras ("un cinco", "un ocho") — común en el habla natural para una
    escala 0-10; no se usa para temperatura, donde el dataset siempre usa
    dígitos ("38.1", "39").
    """
    lowered = text.lower()
    clauses = _CLAUSE_SPLIT_PATTERN.split(lowered)
    for clause in clauses:
        if not any(keyword in clause for keyword in keywords):
            continue
        digit_match = (value_pattern or _GENERIC_NUMBER_PATTERN).search(clause)
        if digit_match:
            try:
                return float(digit_match.group(1).replace(",", "."))
            except ValueError:
                pass
        if allow_pain_words:
            word_match = _PAIN_WORD_PATTERN.search(clause)
            if word_match:
                return _PAIN_WORD_VALUES[word_match.group(1)]
    return None


# "sin fiebre" o "no tengo dolor" no pueden activar la keyword solo porque la
# palabra aparece en el texto: sin esto, cualquier negación explícita del
# síntoma se leía como si el síntoma estuviera presente (falso positivo). Se
# busca una señal de negación en una ventana corta inmediatamente antes de la
# keyword, en vez de un NLP completo — suficiente para el caso común de un
# turno de voz corto.
# Antes: una lista fija de frases exactas ("no tengo", "no siento", "sin ").
# El eval mostró el costo real: "no veo pus ni nada raro" no calzaba con
# ninguna frase de la lista ("no veo" no está, solo "no siento"/"no tengo")
# y "pus" se marcaba como bandera roja pese a estar negada explícitamente —
# un falso rojo por un paciente diciendo, literalmente, que no tiene el
# síntoma. Se reemplaza por una palabra de negación general buscada dentro
# de la MISMA CLÁUSULA que la keyword (no una ventana de caracteres fija,
# que sí podría cruzar hacia una cláusula distinta y negar un síntoma que
# el paciente en realidad sí reportó después de una coma).
_NEGATION_WORDS = ["no", "sin", "nunca", "jamás", "jamas", "niega", "ausencia de", "nada de"]
_NEGATION_WORD_PATTERN = re.compile(r"\b(" + "|".join(w.replace(" ", r"\s+") for w in _NEGATION_WORDS) + r")\b")


# --- Temperatura mencionada sin repetir la palabra clave ----------------------
# _extract_numeric_value exige que la keyword ("fiebre"/"temperatura") esté en
# la MISMA cláusula que el número. Al hablar, casi nadie repite la palabra:
# dice "me la tomé y marcaba como 38 y algo" o "creo que como 39". El número
# queda en una cláusula sin keyword y no se extrae, así que una fiebre real
# no sumaba sus +3 y el turno caía a verde.
#
# Medido en el gold-set, tres falsos negativos rojo venían exactamente de aquí:
#   "la tomé y marcaba como 38 y algo"  -> temperature_value=None
#   "Marcaba como 39 algo"              -> temperature_value=None
#   "afiebrada... creo que como 38"     -> temperature_value=None
#
# Regla de respaldo: si el turno habla de fiebre en cualquier parte, se acepta
# un número en el rango fisiológico plausible (35-42) de todo el turno. Fuera
# de ese rango no se toca nada, y una escala de dolor (0-10) nunca lo alcanza.
_FEVER_CONTEXT_PATTERN = re.compile(
    r"\b(fiebre|calentura|temperatura|term[oó]metro|afiebrad[oa]s?|destemplad[oa]s?"
    r"|calientic[oa]s?|caliente|escalofr[ií]os?|me la tom[eé])\b"
)

# El guardarraíl que hace segura la regla anterior: 38 puede ser una edad o un
# número de días. Sin esto, "tengo 38 años" se leería como fiebre de 38.
_TEMPERATURE_VALUE_PATTERN = re.compile(
    r"\b(3[5-9](?:[.,]\d+)?|4[0-2](?:[.,]\d+)?)\b"
    r"(?!\s*(?:a[nñ]os?|d[ií]as?|semanas?|meses|mes|horas?|minutos?|veces))"
)


# --- Drenaje purulento --------------------------------------------------------
# Un líquido amarillo saliendo de la herida es drenaje purulento: bandera roja
# de infección de sitio operatorio. La lista de keywords solo tenía "pus" y
# "secreción con mal olor", y ningún paciente del gold-set lo dice así — lo
# describen como "un líquido, amarillo creo, saliendo de ahí" o "le sale un
# poquito de líquido ahí, como amarillito". Dos falsos negativos rojo venían
# de esto, ambos clasificados verde con score 0.
#
# Se acepta en los dos órdenes (líquido→color y color→líquido) y se tolera
# puntuación intermedia, porque en el habla real la descripción viene partida
# por comas: "un líquido, amarillo creo, saliendo".
_DRAINAGE_TERMS = r"(?:l[ií]quido|secreci[oó]n|drenaje|supura\w*|le sale|me sale)"
_PURULENT_TERMS = r"(?:amarill\w+|verdos\w+|purulent\w+|espes[oa]s?)"
_PURULENT_DRAINAGE_PATTERN = re.compile(
    _DRAINAGE_TERMS + r"[^.;]{0,45}?" + _PURULENT_TERMS
    + r"|" + _PURULENT_TERMS + r"[^.;]{0,45}?" + _DRAINAGE_TERMS
)


# --- Enrojecimiento dicho en diminutivo ---------------------------------------
# YELLOW_FLAG_KEYWORDS solo tenía "enrojecimiento", "enrojecida" y "colorada".
# Contando cómo lo dicen realmente los pacientes en el gold-set, esas tres
# cubren 94 menciones y se quedan fuera 171: "rojita" (45), "rojo" (40),
# "roja" (32), "rojito" (32), "rojez" (22). Es decir, se perdían dos de cada
# tres menciones de un signo clásico de infección de sitio operatorio.
#
# Va como patrón y no como keyword porque el emparejamiento de keywords es por
# subcadena, y "roja" como subcadena casa dentro de apellidos tan comunes como
# "Rojas". Con \b delimitando la palabra, "rojas" ya no activa "roja".
_WOUND_REDNESS_PATTERN = re.compile(r"\b(roj[ao]|rojit[ao]|rojez|enrojecidit[ao])\b")


def _is_negated_before(lowered: str, start: int) -> bool:
    """¿Hay una negación entre el inicio de la oración y esta posición?

    Se mira solo hacia ATRÁS a propósito. En "sí le sale líquido amarillito,
    pero no es mucho" la negación va después y niega la cantidad, no el
    hallazgo; contarla marcaría como ausente un síntoma que el paciente sí
    reportó. El límite es la oración (punto o punto y coma), no la cláusula,
    porque estas descripciones vienen partidas por comas.
    """
    inicio_oracion = max(lowered.rfind(".", 0, start), lowered.rfind(";", 0, start)) + 1
    return bool(_NEGATION_WORD_PATTERN.search(lowered[inicio_oracion:start]))


def _is_negated(lowered: str, keyword: str) -> bool:
    for clause in _CLAUSE_SPLIT_PATTERN.split(lowered):
        if keyword in clause and _NEGATION_WORD_PATTERN.search(clause):
            return True
    return False


def classify_report(text: str, patient_context: dict[str, object] | None = None) -> dict[str, object]:
    """Clasifica un reporte del paciente en verde / amarillo / rojo.

    `patient_context` es el registro clínico del paciente (procedimiento, fecha
    de cirugía, edad, comorbilidades) tal como lo devuelve
    PatientLookupService.get_patient_context. Es opcional y por defecto no
    altera el resultado: hasta ahora el historial solo alimentaba la redacción
    de la respuesta, no la decisión, de modo que dos pacientes con perfiles de
    riesgo muy distintos recibían la misma clasificación ante síntomas
    idénticos.
    """
    lowered = text.lower()
    red_flags = [keyword for keyword in RED_FLAG_KEYWORDS if keyword in lowered and not _is_negated(lowered, keyword)]
    yellow_flags = [
        keyword for keyword in YELLOW_FLAG_KEYWORDS if keyword in lowered and not _is_negated(lowered, keyword)
    ]

    # "duele"/"duelen" además de "dolor": la cláusula se descarta antes de
    # buscar el número si no contiene ninguna keyword, así que "me duele como
    # nueve" no llegaba siquiera a evaluarse.
    pain_value = _extract_numeric_value(
        lowered, ["dolor", "duele", "duelen", "pain"], allow_pain_words=True, value_pattern=_PAIN_DIGIT_PATTERN
    )
    temperature_value = _extract_numeric_value(
        lowered, ["fiebre", "temperatura", "temp"], value_pattern=_TEMPERATURE_VALUE_PATTERN
    )
    if temperature_value is None and _FEVER_CONTEXT_PATTERN.search(lowered):
        temp_match = _TEMPERATURE_VALUE_PATTERN.search(lowered)
        if temp_match and not _is_negated_before(lowered, temp_match.start()):
            temperature_value = float(temp_match.group(1).replace(",", "."))

    redness_match = _WOUND_REDNESS_PATTERN.search(lowered)
    if (
        redness_match
        and not _is_negated_before(lowered, redness_match.start())
        and not any(f in yellow_flags for f in ("enrojecimiento", "enrojecida", "colorada"))
    ):
        yellow_flags = yellow_flags + ["enrojecimiento de la herida"]

    drainage_match = _PURULENT_DRAINAGE_PATTERN.search(lowered)
    if drainage_match and not _is_negated_before(lowered, drainage_match.start()):
        red_flags = red_flags + ["drenaje purulento (líquido amarillento en la herida)"]

    has_reassurance = any(pattern in lowered for pattern in REASSURANCE_PATTERNS)
    ambiguous_hits = [marker for marker in AMBIGUOUS_MARKERS if marker in lowered]

    # El puntaje se separa en señales DURAS y BLANDAS para poder modular las
    # segundas según el día de postoperatorio (ver la ventana temprana más
    # abajo). Las duras —un signo de alarma, fiebre >=38, dolor severo— nunca
    # se modulan: son anómalas en cualquier día del postoperatorio.
    hard_score = 0
    if red_flags:
        hard_score += 3
    if temperature_value is not None and temperature_value >= 38.0:
        hard_score += 3
    if pain_value is not None and pain_value >= 8:
        hard_score += 2

    score = 0
    # Antes: `if yellow_flags: score += 1` — un paciente con 1 síntoma amarillo
    # sumaba exactamente lo mismo que uno con 5 concurrentes (fiebre, escalofríos,
    # enrojecimiento, poco apetito, mal dormir). El eval mostró varios rojo reales
    # con múltiples síntomas moderados simultáneos que nunca alcanzaban el umbral
    # de escalamiento porque cada uno individualmente era "solo amarillo". La
    # combinación de varios síntomas concurrentes es en sí misma una señal de
    # severidad mayor, no aditiva 1 a 1 con el peso de un signo aislado — se
    # limita a +3 para no sobreponderar frente a un signo de alarma real (que
    # vale +3 también) ni convertir cualquier lista larga de síntomas leves en
    # rojo automático.
    if yellow_flags:
        score += min(len(yellow_flags), 3)
    if temperature_value is not None and 37.5 <= temperature_value < 38.0:
        score += 1
    # Dolor moderado-alto (6-7.9): no llega al umbral de +2 de "severo" (>=8),
    # pero tampoco es un dato a ignorar — mismo criterio escalonado que ya se
    # usaba para temperatura (37.5-38 vs >=38).
    if pain_value is not None and 6 <= pain_value < 8:
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

    # --- Ventana temprana del postoperatorio -------------------------------
    # Febrícula, dolor moderado y molestias leves son parte de la recuperación
    # esperada en los primeros días; los mismos signos a partir de la semana ya
    # no lo son. Hasta aquí el motor puntuaba idéntico el día 2 y el día 14.
    #
    # Distribución real de la etiqueta por día en el gold-set:
    #   día  1: rojo  0.0%   amarillo  7.5%   verde 92.5%
    #   día  3: rojo  0.0%   amarillo 30.0%   verde 70.0%
    #   día  7: rojo 15.0%   amarillo 25.0%   verde 60.0%
    #   día 14: rojo 15.0%   amarillo  0.0%   verde 85.0%
    # No hay un solo caso rojo antes del día 7, coherente con que una infección
    # de sitio operatorio no se manifiesta a las 24 horas.
    #
    # Por eso en la ventana temprana se descuenta UN punto, y solo de las
    # señales blandas. Nunca de las duras: una fiebre de 39 o un drenaje
    # purulento en el día 2 siguen escalando igual, porque son anómalos
    # cualquier día. El descuento no puede bajar de cero.
    dias_postop = None
    if patient_context:
        raw_dias = patient_context.get("dias_postop")
        if raw_dias is not None:
            try:
                dias_postop = int(raw_dias)
            except (TypeError, ValueError):
                dias_postop = None

    early_window = dias_postop is not None and dias_postop <= EARLY_POSTOP_DAYS
    if early_window:
        score = max(0, score - 1)

    score += hard_score

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
