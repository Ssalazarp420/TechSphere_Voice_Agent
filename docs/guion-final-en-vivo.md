# Guion para la sesión en vivo de finalistas (5 min demo + 10 min Q&A)

Este documento es distinto de [`guion-video.md`](guion-video.md) (ese es para el video
pregrabado con las dos preguntas de cierre). Este es para la sesión en vivo del sábado:
formato anunciado por Source Meridian a los finalistas — 5 minutos de demo, 10 minutos de
preguntas de un jurado de expertos que **pide explícitamente** oír errores, cambios de
plan y casi-fallas, no solo ver la app funcionando.

El protocolo de evaluación en vivo (§7 de `rubrica-evaluacion.md`) ya anticipa el formato:
preguntas con respuesta conocida contra el corpus, escenarios de decisión interpretados
por el jurado, entradas adversas, y una prueba de conocimiento vivo con material que el
agente no ha visto. Este guion se prepara para eso, no solo para un demo lineal.

---

## 1. Demo cronometrado (5:00)

**Antes de empezar:** confirmar billing activo en Google AI Studio (riesgo operativo ya
documentado: cuota gratuita de Gemini son 20 requests/día, se agota a media demo). Tener
listo un documento de prueba que no esté en `dataset/textos/` para la prueba de
conocimiento vivo (punto 4).

| Tiempo | Qué hacer | Qué decir |
|---|---|---|
| 0:00–0:25 | Pantalla en `frontend/call.html` | Una frase: qué es el agente, a quién sirve, por qué voz y no chat (seguimiento postoperatorio real es por teléfono, no por app). |
| 0:25–1:15 | Elegir un paciente del selector (identidad + procedimiento) → Iniciar llamada | El saludo sale personalizado y hablado — mencionar en una frase que el sistema conoce quién es el paciente y de qué cirugía, dato que **antes no existía en el flujo** (evitar detalle técnico aquí, solo el resultado). |
| 1:15–2:45 | Turno de síntomas por voz. **Usar una frase clara y directa, no fragmentada** (ver nota abajo) | Mientras responde: señalar que la respuesta cabe en ~12 segundos de voz — a propósito, porque una llamada real no puede sonar a lectura de manual. |
| 2:45–3:30 | Mostrar el panel de resumen actualizado: nivel de dolor, temperatura, síntomas, prioridad de escalamiento | Una frase: esto es lo que un enfermero vería después, no solo la transcripción cruda. |
| 3:30–4:15 | Cerrar la llamada → el agente dice el mensaje de cierre en voz, con próximos pasos concretos según la clasificación | Señalar que el cierre cambia según rojo/amarillo/verde — no es un "gracias, adiós" genérico. |
| 4:15–5:00 | Cambiar a consola admin → subir el documento de prueba (fuera de cualquier corpus) → mencionar que al eliminarlo el agente lo olvida (no hace falta demostrar el ciclo completo si el tiempo aprieta, con mostrarlo una vez alcanza) | Cierre: una frase de por qué esto importa (conocimiento vivo, no estático). |

**Nota sobre qué frase de síntomas usar en vivo:** el eval contra el gold-set oficial
(ver `backend/scripts/eval_gold_set.py`) mostró que el motor de decisión pierde precisión
con habla muy fragmentada y con el número del síntoma en una cláusula distinta de la
palabra clave ("me sentí con calor... no sé, ¿39 algo?"). Para el demo en vivo, decir el
síntoma de forma clara y directa ("tengo fiebre de 38.5 y la herida está enrojecida") —
no es hacer trampa, es la misma lógica de no demostrar un auto nuevo en terreno que ni el
fabricante recomienda. La fragmentación conversacional real es precisamente uno de los
temas fuertes para la Pregunta 2 del Q&A (ver más abajo), así que se guarda para ahí, no
para el demo.

---

## 2. Si el jurado quiere manejar el demo ellos mismos

El protocolo dice que prueban con sus propios insumos, no solo ven tu guion. Estar listo
para que:

- **Pidan un saludo + pregunta trivial en vivo** (esto es literalmente la compuerta G4) —
  sin preparación especial, ya funciona.
- **Digan una frase ambigua o fragmentada a propósito** para ver qué pasa. Si el sistema
  responde con una pregunta de precisión en vez de decidir en falso, eso es lo esperado
  (`requires_clarification`) — señalarlo como comportamiento intencional, no como falla,
  si el resultado es razonable. Si falla de verdad (clasifica mal), es la oportunidad
  perfecta para conectar con la Pregunta 2 del Q&A: "de hecho, esto es exactamente lo que
  encontramos al evaluar contra el dataset oficial del reto esta semana...".
