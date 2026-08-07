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
- Reglas de triaje inicial para la clasificación verde, amarillo y rojo.
- Persistencia local para documentos administrados y sesiones de llamada.

## 4. Modelo usado

Pendiente de declaración final cuando se conecte el LLM permitido por la rúbrica.

## 5. Evidencia del proceso

- Exploración del dataset con los cuatro Excel.
- Inventario del corpus clínico.
- Indexación local de los PDFs con trazabilidad.
- Consola de administración en caliente.
- Persistencia de sesiones de llamada.

## 6. Métricas observables

Pendiente de completar con mediciones finales de latencia, tokens y costo cuando el LLM y la voz estén conectados.

## 7. Próximos pasos

- Conectar STT/TTS
- Sustituir las reglas por la capa final de razonamiento si corresponde
- Registrar métricas de demo
