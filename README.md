# TechSphere Voice Agent

Proyecto base para un agente de voz orientado al seguimiento postoperatorio, con dos superficies principales:

- Consola de administración para gestionar conocimiento clínico
- Interfaz de llamada para iniciar conversaciones de voz

# URL al video de explicacion
- https://youtu.be/F3BupdamrUs

## El diagrama esta en "docs/arquitectura.md"
## El informe final esta en "docs/informe_final.md"

## Estructura del proyecto

- backend/: API FastAPI
- frontend/: páginas web de administración y llamada
- data/: datos del reto y documentos del corpus
- docs/: arquitectura, informe final y entregables

## Frontend y sistema visual

Las dos superficies web (`frontend/admin.html` y `frontend/call.html`) comparten un
único sistema de diseño en **`frontend/assets/app.css`**, servido desde el propio
repositorio. No hay CDN, no hay fuentes remotas y no hay paso de build: las páginas se
ven igual sin conexión a internet, algo necesario para la demo en vivo. Tampoco agrega
una dependencia Python ni cambia `requirements.txt`.

`app.css` define tokens para superficies, bordes, texto, acento, semáforo de triaje,
radios, espaciado, tipografía y sombras; encima de esos tokens viven los componentes
(tarjeta, botón, campo, badge, aviso, métrica, burbuja de chat, lista de documentos).
La regla de trabajo es que **todo valor visual sale de un token**: si hace falta un
número que no está en la escala, casi siempre lo correcto es usar el escalón más
cercano en vez de añadir un valor nuevo.

Por qué un CSS propio y no Tailwind: la versión anterior tenía las dos cosas a la vez
—un bloque `<style>` copiado en cada página más utilidades Tailwind sobre el mismo
HTML— y competían por las mismas propiedades, así que el resultado dependía de cuál
regla ganara. Los tokens duplicados además habían derivado entre archivos (`--accent`
era `#4ed6a7` en una página y `#3ddc97` en la otra), por lo que las dos superficies no
combinaban ni entre sí.

Para que el navegador alcance ese CSS, `backend/main.py` monta `frontend/assets` en
`/assets` con `StaticFiles`. Sin ese montaje las páginas cargarían sin estilos: las
rutas `/admin` y `/call` devuelven un `FileResponse` de un único archivo y no alcanzan
a los recursos que ese HTML referencia.

Los IDs, endpoints y flujos JavaScript existentes se conservaron, por lo que el cambio
es visual y no altera la lógica de voz, RAG o triaje.

## Requisitos

- **Python 3.11, 3.12 o 3.13.** Evita 3.14: al momento de escribir esto es una versión
  muy reciente y `tokenizers` (dependencia de `transformers`/`sentence-transformers`)
  todavía no publica wheel precompilado para ella, así que `pip install` intenta
  compilarlo desde código Rust y falla si no tienes el toolchain de Rust/Cargo
  instalado. `requirements.txt` pinnea versiones exactas del stack de embeddings
  (`transformers==4.57.6`, `tokenizers==0.22.2`, `torch==2.13.0`, entre otras)
  porque un rango abierto permitía que pip resolviera combinaciones distintas en
  cada máquina — la causa de que el mismo código funcionara en un entorno y
  fallara en otro con el error "Cannot copy out of meta tensor". Esas versiones
  sí traen wheel para 3.11-3.13; la versión de Python la eliges tú al crear el
  entorno. No añadas `accelerate`: no es dependencia del proyecto y es la causa
  más probable de ese mismo error (ver `backend/rag/embeddings.py`).
