# Decisiones de RAG y criterio de escalamiento

Documento de respaldo para las preguntas de la demo. Todo lo que aquí se
afirma está medido contra el gold-set oficial del reto
(`dataset/dataset_final.xlsx`: 160 casos, 3.991 turnos, dos capas de
dificultad) o contra el índice vectorial real del proyecto. Donde no hay
medición, se dice explícitamente.

> **Advertencia de encuadre.** Este sistema **nunca ha estado en producción**.
> No hay usuarios reales, ni volumen, ni periodo de operación. Si alguien
> pregunta "qué falló en producción", la respuesta honesta es que lo que
> existe es una evaluación sobre 3.991 turnos etiquetados más pruebas
> dirigidas sobre el índice. Eso es más defendible que describir una operación
> que no ocurrió.

---

## 1. Qué funcionó y qué falló en el RAG con información clínica ambigua

Medición hecha sobre el índice real (6.234 fragmentos,
`paraphrase-multilingual-MiniLM-L12-v2`, 384 dimensiones, distancia coseno).
**Menor distancia es mejor.**

### Lo que funcionó

| Consulta | Distancia | Fragmento recuperado |
|---|---|---|
| "fiebre y pus en la herida quirúrgica" | **0,277** | Guía de infecciones postquirúrgicas |
| "dolor abdominal severo después de cirugía" | **0,263** | Cuidado del paciente quirúrgico |
| "me duele muchísimo la barriga desde la operación" | 0,347 | Sección de dolor postoperatorio |

**El lenguaje coloquial funciona bien.** "Tengo la herida caliente y roja
alrededor" (0,449) recuperó instrucciones postoperatorias de apendicectomía
que dicen literalmente *"increasing warmth or redness, fevers, or chills,
please call the office"*. El acierto ocurre **cruzando el idioma**: la
consulta va en español y el documento está en inglés. Es mérito del modelo
multilingüe y es un resultado genuino que vale la pena mostrar.

### Lo que falló

**a) El término técnico falla donde el coloquial acierta.** "Signos de
infección de sitio operatorio" (0,466) recuperó un documento sobre
**vacunación contra el cáncer de cuello uterino**. La jerga clínica está peor
representada en el corpus que la descripción de paciente. Es contraintuitivo y
conviene contarlo, porque demuestra que se evaluó de verdad.

**b) El corpus es heterogéneo.** Contiene documentos de cáncer cervical y de
colon mezclados con guías postoperatorias. Consultas legítimas arrastran
material de otra especialidad.

**c) El lenguaje ambiguo no recupera nada útil.** "Me siento maluca" da 0,673,
prácticamente indistinguible del ruido puro ("qué día es hoy" da 0,706).

**d) No había umbral de relevancia.** `store.search()` devolvía siempre
`limit` fragmentos sin importar la distancia, y el orquestador metía los tres
primeros en el prompt de Gemini sin filtrar. Un turno sin contenido clínico
inyectaba material irrelevante al modelo. **Corregido** — ver la sección
siguiente.

### El umbral de distancia no funcionó, y por qué importa contarlo

La solución evidente era descartar referencias por encima de cierta distancia.
**Se implementó, se midió y se descartó.**

Sobre turnos **reales** del gold-set, la distancia del mejor fragmento es:

| | mediana | p90 | máximo |
|---|---|---|---|
| Turnos de casos rojo | 0,569 | 0,703 | 0,766 |
| Turnos de casos verde | 0,512 | 0,669 | 0,794 |

Un corte en 0,60 dejaba **sin ninguna referencia al 38 % de los turnos rojo**
— justo donde más falta hace el respaldo documental.

