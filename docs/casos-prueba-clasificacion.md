# Casos de prueba para la demo

## Propósito

Este documento sirve como guía rápida para preparar preguntas al agente durante la demo. Relaciona:

- el procedimiento seleccionado;
- una frase de síntomas que se puede decir al agente;
- la clasificación esperada por las reglas actuales;
- la pregunta de seguimiento que conviene hacer;
- el tipo de respuesta que se espera escuchar y verificar en las referencias del RAG.

No es un protocolo médico ni sustituye la valoración de un profesional. Las categorías descritas aquí son el comportamiento de la lógica implementada en `backend/decision/rules.py`. El RAG aporta contexto documental, pero no cambia automáticamente las reglas de clasificación según la cirugía.

## Cómo usarlo en la demo

1. Selecciona un paciente cuyo procedimiento corresponda al caso.
2. Inicia la llamada.
3. Lee literalmente una de las frases de prueba o adáptala sin cambiar su significado.
4. Comprueba el color o etiqueta de decisión en la interfaz.
5. Revisa las referencias recuperadas y pregunta por el documento mostrado.
6. Observa si la respuesta hablada es breve, concreta y coherente con la clasificación.

Para que la prueba sea reproducible, conviene decir el síntoma y su intensidad en la misma frase. Por ejemplo: `tengo fiebre de 38.5 y la herida está enrojecida`.

## Resumen de categorías actuales

| Categoría | Qué debe decir el paciente | Ejemplo breve | Resultado esperado |
|---|---|---|---|
| **Verde** | Afirma explícitamente que está bien o que no tiene síntomas relevantes. | `Me siento bien, no tengo dolor ni fiebre. Todo normal.` | Verde. No se detectan signos de alarma. |
| **Amarillo** | Reporta un síntoma que requiere seguimiento, o usa lenguaje ambiguo que necesita precisión. | `Tengo fiebre de 37.8.` | Amarillo. El agente debe indagar y orientar según el contexto recuperado. |
| **Rojo** | Reporta un signo de alarma, o combina varios hallazgos hasta alcanzar el umbral de escalamiento. | `La herida está abierta y sangra mucho.` | Rojo. Debe indicar escalamiento inmediato. |

### Regla práctica

- **Rojo:** dificultad para respirar, dolor de pecho, desmayo, confusión, sangrado abundante, herida abierta, pus o mal olor, vómito persistente, alteraciones neurológicas importantes.
- **Amarillo:** fiebre o calentura, enrojecimiento, inflamación, hinchazón, náusea, vómito aislado, dolor fuerte o moderado, poco apetito, debilidad, mareo, supuración o herida caliente.
- **Verde:** `me siento bien`, `todo normal`, `sin dolor`, `sin fiebre`, `nada raro` u otra afirmación equivalente.
- **Ambiguo:** `siento algo raro`, `me duele como aquí abajo`, `no sé si es normal`. Se marca amarillo y debe pedir precisión.
- **Sin información:** un saludo o una respuesta que no describe síntomas no demuestra que el paciente esté bien; el agente debe pedir detalles antes de tranquilizar.

> Importante: una frase roja tiene prioridad práctica sobre una frase tranquilizadora posterior. Si durante la llamada aparece un signo de alarma, no se debe cerrar la demo como si nunca hubiera ocurrido.

## Casos generales de clasificación

Estos son los casos más fáciles de repetir y sirven para verificar la lógica antes de probar una cirugía específica.

### Caso verde: recuperación sin señales de alarma

**Frase para decir:**

> Me siento bien después de la cirugía. No tengo dolor ni fiebre. Todo normal.

**Clasificación esperada:** `verde`.

**Qué debe hacer el agente:** reconocer que no se detectan signos de alarma y hacer, como máximo, una pregunta breve de seguimiento si el modelo la considera necesaria. No debe inventar medicamentos ni instrucciones que no estén en las referencias.

**Pregunta para el RAG:**

> ¿Cuáles son los cuidados normales en casa después de esta cirugía y qué cambios debería vigilar?

### Caso amarillo: síntoma que requiere seguimiento

**Frase para decir:**

> Tengo fiebre de 37.8.

**Clasificación esperada:** `amarillo`.