- pip (o [`uv`](https://docs.astral.sh/uv/), más rápido y con gestión de versiones de
  Python integrada — así se probó este repo)

## Levantamiento rápido

1. Crear entorno virtual con una versión de Python soportada
   ```bash
   # Opción A: venv estándar (usa el intérprete de Python que tengas apuntando a 3.11-3.13)
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate

   # Opción B: uv (descarga automáticamente Python 3.12 si no lo tienes)
   uv venv --python 3.12 .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   ```

2. Instalar dependencias
   ```bash
   pip install -r requirements.txt
   # o, con uv:
   uv pip install --python .venv/bin/python -r requirements.txt
   ```

3. Configurar las claves
   ```bash
   cp .env.example .env
   ```
   Edita `.env` y pon tus claves de Gemini y Groq. Sin ellas el agente arranca
   pero no puede generar respuestas ni transcribir audio. Ver
   [Variables de entorno](#variables-de-entorno) para el detalle de cada valor.

4. Generar el catálogo e indexar el corpus — **obligatorio en un clon nuevo**
   ```bash
   python backend/scripts/build_knowledge_base.py
   python backend/scripts/index_corpus.py
   ```
   Construye `backend/data/corpus_catalog.json` y el índice vectorial en
   `backend/data/chroma/` (unos 6234 fragmentos con
   `paraphrase-multilingual-MiniLM-L12-v2`) a partir de los 107 documentos de
   `dataset/textos/`, que sí están versionados. Tarda varios minutos y baja el
   modelo de embeddings la primera vez.

   Estos artefactos **no** se versionan, a propósito: se reconstruyen desde
   fuentes que ya están en el repo, y tenerlos versionados solo causaba
   conflictos. Basta con ejecutar la app para que cambien —SQLite reescribe
   `chroma.sqlite3` con solo abrirlo— y git no sabe fusionar un binario, así
   que cualquier `git pull` quedaba bloqueado hasta descartar los cambios a
   mano. Si ya tienes el índice construido, este paso no hace falta otra vez.

5. Ejecutar la API
   ```bash
   # Desde la RAÍZ del repositorio, con el entorno virtual activado:
   uvicorn backend.main:app --reload --port 8000
   ```
   Queda escuchando en `http://127.0.0.1:8000`. Se detiene con `Ctrl+C`.

   Detalles que importan:
   - El módulo se escribe `backend.main:app` (con punto) cuando lanzas desde la
     raíz. Desde dentro de `backend/` sería `main:app` y también funciona: las
     rutas del corpus, el índice y `frontend/assets` se derivan de la ubicación
     del propio archivo (`Path(__file__).resolve().parents[1]`), no del
     directorio de trabajo. Aun así, usa la forma desde la raíz: es la que
     asumen el resto de los comandos de este README.
   - `--reload` reinicia el servidor al guardar un archivo. Cómodo para
     desarrollar, pero recarga el modelo de embeddings en cada reinicio (~14 s).
     Para una demo, omítelo.
   - Añade `--host 0.0.0.0` **solo** si necesitas abrirlo desde otro equipo de
     la red; por defecto escucha únicamente en tu máquina, que es lo que quieres
     para una demo local.
   - Si no activaste el entorno virtual, invoca su intérprete directamente:
     `.venv/bin/python -m uvicorn backend.main:app --port 8000`
     (en Windows: `.venv\Scripts\python -m uvicorn ...`).

6. Abrir en el navegador
   - http://localhost:8000/call — interfaz de llamada
   - http://localhost:8000/admin — consola de administración

   El primer turno tarda más que los siguientes: el modelo de embeddings se
   carga de forma diferida (`@lru_cache` en `get_vector_store()`), en el primer
   uso real del RAG — unos 14 s. Si vas a presentar en vivo, haz un turno de
   prueba antes de empezar para que esa carga no le toque al primero de verdad.
   El TTS de Piper sí se precalienta en el arranque, así que el servidor tarda
   un par de segundos más en levantar pero no hay silencio en el primer turno.

### Si el puerto 8000 está ocupado

`[Errno 98] Address already in use` casi siempre significa que quedó una
instancia anterior corriendo (típico tras cerrar la terminal sin `Ctrl+C`).
Para identificarla y cerrarla:

```bash
ss -ltnp | grep ':8000'      # muestra el PID que tiene el puerto
kill <PID>                   # cierre limpio
```

Alternativa: dejar la instancia vieja en paz y levantar la nueva en otro
puerto con `--port 8001`.

## Variables de entorno

Copia .env.example a .env y ajusta los valores si vas a conectar modelos o servicios externos.

Por defecto `EMBEDDING_BACKEND=sentence-transformers`: si el modelo no puede cargar, la app falla explícitamente en vez de degradar en silencio al hash. Esto es intencional — como el índice ya viene pre-construido con este modelo, un fallback silencioso a otro backend siempre termina en un error de dimensión más adelante, solo que más difícil de diagnosticar. Si necesitas correr sin poder descargar el modelo (por ejemplo, para probar la lógica de decisión sin RAG real), usa `EMBEDDING_BACKEND=hash` explícitamente y ten en cuenta que vas a necesitar reindexar el corpus completo para que vuelva a ser consistente.

Por defecto se usa `paraphrase-multilingual-MiniLM-L12-v2` (~470MB) en vez de BGE-M3 (~2.2GB) porque BGE-M3 puede agotar la RAM o tardar horas en equipos modestos durante la indexación. El índice ya viene pre-construido con MiniLM en `backend/data/chroma/` — no hace falta reindexar salvo que agregues documentos nuevos. Si tu máquina tiene RAM de sobra puedes forzar BGE-M3 con `EMBEDDING_MODEL=BAAI/bge-m3` en tu `.env`, pero tendrías que reindexar el corpus completo (las dimensiones de los vectores cambian).

## GitHub

Para publicar este repositorio:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/Ssalazarp420/TechSphere_Voice_Agent.git
git push -u origin main
```

## Próximos pasos

Los tres puntos originales de esta sección (RAG con el dataset, voz en tiempo real
STT/TTS, lógica de decisión y escalamiento) ya están implementados — ver "Estado actual"
más abajo. Lo que queda pendiente hoy es más específico:

- **Cerrar la brecha de recall en rojo del motor de decisión.** El eval contra el
  gold-set oficial (`backend/scripts/eval_gold_set.py`) subió de 25% a 41.7% de recall en
  rojo tras corregir un bug de negación y de extracción numérica, pero sigue habiendo un
  techo cuando el paciente menciona el valor clínico en una cláusula separada de la
  palabra clave del síntoma — un motor de reglas puro no lo captura de forma confiable.
- **Instrumentar la síntesis de Piper como etapa medida propia.** Al migrar el TTS del
  navegador a Piper local apareció al menos una latencia end-to-end atípica que la
  métrica actual no separa por etapa (ver `docs/informe-final.md` §7).
- Evaluar streaming de audio por WebSocket si el tiempo lo permite, en vez del flujo
  actual por turnos (grabar → detener → transcribir).

## Entregables

- Diagrama de arquitectura: [docs/arquitectura.md](docs/arquitectura.md)
- Informe final: [docs/informe-final.md](docs/informe-final.md)

## Estado actual

El repositorio ya incluye una primera versión funcional de las dos superficies que pide la rúbrica:

- Consola de administración para subir, listar y eliminar documentos vivos del conocimiento
- Interfaz de llamada con inicio de llamada, turnos, decisión preliminar y resumen persistido

Además, el corpus clínico ya está inventariado e indexado localmente, con trazabilidad por documento y soporte explícito para PDFs escaneados que aún no pueden procesarse sin OCR.

La capa de RAG usa ChromaDB con `paraphrase-multilingual-MiniLM-L12-v2` como embedding local por defecto (con BGE-M3 disponible como alternativa opcional para equipos con más RAM) y conserva un fallback hash para entornos sin descarga de modelos. El índice ya viene pre-construido en el repo.

La lógica de decisión (`backend/decision/rules.py`) no solo detecta banderas rojas/amarillas explícitas: también reconoce negaciones ("sin fiebre" no cuenta como fiebre) y lenguaje ambiguo o regional que no calza con ninguna keyword clínica (el ejemplo de este mismo README, *"me duele como aquí abajito de la axila"*) — en ese caso no asume "verde" por defecto, lo trata como señal amarilla y genera una pregunta de seguimiento concreta antes de tranquilizar al paciente. El prompt del orquestador (`backend/agent/orchestrator.py`) trata el turno del paciente explícitamente como dato a interpretar, no como instrucciones, y está probado contra intentos de inyección (pedir el system prompt, cambiar de rol, recomendar dosis peligrosas).

## Arquitectura actual

- `backend/rag/`: inventario del corpus, extracción de texto, chunking e índice vectorial local
- `backend/admin/`: alta, baja y listado de documentos subidos desde la consola
- `backend/decision/`: reglas de triaje inicial para clasificar verde, amarillo o rojo
- `backend/agent/`: orquestación de la respuesta de llamada con referencias recuperadas
- `backend/call/`: persistencia de sesiones, turnos, métricas y resumen final
- `frontend/`: consola de administración e interfaz de llamada en navegador

## Métricas observables disponibles

`GET /metrics` agrega, en vivo y a partir de las sesiones persistidas en
`backend/data/call_sessions.json`, todo lo que la rúbrica exige reportar (§5):

- **Latencia P50 y P95**, medida desde que el paciente termina de hablar hasta que
  empieza a sonar el audio del agente (`avg/p50/p95_end_to_end_latency_ms`, que suma
  la transcripción de Groq Whisper + la búsqueda RAG + la generación de Gemini). Para
  turnos de texto manual, sin STT, se reporta también `avg/p50/p95_turn_latency_ms`
  (solo RAG + LLM) por separado.
- **Tokens de entrada y salida** por turno y acumulados por llamada (`input_tokens`,
  `output_tokens`, `total_tokens`, leídos del `usage_metadata` real que devuelve Gemini,
  no estimados).
- **Invocaciones al modelo por turno**: siempre 1 (una sola llamada a Gemini por turno,
  sin reintentos) — expuesto como dato (`model_invocations`), no solo documentado en el
  código.
- **Consultas al RAG por llamada** (`rag_queries`): una búsqueda vectorial por cada
  turno del paciente que pasa por el orquestador.
- **Costo estimado por llamada** (`estimated_cost_per_call_usd`), extrapolando a precios
  de producción de Gemini Flash y Groq Whisper. Las tarifas usadas están en
  `pricing_assumptions` dentro de la misma respuesta y son configurables por variable de
  entorno (`GEMINI_INPUT_PRICE_PER_1M_USD`, `GEMINI_OUTPUT_PRICE_PER_1M_USD`,
  `GROQ_STT_PRICE_PER_MINUTE_USD`) — verifica la tarifa vigente en Google AI Studio /
  Groq Console antes de citar el número como definitivo, las tarifas cambian.
- Además: documentos del corpus (con/sin texto), fragmentos indexados, documentos
  administrativos activos, referencias recuperadas y decisión clínica por turno.

`backend/scripts/collect_metrics.py` y `GET /metrics` usan **la misma función**
(`CallSessionService.global_metrics()`) para que el número que reportes acá nunca pueda
divergir del que el jurado ve en logs — la rúbrica penaliza explícitamente esa
inconsistencia.

### Snapshot de referencia

Captura real de una tanda de 5 llamadas de verificación local (4 turnos de texto
cubriendo verde/amarillo/rojo/ambiguo regional, más 1 turno de audio real transcrito por
Groq Whisper) — no son cifras de producción con tráfico real, son la evidencia de que el
pipeline de medición funciona extremo a extremo:

| Métrica | Valor |
|---|---:|
| P50 latencia end-to-end (audio→respuesta) | 1883 ms |
| P95 latencia end-to-end | 3048 ms |
| Tokens de entrada (total / promedio por turno) | 5794 / 1159 |
| Tokens de salida (total / promedio por turno) | 420 / 84 |
| Invocaciones al modelo por turno | 1 |
| Consultas al RAG por llamada | 1 |
| Costo estimado por llamada | ~US$ 0.00035 |

Para reproducirlo (con el servidor corriendo):

```bash
python backend/scripts/collect_metrics.py
```

Para verificar el flujo completo de forma local antes del demo:

```bash
python backend/scripts/smoke_test.py
```

## Nota sobre el modelo

La capa de llamada ya está preparada para usar uno de los modelos permitidos por `docs/stack-tecnico.md` (Gemini 1.5 Flash fue retirado por Google, y Gemini 2.5 Flash dejó de estar disponible para API keys nuevas; la rúbrica exige familia, no snapshot puntual). Por defecto queda configurada con **`gemini-3.5-flash-lite`**, no con `gemini-3.5-flash`: en pruebas manuales, el free tier de `3.5 Flash` agotaba su cuota después de 2-3 interacciones, un riesgo real para una demo en vivo de 15 minutos frente a un jurado. `3.5 Flash Lite` respondió correctamente en las mismas pruebas con más margen de cuota disponible (ver `docs/bitacora-modelos-gemini.md`). El modelo se controla por variable de entorno (`GEMINI_MODEL`), así que se puede volver a `gemini-3.5-flash` sin tocar código si se activa facturación antes de la presentación. Si no hay `GEMINI_API_KEY` configurada, la app cae a un fallback local para que el repo siga siendo ejecutable.

---

## El problema

El seguimiento postoperatorio depende hoy de personal humano: es costoso, no escala y
está sujeto a errores. El paciente, mientras tanto, no tiene conocimiento médico —a veces
ni un termómetro— y describe lo que siente en lenguaje cotidiano, ambiguo y regional:

> *"Me duele como aquí abajito de la axila hace como 20 minutos."*

En paralelo, la operación clínica vive en conocimiento no estructurado —manuales,
instructivos, guías, PDFs, notas— que **cambia de versión constantemente**. El agente
debe reflejar siempre la versión vigente sin contaminarse con la anterior.

Tres cosas hacen este reto distinto de un chatbot cualquiera:

- **Es voz, no chat.** Conversación en tiempo real, con todo lo que eso implica:
  latencia, silencios incómodos, respuestas largas inviables.
- **Es salud, no e-commerce.** Cero tolerancia a alucinaciones, respuestas fundamentadas
  en el corpus clínico, y honestidad explícita cuando el agente no sabe.
- **El conocimiento es vivo, no estático.** El RAG debe poder actualizarse —aprender y
  olvidar— en caliente.

## Qué construyes

- Una conversación de voz que se adapta a las respuestas del paciente.
- Respuestas fundamentadas en una base de conocimiento clínico (RAG).
- Una consola para actualizar el conocimiento en caliente: subes un documento y el agente
  lo aprende; lo eliminas y lo olvida.
- Trazabilidad: cada respuesta clínica registra qué documento la sustenta.
- Una lógica de decisión: ¿esto amerita alertar a un humano, o no?
- Un resumen estructurado de cada llamada.

### Qué no necesitas construir

Telefonía real en producción · integración con sistemas hospitalarios reales ·
autenticación empresarial o gestión de roles · cobertura de todos los procedimientos
médicos existentes.

### Las dos superficies

Tu solución debe exponer dos superficies. Pueden ser una sola aplicación o dos; el diseño
visual no se evalúa, pero el contrato funcional sí:

| Superficie | Qué representa | Contrato funcional mínimo |
|---|---|---|
| **Consola de administración** | El back-office del producto real: gestión del conocimiento | Subir documento · listar documentos cargados · eliminar documento · indicación visible de "procesado y disponible" |
| **Interfaz de llamada** | La llamada telefónica de producción | Iniciar llamada de voz desde el navegador · hablar (micrófono) · escuchar al agente |

Puedes ofrecer además API, CLI o una carpeta que el sistema vigile e ingiera
automáticamente, pero la consola es exigida.

### Restricciones

- **El stack es abierto; el modelo, no.** Orquestación, voz, RAG y embeddings los eliges
  tú, pero el modelo de lenguaje debe ser uno de los
  [permitidos](docs/stack-tecnico.md#1-los-modelos-permitidos) — y tienes que declarar en
  tu informe cuál usaste y por qué. Mismas opciones sobre la mesa: gana la ingeniería, no
  la billetera.
- La llamada va vía **navegador/API**. No hay telefonía real.
- El agente conversa en **español**, con pacientes colombianos que usan regionalismos y
  descripciones ambiguas.
- Tu repositorio debe ser **público en GitHub**, con README y dependencias declaradas.

---

## Los datos: `dataset/`

Todos los datos del reto están en la carpeta [`dataset/`](dataset/) de este repositorio.
No hay que conectarse a nada externo para obtenerlos.

Son **datos sintéticos**. Ningún paciente, nombre, cédula, dirección o EPS corresponde a
una persona real.

| Archivo | Qué es |
|---|---|
| `dataset_final.xlsx` | **Las conversaciones.** 3.991 filas × 13 columnas: una fila es un turno, no una conversación. 40 pacientes, 160 casos (uno por paciente y día postoperatorio: 1, 3, 7 y 14), dos capas de dificultad. Incluye `label_ground_truth` con la criticidad de referencia del caso —`verde`, `amarillo` o `rojo`—, constante dentro de cada `caso_id`. |
| `trayectorias_postop_silver.xlsx` | **El cuadro clínico real de cada llamada**: dolor, fiebre, movilidad, estado de la herida, apetito y sueño, más el arquetipo de recuperación. 160 filas, una por caso. Es lo que el paciente está viviendo y el agente solo puede averiguar conversando. |
| `perfiles_clinicos_pacientes_silver_contest.xlsx` | **Perfil clínico** por paciente: procedimiento, fecha de cirugía, edad, género, comorbilidades. 40 filas. |
| `perfiles_pacientes_co.xlsx` | **Demografía colombiana** sintética: nombre, dirección, ciudad, departamento, documento y EPS. 40 filas. Se derivó de una población simulada estadounidense y se adaptó a Colombia; `adaptation_fields` lista qué campos se sustituyeron. |
| `textos/` | **El corpus clínico**: 107 documentos PDF en español e inglés —guías de práctica clínica, protocolos de recuperación, papers de complicaciones postoperatorias, planes de cuidado e instructivos para el paciente—, repartidos en cinco carpetas por escenario. Es el combustible de tu RAG. |

### Las dos capas

`capa1_limpia` son conversaciones ordenadas: el paciente responde lo que se le pregunta.
`capa2_ruidosa` es la misma conversación degradada con ruido realista —respuestas
evasivas o ambiguas, información faltante, síntomas irrelevantes, interrupciones de un
familiar—.

**Un mismo `caso_id` contiene ambas versiones de la llamada**, así que filtra por `capa`
antes de reconstruir una conversación. Los turnos de la capa 2 derivados de un turno de la
capa 1 llevan el mismo `dialogo_id` con sufijo `_c2`; los turnos insertados por un tercero
llevan `_c2_tercero`.

### Cómo se relacionan los archivos

`paciente_id` une los cuatro archivos. El join entre conversaciones y trayectorias **no
es directo**:

```
caso_id  =  "caso_" + trayectoria_id
```

Un paciente tiene un perfil clínico, un perfil demográfico y cuatro trayectorias (una por
día postoperatorio); cada trayectoria corresponde a un caso, y cada caso a una
conversación en sus dos capas.

### Antes de que empieces

- Las clases están **desbalanceadas**, como en la realidad: de los 160 casos, 123 son
  `verde`, 25 `amarillo` y 12 `rojo`.
- `comorbilidades` y `adaptation_fields` son **listas JSON dentro de una celda de texto**.
- Los cuatro `.xlsx` tienen **una sola hoja, llamada `result`**.
- En `dataset/textos/`, dos nombres de carpeta contienen espacios, hay documentos
  repetidos y un PDF de `Appendicitis/` está escaneado **sin capa de texto**.
- El material entregado **no es todo el material de evaluación**. Habrá conocimiento
  clínico que tu agente no habrá visto antes.

---

## Qué debes entregar

| # | Entregable |
|---|---|
| **01** | **Repositorio** público en GitHub, con tu implementación completa y documentación clara |
| **02** | **Diagrama** de la arquitectura de tu solución y del flujo de decisión del agente |
| **03** | **Informe final** con evidencia de tu proceso —prompts, configuraciones, capturas del demo— y la declaración explícita de qué modelo usaste y por qué lo elegiste |
| **04** | **Video**: demo funcional con grabación de pantalla, más las [dos preguntas de cierre](docs/rubrica-evaluacion.md#las-dos-preguntas-de-cierre-del-video) respondidas frente a cámara |

## Cómo se evalúa

Dos fases: **cinco compuertas eliminatorias** y una **rúbrica de 100 puntos** repartida
en seis criterios. Lo que no pasa las compuertas no se puntúa.

Entre las compuertas hay una que conviene tener presente desde el primer commit: **tu
solución debe ser levantable en 15 minutos o menos siguiendo únicamente tu README.**

El detalle completo —las cinco compuertas, los seis criterios con sus pesos, las métricas
que tu README debe reportar y las conductas que penalizan— está en
[`docs/rubrica-evaluacion.md`](docs/rubrica-evaluacion.md). Léelo antes de empezar a
construir.

## Cronograma 2026

| Fecha | Hito |
|---|---|
| **22 jul** | Live + apertura de inscripciones |
| **7 – 10 ago** | Construcción: recibes este repositorio y el material técnico, y entregas el 10 de agosto |
| **10 – 18 ago** | Revisiones y anuncio de los 3 finalistas |
| **5 sep** | Ganadores: panel de expertos y demo en vivo de los 3 finalistas, durante el evento de premiación de Tech Sphere |

---

## Licencia y avisos

El código y los datos sintéticos de este repositorio se distribuyen bajo licencia MIT
(ver [`LICENSE`](LICENSE)).

Los documentos PDF de `dataset/textos/` son obra de sus respectivos autores y editores,
conservan sus propios derechos y se incluyen únicamente como material de referencia para
el reto.

Los datos clínicos son **sintéticos y no han sido validados clínicamente**. No sirven para
ninguna finalidad clínica, diagnóstica ni asistencial fuera de este reto.

## Contacto

ssalazarp@unal.edu.co
Sebastian Salazar Perez