La causa: los turnos hablados son largos y divagantes (*"Ay, no, tranquila
doctora, un poquito molesto no más, nada del otro mundo"*), y su embedding
queda lejos de cualquier fragmento limpio de una guía clínica. Las consultas
cortas y bien redactadas con las que se probó al principio no eran
representativas.

Y lo decisivo: **el ruido puro (0,706) cae dentro del rango de los turnos rojo
legítimos (hasta 0,766)**. La distancia por sí sola no separa señal de ruido.

### La solución que sí funcionó

Se omite la búsqueda cuando el motor de reglas indica que el turno no tiene
contenido clínico: decisión **verde**, sin ninguna bandera, y sin cifra de
dolor ni de temperatura.

La condición se escribe explícita en lugar de reutilizar
`requires_clarification`, que responde a otra pregunta: un "todo bien, sin
dolor" es tranquilidad explícita —no requiere aclaración— pero tampoco tiene
nada que buscar en el corpus.

**Resultado medido sobre los 960 turnos de paciente del gold-set:**

| Turno | Conserva RAG | Omite |
|---|---|---|
| rojo | **100 %** | 0 % |
| amarillo | **100 %** | 0 % |
| verde | 11 % | 89 % |

Ningún turno con señal clínica pierde su respaldo documental. Los que se
omiten son saludos, cortesías y preguntas al agente. Efecto secundario útil:
esos turnos ahorran la búsqueda vectorial completa.

### Hallazgo colateral: el enrojecimiento en diminutivo

Al implementar el filtro se vio que "tengo la herida un poco roja" quedaba en
verde sin banderas y por tanto perdía también su RAG. La causa era una laguna
de palabras clave: solo existían `enrojecimiento`, `enrojecida` y `colorada`.

Contando el gold-set, esas tres cubren **94 menciones** y quedaban fuera
**171**:

| Término | Menciones |
|---|---|
| rojita | 45 |
| rojo | 40 |
| roja | 32 |
| rojito | 32 |
| rojez | 22 |

Se perdían **dos de cada tres menciones** de un signo clásico de infección de
sitio operatorio.

Se implementó como patrón con delimitadores de palabra y no como palabra
clave, porque el emparejamiento de claves es por subcadena y "roja" casa
dentro de apellidos como "Rojas".

**Efecto en el gold-set:**

| | Capa limpia | Capa ruidosa |
|---|---|---|
| **rojo → verde** (el error más grave) | 2 → **0** | 1 → **0** |
| amarillo acertado | 17 → **22** | 16 → **20** |
| amarillo → verde | 6 → **1** | 6 → **2** |
| Recall de rojo | 0,75 (igual) | 0,667 (igual) |
| Accuracy | 0,506 → 0,500 | 0,419 (igual) |
| verde → amarillo | 60 → 66 | 72 → 76 |

**La accuracy no mejora, pero el perfil de error se vuelve más seguro:**
ningún caso rojo se clasifica ya como verde. El costo son 6 y 4 casos verdes
que pasan a amarillo, lo que solo significa una pregunta de seguimiento de
más.

---

## 2. Cómo se definió el criterio de escalamiento a un humano

**El punto que conviene subrayar: la decisión no la toma Gemini.** La toma
`backend/decision/rules.py`, un motor determinista y auditable. Gemini recibe
la decisión ya tomada y solo redacta cómo comunicarla al paciente.

Eso significa que la decisión clínica es **reproducible**: el mismo texto
produce siempre la misma etiqueta, y se puede auditar caso por caso.

### El sistema de puntaje

| Señal | Puntos |
|---|---|
| Bandera roja (pus, sangrado abundante, dificultad respiratoria, herida abierta…) | **+3** |
| Temperatura ≥ 38 °C | **+3** |
| Dolor ≥ 8/10 | +2 |
| Banderas amarillas concurrentes | +1 cada una, **tope +3** |
| Temperatura 37,5–38 °C | +1 |
| Dolor 6–7,9 | +1 |
| Lenguaje ambiguo sin síntoma identificable | +1 |

**Umbrales:** ≥ 3 → **rojo** (escalamiento inmediato) · 1–2 → **amarillo**
(seguimiento estrecho) · 0 → **verde**

### Las cuatro decisiones de diseño defendibles

**1. Asimetría clínica deliberada.** El falso negativo es la falla
catastrófica; el falso positivo solo cuesta una revisión de más. Por eso una
sola bandera roja basta para escalar, sin necesidad de acumular otras señales.

**2. Los síntomas concurrentes suman.** Antes, cualquier cantidad de síntomas
amarillos sumaba +1: un paciente con un síntoma puntuaba igual que uno con
cinco simultáneos (fiebre, escalofríos, enrojecimiento, poco apetito, mal
dormir). La evaluación mostró casos rojo reales que nunca alcanzaban el umbral
porque cada síntoma aislado era "solo amarillo". El tope de +3 evita que una
lista larga de molestias leves dispare un rojo automático.

**3. La ambigüedad no es tranquilidad.** Si el paciente describe algo con
lenguaje vago o regional que ninguna regla captura, y no se muestra
explícitamente tranquilo, se marca amarillo. Obliga a indagar en vez de
tranquilizar por defecto.

**4. La decisión se toma sobre toda la llamada, no sobre el último turno.** El
resumen usa la decisión **más severa** vista en cualquier punto
(`max` por severidad). Si apareció una señal de alarma en el minuto 2, sigue
vigente aunque el paciente suene tranquilo en el minuto 8. Una señal de alarma
no se "olvida" porque el paciente se calme después.

### Respaldo cuantitativo

| | Capa limpia | Capa ruidosa |
|---|---|---|
| Recall de rojo | **0,75** | **0,667** |
| Casos rojo clasificados verde | **0** | **0** |

Medido sobre 160 casos del gold-set oficial. El punto de partida era 0,42 y
0,33.

### Limitaciones conocidas

Quedan **3 y 4 casos rojo** sin detectar. Todos comparten un patrón: pacientes
que minimizan verbalmente ("un poquito molesto", "nada del otro mundo", "uno
aguanta") sin dar cifras ni nombrar síntomas reconocibles. Ahí un motor de
palabras clave se queda corto; haría falta llevar el modelo generativo también
a la decisión, no solo a la respuesta.

**Sobre-triaje.** 66 y 76 casos verdes se clasifican como amarillo. Es la
consecuencia directa de la asimetría elegida y no se corrigió a propósito:
reducirlo empuja hacia el falso negativo, que es el error que este sistema
prioriza evitar.

---

## 3. El historial del paciente: dónde se usa y dónde no

### Dónde se usa hoy

**Identidad conversacional.** El saludo inicial menciona nombre y
procedimiento en vez de ser genérico.

**Un bloque en el prompt de Gemini** con nombre, procedimiento, fecha de
cirugía, edad y comorbilidades, instruyendo al modelo a interpretar los
síntomas en contexto y a no volver a preguntar lo que ya sabe.

### Dónde NO se usa

**El motor de triaje no conoce al paciente en absoluto.** `rules.py` no recibe
edad, comorbilidades, procedimiento ni días de postoperatorio.

Consecuencia: la decisión rojo/amarillo/verde es **idéntica** para un paciente
de 25 años sin antecedentes y para uno de 80 años diabético que reporten
exactamente los mismos síntomas. Clínicamente eso no se sostiene.

**Ésta es la limitación más honesta y más valiosa que se puede declarar**, y
es donde está la siguiente mejora del sistema.

### Qué dicen los datos

Perfil del dataset: 40 pacientes, 5 procedimientos (8 cada uno), 7
comorbilidades distintas, edades de 16 a 82 años.

**El día postoperatorio sí lleva señal:**

| Día | rojo | amarillo | verde |
|---|---|---|---|
| 1 | **0 %** | 7,5 % | 92,5 % |
| 3 | **0 %** | 30 % | 70 % |
| 7 | **15 %** | 25 % | 60 % |
| 14 | **15 %** | 0 % | 85 % |

Ningún caso rojo antes del día 7, coherente con que una infección de sitio
operatorio no aparece a las 24 horas.

**Las comorbilidades tienen la señal invertida:**

| | rojo |
|---|---|
| 0 comorbilidades | **12,5 %** |
| 1 comorbilidad | 5 % |
| 2 comorbilidades | **0 %** |
| Con diabetes | **0 %** |

Esto contradice la clínica, y la explicación es que el dataset es **sintético**
(Synthea): las complicaciones se generaron sin condicionarlas a las
comorbilidades.

**Implicación para el plan:** una regla del tipo "bajar el umbral en
diabéticos" es clínicamente correcta pero **el gold-set dirá que empeora**.
Ajustar pesos contra estos números sería aprender ruido invertido.

> **Cautela estadística.** Solo hay 16 casos rojo en la capa limpia. Los
> porcentajes por subgrupo se calculan sobre muestras de 32 a 80 casos: son
> orientativos, no concluyentes.

### Plan de implementación

| Fase | Contenido | ¿Validable con el gold-set? |
|---|---|---|
| **0** ✅ | Habilitar la medición: `classify_report(text, patient_context=None)` y unir el eval con `paciente_id` + `dia_postop`, columnas que ya existen en el Excel | Prerrequisito |
| **1** ✅ | Días de postoperatorio: descontar un punto a las señales blandas en la ventana temprana | **Sí — implementada, ver abajo** |
| **2** | Comorbilidades y edad: diabetes y EPOC bajan el umbral ante signos de infección. Justificar clínicamente, **no ajustar contra el gold-set**. Dejar tras bandera `ENABLE_PATIENT_RISK_RULES=false` | **No — el dataset la contradice** |
| **3** | Procedimiento → filtrado del RAG. Requiere un mapeo explícito de los 5 procedimientos a las categorías del corpus, porque `modulo_synthea` no coincide 1:1 con los nombres de carpeta | Parcialmente |

### Resultado de las fases 0 y 1 (implementadas)

El puntaje se separa en señales **duras** (signo de alarma, fiebre ≥ 38, dolor
severo) y **blandas** (banderas amarillas, febrícula, dolor moderado, lenguaje
ambiguo). En la ventana temprana se descuenta un punto, y **solo de las
blandas**: una fiebre de 39 o un drenaje purulento en el día 2 siguen
escalando igual, porque son anómalos cualquier día.

| | Capa limpia | Capa ruidosa |
|---|---|---|
| **Accuracy** | 0,500 → **0,594** | 0,419 → **0,531** |
| Recall de rojo | 0,75 (igual) | 0,667 (igual) |
| rojo → verde | 0 (igual) | 0 (igual) |
| verde → amarillo | 66 → **49** | 76 → **57** |
| amarillo → verde | 1 → 3 | 2 → 3 |

La accuracy sube ~9 y ~11 puntos atacando el sobre-triaje, sin tocar el recall
de rojo ni reintroducir el error `rojo → verde`.

**Sobre la ventana elegida.** Se probaron tres. Extenderla al día 3 da mejor
accuracy (0,650 / 0,600) pero hace que **se escapen 8 casos amarillo más**
(`amarillo → verde` pasa de 3 a 11): el día 3 es justo donde la etiqueta real
tiene más amarillos (30 %). Se eligió la ventana conservadora porque el
criterio declarado del proyecto es que el falso negativo es la falla grave, y
tranquilizar a quien necesitaba seguimiento estrecho lo es. La constante
`EARLY_POSTOP_DAYS` deja la decisión explícita y revisable.

**Nota para la demo.** Los pacientes del dataset tienen cirugías de hace meses
(83, 238 y 108 días), así que la ventana temprana no se activa con ellos y el
comportamiento en vivo es idéntico al anterior. El cambio es seguro, pero no
se verá salvo que se use un paciente con cirugía reciente.
