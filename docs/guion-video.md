# Guion de apoyo para el video — explicación técnica

Este documento reúne las explicaciones ya corregidas y verificadas contra el código, para
usarlas como base al grabar el video de demo. Cada sección tiene una versión técnica
detallada (por si te preguntan a fondo) y una versión corta para decir de corrido frente
a cámara.

Referencia cruzada: los dos diagramas de flujo están en
[arquitectura.md](arquitectura.md) — "Flujo de administración del conocimiento" y
"Flujo de llamada y decisión". El jurado toma elementos del diagrama al azar y los busca
en el código, así que esta narración sigue esos diagramas literalmente.

---

## 1. Flujo de la consola de administración (conocimiento vivo)

### Versión corta (para cámara)

> "La app tiene dos modos: uno de administración y otro de llamada de voz. En el modo
> admin subo un PDF o un TXT con conocimiento clínico nuevo. El backend, que está hecho
> en FastAPI, extrae el texto, lo divide en fragmentos, y esos fragmentos se convierten
> en vectores con un modelo de embeddings que se guardan en ChromaDB, mi base de datos
> vectorial. A partir de ahí el agente ya puede citar ese documento. Si lo elimino, borro
> esos mismos vectores de Chroma y el agente lo olvida por completo."

### Versión técnica

1. La consola (`frontend/admin.html`) sube el archivo con `POST /admin/documents`
   directamente a FastAPI (`backend/main.py`) — **FastAPI es el backend**, no un
   intermediario hacia "otro backend".
2. **Formatos aceptados: solo PDF o TXT.** (Nunca xlsx ni JSON — los `.xlsx` del reto son
   datos de simulación de pacientes/conversaciones, no se ingestan por la consola).
3. Si es PDF, se valida primero que tenga texto extraíble (`inspect_pdf`); **un PDF
   escaneado sin capa de texto se rechaza explícitamente**, porque el proyecto no tiene
   OCR todavía. Esto es un comportamiento visible y probable de demostrar en vivo.
4. `AdminDocumentService` extrae el texto (`pypdf`) y lo trocea en fragmentos de ~1200
   caracteres con solapamiento (`chunk_text`).
5. Cada fragmento se convierte en un vector con el **modelo de embeddings**
   `paraphrase-multilingual-MiniLM-L12-v2` y se guarda (`upsert`) en la colección de
   **ChromaDB** (la base de datos vectorial).
   - Precisión de vocabulario: el modelo de embeddings *vectoriza* el texto; ChromaDB lo
     *almacena y busca por similitud*; "RAG" es el nombre de la técnica completa
     (recuperar + generar), no un modelo puntual.
6. Queda agregado al **índice vectorial / base de conocimiento** del agente (evita decir
   "dataset" acá — esa palabra ya se usa para los Excel del reto, mezclarla confunde).
7. Al eliminar (`DELETE /admin/documents/{id}`), se borran esos mismos IDs de Chroma y del
   registro (`admin_registry.json`) — así el agente lo olvida de verdad, no solo dejas de
   mostrarlo en la lista.

---

## 2. Flujo de la interfaz de llamada (conversación de voz + decisión)

### Versión corta (para cámara)

> "En el modo de llamada, si hablo por micrófono, el audio primero pasa por Groq Whisper,
> que lo transcribe a texto. Ese texto lo recibe el orquestador, que es el que coordina
> todo: primero pasa el texto por un clasificador local de reglas que decide si es verde,
> amarillo o rojo según los síntomas — esa decisión no la toma la inteligencia artificial,
> la toma lógica determinística. Después busca en ChromaDB los fragmentos más relevantes
> del corpus clínico. Con la decisión y esas referencias, ahí sí llama a Gemini 3.5 Flash,
> que redacta la respuesta empática y hace la siguiente pregunta. Todo turno por turno
> queda guardado, con sus métricas de latencia, tokens y referencias usadas."

### Versión técnica

1. **Si el turno es por voz**: el audio grabado en el navegador se sube a
   `POST /call/session/turn/audio` y `GroqWhisperTranscriber` (Whisper Large V3) lo
   transcribe a texto en español. Este paso es previo al orquestador y **solo existe en
   la interfaz de voz** — si el turno es texto manual, se salta directo al paso 2.
2. El **orquestador** (`CallOrchestrator.respond()` en `backend/agent/orchestrator.py`)
   es quien dirige todo lo demás — no al revés. Su primera llamada es al **clasificador
   local** (`classify_report`, en `backend/decision/rules.py`): reglas basadas en
   keywords, con detección de negaciones ("sin fiebre" no cuenta como fiebre) y de
   lenguaje ambiguo/regional. Es determinístico, **no usa IA generativa**.
   - La clasificación tiene **tres niveles, no dos**: verde (sin alarma), amarillo
     (seguimiento estrecho), rojo (escalamiento inmediato).
3. Con el texto del paciente, el orquestador busca en **ChromaDB** (`store.search`) los
   fragmentos más relevantes del corpus clínico.
4. Con la decisión local + las referencias recuperadas, el orquestador arma el prompt y
   ahí sí llama a **Gemini 3.5 Flash**. Gemini **no decide la criticidad** — solo la
   comunica en lenguaje natural, empático, y hace una pregunta de seguimiento corta. Si
   Gemini falla (sin clave, cuota agotada), hay una plantilla local de respaldo para que
   la conversación no se caiga.
5. El resultado (texto, decisión, referencias citadas, tokens de entrada/salida,
   latencia) se persiste como turno de sesión — de ahí salen las métricas visibles en el
   panel de "Resumen de sesión": latencia P50/P95, turnos atendidos por Gemini, y el
   costo estimado.