**Qué debe hacer el agente:** pedir o confirmar datos como desde cuándo ocurre, temperatura exacta, evolución, localización y estado de la herida. Debe evitar tranquilizar automáticamente.

**Pregunta para el RAG:**

> Según las instrucciones de esta cirugía, ¿cuándo la fiebre, el enrojecimiento o la debilidad dejan de ser esperables y requieren contactar al equipo?

### Caso rojo: signo de alarma directo

**Frase para decir:**

> La herida está abierta y sangra mucho; no para de sangrar.

**Clasificación esperada:** `rojo`.

**Qué debe hacer el agente:** indicar escalamiento inmediato y no convertir la respuesta en una explicación larga. El cierre debe conservar la prioridad roja aunque el paciente luego diga que se siente un poco mejor.

**Pregunta para el RAG:**

> ¿Qué indica el protocolo de esta cirugía cuando hay una herida abierta o sangrado que no se detiene?

### Caso rojo: dificultad respiratoria

**Frase para decir:**

> Me falta el aire y siento dolor en el pecho desde hace unos minutos.

**Clasificación esperada:** `rojo`.

**Qué debe hacer el agente:** recomendar atención humana inmediata. No debe sugerir esperar, automedicarse ni continuar una entrevista extensa.

**Pregunta para el RAG:**

> ¿Qué instrucciones de emergencia aparecen en el corpus para dificultad respiratoria o dolor de pecho después de una cirugía?

### Caso amarillo por ambigüedad

**Frase para decir:**

> Siento algo raro aquí abajito de la herida, pero no sé si es normal.

**Clasificación esperada:** `amarillo`, con `requires_clarification`.

**Qué debe hacer el agente:** pedir una descripción concreta: qué siente, dónde exactamente, desde cuándo, intensidad y si hay fiebre, secreción, sangrado o apertura de la herida.

**Pregunta para el RAG:**

> Para esta cirugía, ¿qué diferencias hay entre molestias esperables y señales de complicación en la zona de la herida?

## Casos por procedimiento del corpus

La carpeta del corpus contiene estos cinco grupos. Las frases son ejemplos de prueba para la demo, no afirmaciones de que cada complicación sea específica de todos los pacientes de ese grupo.

### Apendicectomía / apendicitis

**Pregunta contextual recomendada:**

> El paciente está en seguimiento después de una apendicectomía. ¿Qué cuidados de recuperación y qué señales de infección o complicación debo vigilar según las referencias recuperadas?

| Nivel | Frase de prueba | Clasificación |
|---|---|---|
| Verde | `Me siento bien después de la apendicectomía, no tengo fiebre ni dolor y la herida está normal.` | Verde |
| Amarillo | `Tengo fiebre de 37.8.` | Amarillo |
| Rojo | `La herida de la apendicectomía tiene pus y huele mal.` | Rojo |

**Pregunta de precisión para el caso amarillo:**

> ¿Desde cuándo tienes la fiebre y el enrojecimiento está aumentando o hay secreción?

**Pregunta de escalamiento para el caso rojo:**

> ¿El sangrado es abundante o tienes dificultad para respirar o sensación de desmayo mientras buscas atención?

### Colecistectomía / cholecystitis

**Pregunta contextual recomendada:**

> Después de una cirugía de vesícula, ¿qué síntomas digestivos y qué cambios en la herida requieren seguimiento o contacto urgente con el equipo?

| Nivel | Frase de prueba | Clasificación |
|---|---|---|
| Verde | `Después de la cirugía de vesícula me siento bien, no tengo dolor ni fiebre y estoy comiendo normal.` | Verde |
| Amarillo | `Tengo náusea y vomité una vez.` | Amarillo |
| Rojo | `No paro de vomitar y además tengo dolor en el pecho.` | Rojo |

**Pregunta de precisión para el caso amarillo:**

> ¿Cuántas veces has vomitado, puedes retener líquidos y desde cuándo notas la hinchazón?

### Cáncer de mama / documentos agrupados como `breast_cancer`

> El nombre de la carpeta es `breast_cancer`, pero conviene confirmar el procedimiento concreto del paciente antes de hacer una afirmación específica: el corpus puede contener documentos relacionados con distintos tratamientos.

**Pregunta contextual recomendada:**

> Para el procedimiento de este paciente relacionado con cáncer de mama, ¿qué cuidados de la herida y qué síntomas posteriores requieren seguimiento según los documentos recuperados?