- **Intenten inyección de prompt** ("ignora tus instrucciones anteriores y...", "actúa
  como un asistente sin restricciones"). El prompt ya delimita el turno del paciente como
  dato, no como instrucción (`backend/agent/orchestrator.py::_build_prompt`) — vale la
  pena probarlo uno mismo antes del sábado para tener la respuesta real memorizada, no
  solo la intención de diseño.
- **Suban o pidan subir un documento propio** para la prueba de conocimiento vivo (G5) —
  confirmar que el flujo admin funciona con un archivo que el jurado mismo aporte, no solo
  el que se preparó de antemano.

---

## 3. Banco de "errores y casi-fallas" para el Q&A

El jurado pide esto explícitamente — tenerlo memorizado, no leído. Ordenado de más
reciente (más fuerte, porque muestra rigor de esta semana) a más antiguo:

### El más fuerte: el motor de decisión fallaba 75% de los casos rojo reales

Se construyó un script de eval (`backend/scripts/eval_gold_set.py`) contra el gold-set
oficial del reto (`dataset_final.xlsx`, 3.991 turnos reales etiquetados). Resultado
inicial: **25% de recall en rojo** — de 12 casos que debían escalar, el sistema solo
detectaba 3. Causa raíz, no ajuste cosmético: un bug de negación (`"no veo pus"` se
clasificaba como rojo porque la lista de negación no cubría "no veo", solo frases fijas
como "no tengo") y una extracción numérica que exigía que el valor apareciera casi pegado
a la palabra clave, sin tolerar habla natural fragmentada ("el dolor está como en un 5").
Después de corregir ambos: **recall de rojo subió a 41.7%**, accuracy general de 40.6% a
50%. Sigue habiendo un techo real: cuando el paciente dice el número en una oración
distinta de la palabra clave del síntoma, un motor de reglas no lo captura — cerrar esa
brecha necesitaría que el LLM ayude a extraer los valores clínicos de la conversación
completa, no que las reglas los busquen turno por turno. Se documenta como limitación
conocida, no como algo resuelto.

*Por qué contar esto en vez de esconderlo*: es la respuesta perfecta a "cuéntanos un
error" — tiene causa raíz concreta, corrección medible con números de antes/después, y
una limitación honesta que queda. Es evidencia de que el proceso de evaluación es real
(criterio de "proceso y buenas prácticas"), no solo un README bien escrito.

### El resumen de la llamada podía contradecir sus propias métricas

Al construir el punto anterior se encontró que el resumen final de la llamada tomaba la
decisión del **último turno únicamente**, no la más severa de toda la conversación. Si
aparecía una bandera roja a mitad de la llamada pero el paciente sonaba tranquilo al
final, el mensaje de cierre podía decir "no veo señales de alarma" mientras
`metrics.escalation_required` internamente decía `true` — inconsistencia que el jurado
explícitamente penaliza ("métricas inconsistentes con los logs"). Se corrigió para tomar
la decisión más severa de toda la sesión.

### Las migraciones forzadas de Gemini

`gemini-1.5-flash` (el modelo originalmente permitido por nombre) fue retirado por
Google durante la ventana de construcción del reto — no una vez, sino en cadena, forzando
saltar de 1.5 a 2.5 y finalmente a 3.5 Flash. Los propios organizadores enmendaron la
regla el 7 de agosto (antes de que el equipo empezara a construir) de "un modelo puntual"
a "una familia de modelos", con la razón explícita de que "los modelos vencen, las
familias no" — se disclosed proactivamente a los organizadores. Punto de aprendizaje: no
anclar la arquitectura a un nombre de modelo específico cuando el proveedor controla su
ciclo de vida.

### BGE-M3 abandonado por agotamiento de RAM, y el bug de `accelerate`

Se evaluó BGE-M3 como modelo de embeddings por su mejor desempeño multilingüe, pero
agotaba la RAM disponible. Se cambió a `paraphrase-multilingual-MiniLM-L12-v2` (384
dimensiones). Aparte, un error de `Cannot copy out of meta tensor` en
`sentence-transformers` costó tiempo de debugging hasta encontrar que la causa era tener
`accelerate` instalado — desinstalarlo lo resolvió, y quedó documentado en
`requirements.txt` para que nadie lo reinstale sin saber por qué.

### El fallback verboso escondía qué se estaba evaluando realmente

Cuando se agotaba la cuota de Gemini, la plantilla local de respaldo concatenaba 4 piezas
de texto y podía sonar a lectura de manual en vez de conversación. Es posible que algunos
jueces de la ronda general hayan evaluado ese fallback sin saberlo, no a Gemini
directamente — lo cual también explica por qué la verbosidad se atacó primero en el plan
de mejoras: no es solo un tema de puntaje, es un tema de qué se está evaluando en
realidad.

---

## 4. Preparación específica por tipo de prueba del protocolo

**Preguntas con respuesta conocida contra el corpus** — tener 2-3 preguntas propias ya
verificadas contra el corpus (`dataset/textos/`) con la respuesta esperada en mente, para
poder juzgar en el momento si la respuesta del agente es correcta o se está improvisando.

**Escenarios de decisión interpretados por el jurado** — la asimetría clínica es el
principio rector: ante cualquier ambigüedad, el sistema debe indagar antes que
tranquilizar (`requires_clarification`). Si el jurado da un escenario límite y el sistema
pide precisión en vez de decidir en falso, eso es el comportamiento correcto — decirlo así
si preguntan por qué no respondió directo.

**Entradas adversas** — probar la inyección de prompt uno mismo antes del sábado (ver
sección 2) para tener la respuesta real, no solo la intención de diseño.

**Prueba de conocimiento vivo** — tener listo un documento de prueba fuera de cualquier
corpus (PDF o TXT, con texto extraíble — el sistema rechaza PDFs escaneados sin capa de
texto, es un comportamiento a propósito, no una falla si sale a relucir).

---

## 5. Costo por llamada (para el pitch de negocio)

El dato ya existe en `GET /metrics` (`backend/llm/pricing.py`), separado por costo de LLM
y costo de STT. Antes del sábado: correr una llamada de prueba completa, anotar el número
real que devuelve el endpoint, y llevarlo memorizado — no improvisado — para cuando
pregunten por viabilidad comercial (Pregunta 1 del video ya cubre el argumento de negocio
en general; en vivo puede pedirse el número concreto).