**Punto de arquitectura para la Pregunta 2 del video** ("la decisión técnica más
relevante"): desacoplar la decisión de criticidad (reglas locales) de la generación de
lenguaje (Gemini) fue deliberado — permite auditar por qué se escaló sin depender de que
el LLM "decida bien" cada vez, y deja la puerta abierta a reemplazar las reglas por un
clasificador más sofisticado sin tocar la capa conversacional.

---

## 3. Por qué `paraphrase-multilingual-MiniLM-L12-v2` y no BGE-M3

### Versión corta (para cámara)

> "Elegimos un modelo de embeddings más liviano, MiniLM, en vez de BGE-M3, que es más
> pesado. MiniLM pesa cerca de 470MB contra 2.2GB de BGE-M3, indexa mucho más rápido en
> una laptop común y genera vectores más chicos, de 384 dimensiones en vez de 1024, lo
> que hace las búsquedas más rápidas. La calidad semántica en español es suficientemente
> buena para el caso de uso. El trade-off es honesto: BGE-M3 en benchmarks generalmente
> recupera mejor, pero priorizamos que cualquiera pueda levantar el proyecto en menos de
> 15 minutos sin quedarse sin RAM. Si alguien tiene una máquina más potente, el proyecto
> permite forzar BGE-M3 con una variable de entorno."

### Versión técnica

- **Tamaño**: ~470MB vs ~2.2GB (≈4.7x más liviano) — relevante directamente para la
  compuerta G2 (levantable en ≤15 min): indexar con BGE-M3 en un equipo modesto puede
  tardar horas.
- **RAM**: el presupuesto de hardware documentado en `docs/stack-tecnico.md` asume 8GB
  mínimos repartidos entre SO, LLM local opcional, voz y RAG. BGE-M3 solo ya usa una
  porción grande de ese presupuesto.
- **Dimensión del vector**: 384 (verificable en `GET /rag/status` →
  `embedding_dimensions`) vs 1024 de BGE-M3 — búsquedas más rápidas en Chroma, índice más
  liviano en disco (con 6229 fragmentos indexados, se nota).
- **Calidad multilingüe suficiente**: entrenado para similitud semántica ("paraphrase")
  en ~50 idiomas, entiende sinónimos médicos en español razonablemente bien.
- **El índice ya viene pre-construido con estas dimensiones** — cambiar de modelo a mitad
  de camino exige reindexar el corpus completo (las dimensiones no son compatibles entre
  sí en una misma colección de Chroma).
- **Trade-off reconocido, no ignorado**: BGE-M3 generalmente recupera mejor en
  benchmarks, especialmente en retrieval cruzado entre idiomas y documentos largos. La
  elección prioriza "que corra confiable en 15 minutos en cualquier laptop" sobre "la
  mejor precisión posible", y queda configurable (`EMBEDDING_MODEL=BAAI/bge-m3` en
  `.env`) para quien tenga más RAM disponible.

---

## 4. Qué es STT, dónde se usa y por qué Groq Whisper

### Versión corta (para cámara)

> "STT es Speech-to-Text, o sea, el paso que convierte el audio hablado del paciente en
> texto, para que el resto del sistema —que solo entiende texto— pueda procesarlo. Lo
> usamos cuando alguien habla por micrófono en la interfaz de llamada: el audio se manda
> a Groq, que corre Whisper Large V3, y devuelve la transcripción en español. Elegimos
> Groq en vez del reconocimiento nativo del navegador porque corre en el backend, así que
> funciona igual sin importar si el evaluador usa Chrome, Firefox o Safari, es
> extremadamente rápido —en nuestras pruebas tardó alrededor de un segundo—, y maneja
> bien el español, incluyendo acentos regionales."

### Versión técnica

- **STT = Speech-to-Text**: convierte audio hablado en texto. Es el primer eslabón de la
  cadena cuando el turno llega por voz, antes de tocar al orquestador.
- **Dónde se usa**: al pulsar "Usar micrófono" en `frontend/call.html`, el navegador graba
  el audio (`MediaRecorder`) y lo envía a `POST /call/session/turn/audio`. Ahí,
  `backend/stt/service.py` (`GroqWhisperTranscriber`) llama a la API de Groq (modelo
  `whisper-large-v3`), que devuelve el texto transcrito. Ese texto sigue exactamente el
  mismo camino que un turno escrito a mano.
- **Por qué Groq Whisper y no el reconocimiento nativo del navegador (Web Speech API)**:
  - Web Speech API solo funciona de forma confiable en Chrome/Edge, no en
    Safari/Firefox, y no da control sobre qué modelo transcribe.
  - Corre en el **backend**, no en el cliente: el resultado no depende del navegador ni
    del sistema operativo de quien evalúa.
  - **Latencia muy baja**: en la prueba real documentada en el informe final, la
    transcripción tardó ~1 segundo, una fracción de lo que toma después el paso de
    RAG+Gemini (~2 segundos) — relevante porque la rúbrica evalúa la latencia total de la
    conversación.
  - Buena calidad en español, incluyendo acentos regionales — coherente con el requisito
    del reto de pacientes colombianos.
  - Gratis en su nivel de entrada, y es un **proveedor distinto a Gemini**: si Gemini
    tiene un problema de cuota o de red, la transcripción sigue funcionando, y viceversa.
  - `GROQ_STT_LANGUAGE=es` está fijado explícitamente (no autodetección), porque el
    idioma del paciente ya se conoce y un turno corto es más fácil de transcribir mal si
    el modelo tiene que adivinar el idioma primero.