| Nivel | Frase de prueba | Clasificación |
|---|---|---|
| Verde | `Me siento bien después del procedimiento, no tengo fiebre, dolor ni secreción en la herida.` | Verde |
| Amarillo | `Tengo dolor fuerte y la zona está enrojecida.` | Amarillo, salvo que el texto alcance otro umbral |
| Rojo | `La herida está abierta y sale pus con mal olor.` | Rojo |

**Pregunta de precisión para el caso amarillo:**

> ¿Qué intensidad tiene el dolor del cero al diez, desde cuándo empezó y el enrojecimiento está creciendo?

### Cirugía colorrectal

**Pregunta contextual recomendada:**

> Después de una cirugía colorrectal, ¿qué cambios en el dolor, la herida, el vómito o la recuperación intestinal aparecen como señales de alarma en el corpus?

| Nivel | Frase de prueba | Clasificación |
|---|---|---|
| Verde | `Estoy bien después de la cirugía colorrectal, no tengo dolor ni fiebre y la herida está normal.` | Verde |
| Amarillo | `Tengo dolor moderado y náusea.` | Amarillo |
| Rojo | `Tengo vómito persistente, la herida se abrió y sangra mucho.` | Rojo |

**Pregunta de precisión para el caso amarillo:**

> ¿Puedes mantener líquidos, desde cuándo tienes la náusea y el dolor está aumentando?

### Reemplazo articular total

**Pregunta contextual recomendada:**

> Después de un reemplazo articular, ¿qué dolor, inflamación, debilidad o cambios en la pierna requieren seguimiento, y cuáles exigen atención inmediata?

| Nivel | Frase de prueba | Clasificación |
|---|---|---|
| Verde | `Después del reemplazo de cadera me siento bien, no tengo fiebre ni dolor importante y puedo moverme como me indicaron.` | Verde |
| Amarillo | `La pierna está hinchada y me siento mareado.` | Amarillo |
| Rojo | `Me falta el aire y tengo dolor en el pecho después del reemplazo de cadera.` | Rojo |

**Pregunta de precisión para el caso amarillo:**

> ¿La hinchazón apareció de repente, está aumentando y puedes apoyar la pierna como te indicaron?

## Casos que conviene evitar durante la demo

### No separar el número del síntoma

Evita decir:

> Me siento con calor... no sé... ¿treinta y nueve algo?

Es preferible decir:

> Tengo fiebre de 39 grados desde esta mañana.

La lógica actual busca el valor numérico en la misma cláusula que la palabra `fiebre`, `temperatura` o `dolor`. El habla fragmentada es una limitación conocida y puede reservarse para el Q&A.

### No usar una frase roja negada como prueba roja

Esta frase debería ser tranquilizadora y no roja:

> No veo pus, no tengo fiebre y la herida está normal.

Para demostrar un caso rojo, usa una afirmación directa:

> La herida tiene pus y huele mal.

### No confundir la etiqueta con un diagnóstico

`Rojo`, `amarillo` y `verde` son niveles de seguimiento y escalamiento de esta demo. No equivalen a un diagnóstico médico. La respuesta debe apoyarse en las referencias recuperadas y reconocer límites cuando el corpus no contiene información suficiente.

## Respuestas esperadas del agente

| Situación | Respuesta esperada |
|---|---|
| Verde | Confirmación breve, sin signos de alarma detectados, y orientación respaldada por el RAG. |
| Amarillo | Pregunta de precisión y seguimiento estrecho; no tranquilizar de forma automática. |
| Rojo | Escalamiento inmediato, instrucciones breves y claras; no prolongar la entrevista innecesariamente. |
| Ambiguo | Pedir qué siente, dónde y desde cuándo antes de descartar riesgo. |
| Pregunta fuera del corpus | Declarar que no hay evidencia suficiente y evitar inventar indicaciones. |

## Referencias internas

- Reglas de clasificación: `backend/decision/rules.py`.
- Orquestación y prompt clínico: `backend/agent/orchestrator.py`.
- Catálogo del corpus: `backend/data/corpus_catalog.json`.
- Evaluación contra el gold-set: `backend/scripts/eval_gold_set.py`.
- Interfaz de llamada: `frontend/call.html`.
