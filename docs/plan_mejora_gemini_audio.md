# Plan de mejora de voz: TechSphere Voice Agent

## Problema actual

El agente de voz presenta una lectura algo robótica. La arquitectura actual ya separa las responsabilidades principales:

- **STT:** Groq Whisper transcribe el audio del paciente en el backend.
- **Razonamiento:** Gemini genera el texto de respuesta.
- **RAG:** ChromaDB recupera referencias del corpus clínico.
- **TTS actual:** el navegador lee la respuesta mediante `window.speechSynthesis`.

Esto significa que el problema de voz no exige rehacer el orquestador, el RAG ni la persistencia de sesiones. El plan debe mejorar primero el componente que realmente reproduce la respuesta.

## Objetivos

1. Lograr una voz más natural y apropiada para una conversación clínica.
2. Mantener baja la latencia entre la respuesta del agente y el inicio de la lectura.
3. Evitar una migración grande antes de la demostración.
4. Mantener respuestas breves, claras y seguras para reproducción hablada.

## Fase 1: mejorar la voz del navegador

Esta es la opción más rápida y con menor riesgo. No requiere añadir dependencias ni modificar el backend.

### Cambios propuestos

- Enumerar las voces disponibles con `speechSynthesis.getVoices()`.
- Seleccionar explícitamente una voz en español, priorizando `es-CO`, `es-MX` o `es-ES` según las voces instaladas.
- Usar una velocidad ligeramente menor, aproximadamente entre `0.94` y `0.98`, para reducir la sensación de lectura automática.
- Mantener el tono en un valor neutro y evitar cambios bruscos entre turnos.
- Cancelar la lectura anterior antes de iniciar una nueva para evitar respuestas superpuestas.
- Probar la misma frase con las voces disponibles y escoger la que tenga mejor prosodia, no solamente la que coincida con el código regional.

### Limitar el texto generado

La naturalidad también depende de la longitud de la respuesta. Para cada turno de voz, el prompt debe exigir:

- Una o dos frases cortas.
- Una sola pregunta de seguimiento cuando sea necesaria.
- Lenguaje cotidiano y empático.
- Ninguna referencia bibliográfica, etiqueta interna, puntuación, token o explicación del proceso del agente en el texto hablado.
- No repetir la misma información que ya se dijo en el turno anterior.

El detalle técnico puede seguir apareciendo en la interfaz y en las métricas, pero no debe enviarse al sintetizador de voz.

### Ventajas

- Implementación inmediata.
- Latencia prácticamente nula después de recibir el texto.
- No requiere otra API key ni otro servicio externo.
- No cambia el contrato de `CallOrchestrator` ni el modelo de sesiones.

### Limitaciones

- La calidad depende del navegador, el sistema operativo y las voces instaladas.
- La misma voz puede no estar disponible en todos los equipos.
- La medición actual del backend no incluye exactamente el instante en que comienza `speechSynthesis`; conviene medirlo también en el frontend si se desea comparar alternativas.

## Fase 2: Piper como adaptador TTS local

Si después de ajustar la voz del navegador la lectura sigue sonando artificial, la siguiente opción es integrar Piper como un componente TTS separado.

### Alcance de la integración

La integración no requiere rehacer el backend conversacional. Consistiría en:

1. Instalar Piper y una voz española adecuada.
2. Crear un servicio TTS con una interfaz simple, por ejemplo `synthesize(text) -> audio_bytes`.
3. Añadir un endpoint FastAPI que reciba o genere la respuesta hablada y devuelva un archivo WAV o el formato elegido.
4. Cambiar la función `speak()` del frontend para solicitar el audio y reproducirlo con un elemento `Audio` o un `Blob`.
5. Mantener intactos el orquestador, el RAG, la clasificación clínica y las sesiones.

### Flujo propuesto

```text
Paciente habla
    -> Groq Whisper
    -> reglas + RAG + Gemini
    -> texto breve del agente
    -> Piper local
    -> archivo de audio
    -> reproducción en el navegador
```

### Ventajas

- Sin costo por petición ni dependencia de una API externa.
- Latencia estable una vez cargado el modelo.
- Mayor control sobre la voz y el formato de audio.
- El texto y el audio permanecen bajo control del backend local.

### Limitaciones

- Requiere instalar y probar el binario y el modelo de voz.
- El resultado depende del rendimiento de la máquina donde corre el backend.
- Hay que añadir manejo de errores, formato de audio y reproducción en el frontend.
- La calidad puede variar entre voces y acentos disponibles.

## Gemini Native Audio y Live API

Gemini Native Audio puede ser interesante si el objetivo final es una conversación de audio realmente continua, con interrupciones y streaming. Sin embargo, no es la primera mejora recomendada para este repositorio:

- El flujo actual genera texto y usa la síntesis del navegador.
- `response_modalities=["AUDIO"]` introduciría un nuevo camino de entrega y reproducción de audio.
- La Live API requiere una integración orientada a WebSocket y streaming.
- Una llamada REST que genere el audio completo puede añadir latencia en vez de reducirla.

Por ello, Gemini Audio debe considerarse una migración posterior, no un ajuste rápido para la demo.

## Cuotas y nivel gratuito

Las cuotas, los nombres de modelos y la disponibilidad del nivel gratuito cambian con el tiempo y pueden depender del proyecto, la región y el tipo de cuenta. No se deben presentar como garantías cifras como “20 solicitudes diarias”, “500 solicitudes diarias” o “llamadas ilimitadas” sin verificarlas en la consola y documentación vigentes.

Tampoco se recomienda alternar múltiples API keys para evitar límites. Para la demo es más fiable reducir el número de llamadas, mantener respuestas cortas y tener un fallback local visible cuando Gemini no esté disponible.

## Recomendación final para la demo

### Ahora

1. Mantener Gemini como generador de texto.
2. Mejorar la selección explícita de voces españolas en `speechSynthesis`.
3. Ajustar velocidad y prosodia.
4. Limitar las respuestas habladas a una o dos frases.
5. Medir por separado STT, RAG + LLM y el inicio real de la reproducción.

### Si la voz sigue siendo insuficiente

1. Integrar Piper como adaptador TTS local.
2. Añadir un endpoint de audio en FastAPI.
3. Sustituir `speak()` por reproducción del audio devuelto.
4. Dejar sin cambios el orquestador, el RAG y las sesiones.

### Más adelante

Evaluar Gemini Live API únicamente si se necesita audio bidireccional en streaming, interrupciones naturales y una conversación continua. Para el flujo actual, esa migración tiene más riesgo y trabajo que las dos fases anteriores.
