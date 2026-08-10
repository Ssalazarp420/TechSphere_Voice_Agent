# TechSphere Voice Agent

Proyecto base para un agente de voz orientado al seguimiento postoperatorio, con dos superficies principales:

- Consola de administración para gestionar conocimiento clínico
- Interfaz de llamada para iniciar conversaciones de voz

## Estructura del proyecto

- backend/: API FastAPI
- frontend/: páginas web de administración y llamada
- data/: datos del reto y documentos del corpus
- docs/: arquitectura, informe final y entregables

## Requisitos

- Python 3.11+
- pip

## Levantamiento rápido

1. Crear entorno virtual
   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate
   ```

2. Instalar dependencias
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Generar el catálogo e indexar el corpus
  ```bash
  python backend/scripts/build_knowledge_base.py
  python backend/scripts/index_corpus.py
  ```

4. Ejecutar la API
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. Abrir en el navegador
   - http://localhost:8000/admin
   - http://localhost:8000/call

## Variables de entorno

Copia .env.example a .env y ajusta los valores si vas a conectar modelos o servicios externos.

Si tu entorno no puede descargar el modelo semántico la primera vez, deja `EMBEDDING_BACKEND=auto` para que use el modelo local cuando esté disponible y caiga al hash como respaldo. Si quieres forzar el índice semántico, usa `EMBEDDING_BACKEND=sentence-transformers`.

Por defecto se usa `paraphrase-multilingual-MiniLM-L12-v2` (~470MB) en vez de BGE-M3 (~2.2GB) porque BGE-M3 puede agotar la RAM o tardar horas en equipos modestos durante la indexación. El índice ya viene pre-construido con MiniLM en `backend/data/chroma/` — no hace falta reindexar salvo que agregues documentos nuevos. Si tu máquina tiene RAM de sobra puedes forzar BGE-M3 con `EMBEDDING_MODEL=BAAI/bge-m3` en tu `.env`, pero tendrías que reindexar el corpus completo (las dimensiones de los vectores cambian).

## GitHub

Para publicar este repositorio:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<tu-usuario>/<tu-repo>.git
git push -u origin main
```

## Próximos pasos

- Integrar RAG con documentos del dataset
- Añadir voz en tiempo real (STT/TTS)
- Implementar lógica de decisión y escalamiento clínico

## Entregables

- Diagrama de arquitectura: [docs/arquitectura.md](docs/arquitectura.md)
- Informe final: [docs/informe-final.md](docs/informe-final.md)

## Estado actual

El repositorio ya incluye una primera versión funcional de las dos superficies que pide la rúbrica:

- Consola de administración para subir, listar y eliminar documentos vivos del conocimiento
- Interfaz de llamada con inicio de llamada, turnos, decisión preliminar y resumen persistido

Además, el corpus clínico ya está inventariado e indexado localmente, con trazabilidad por documento y soporte explícito para PDFs escaneados que aún no pueden procesarse sin OCR.

La capa de RAG usa ChromaDB con `paraphrase-multilingual-MiniLM-L12-v2` como embedding local por defecto (con BGE-M3 disponible como alternativa opcional para equipos con más RAM) y conserva un fallback hash para entornos sin descarga de modelos. El índice ya viene pre-construido en el repo.

## Arquitectura actual

- `backend/rag/`: inventario del corpus, extracción de texto, chunking e índice vectorial local
- `backend/admin/`: alta, baja y listado de documentos subidos desde la consola
- `backend/decision/`: reglas de triaje inicial para clasificar verde, amarillo o rojo
- `backend/agent/`: orquestación de la respuesta de llamada con referencias recuperadas
- `backend/call/`: persistencia de sesiones, turnos, métricas y resumen final
- `frontend/`: consola de administración e interfaz de llamada en navegador

## Métricas observables disponibles

Ya puedes contrastar en tiempo de ejecución:

- Documentos del corpus total, con texto y escaneados
- Cantidad de fragmentos indexados
- Documentos administrativos activos
- Turnos por llamada y referencias recuperadas
- Decisión clínica preliminar por turno
- Latencia media y p95 de los turnos de llamada
- Modelo usado por turno y cantidad de turnos atendidos por Gemini

Endpoint agregado para revisión rápida: `GET /metrics`

Para dejar un snapshot persistido antes del demo:

```bash
python backend/scripts/collect_metrics.py
```

Para verificar el flujo completo de forma local antes del demo:

```bash
python backend/scripts/smoke_test.py
```

## Nota sobre el modelo

La capa de llamada ya está preparada para usar uno de los modelos permitidos por `docs/stack-tecnico.md`. Por defecto queda lista para Gemini 1.5 Flash y, si no hay clave, cae a un fallback local para que el repo siga siendo ejecutable.

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

communications@sourcemeridian.com
