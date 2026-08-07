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
- BGE-M3 como embedding local para recuperación semántica, con fallback hash para entornos sin descarga de modelos.
- Reglas de triaje inicial para la clasificación verde, amarillo y rojo.
- Persistencia local para documentos administrados y sesiones de llamada.

## 4. Modelo usado

Gemini 1.5 Flash, porque está dentro de los modelos permitidos por la rúbrica, ofrece una ventana de contexto amplia para combinar historial, decisión y referencias del RAG, y ya está integrado con fallback local para mantener el repositorio ejecutable sin clave.

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
