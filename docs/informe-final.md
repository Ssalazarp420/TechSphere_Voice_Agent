# Informe final

## 1. Resumen

Proyecto base para un agente de voz orientado al seguimiento postoperatorio con dos superficies funcionales:

- Consola de administración para conocimiento vivo
- Interfaz de llamada para conversación asistida

## 2. Arquitectura elegida

Ver [arquitectura.md](arquitectura.md) para el diagrama y el flujo de decisión.

## 3. Decisiones técnicas

- FastAPI como backend principal.
- ChromaDB como base vectorial local.
- `paraphrase-multilingual-MiniLM-L12-v2` como embedding local para recuperación semántica (BGE-M3 disponible como alternativa opcional para equipos con más RAM), con fallback hash para entornos sin descarga de modelos.
- Reglas de triaje inicial para la clasificación verde, amarillo y rojo.
- Persistencia local para documentos administrados y sesiones de llamada.

## 4. Modelo usado

Gemini 2.5 Flash, porque está dentro de la familia permitida por la rúbrica (Gemini, gama Flash), ofrece una ventana de contexto amplia para combinar historial, decisión y referencias del RAG, y ya está integrado con fallback local para mantener el repositorio ejecutable sin clave. Se usa esta generación puntual porque Gemini 1.5 Flash —el snapshot originalmente elegido— fue retirado por Google (toda la familia 1.5 devuelve 404 desde su descontinuación); la rúbrica (G3) exige pertenecer a una familia permitida, no a un snapshot congelado, así que la migración a la generación Flash vigente no afecta el cumplimiento de la compuerta.

## 5. Evidencia del proceso

- Exploración del dataset con los cuatro Excel.
- Inventario del corpus clínico.
- Indexación local de los PDFs con trazabilidad.
- Consola de administración en caliente.
- Persistencia de sesiones de llamada.

## 6. Métricas observables

El proyecto ya expone métricas de latencia de turnos, sesiones activas, referencias recuperadas y conteo de turnos atendidos por el modelo remoto. Falta separar STT/TTS por etapa si se decide cerrar la integración de voz nativa.

## 7. Próximos pasos

- Conectar STT/TTS
- Sustituir las reglas por la capa final de razonamiento si corresponde
- Registrar métricas de demo
