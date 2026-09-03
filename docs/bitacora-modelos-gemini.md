# Bitacora de modelos Gemini

Registro de pruebas realizadas en este repositorio con la API key de Google AI Studio configurada en el entorno local.

## Resumen

| Modelo | Resultado | Observacion |
|---|---|---|
| Gemini 1.5 Flash | Fallo | La llamada devolvio `404`; la familia fue retirada/no esta disponible para esta API.
| Gemini 2.5 Flash | Fallo | La prueba realizada en este proyecto fallo por disponibilidad de la API key/modelo en ese momento.
| Gemini 3.5 Flash | Funciona | Era el modelo activo y respondia correctamente, pero el free tier agotaba el limite despues de aproximadamente 2 o 3 interacciones en las pruebas manuales.
| Gemini 3.5 Flash Lite | Funciona | El catalogo de modelos de la API key lo expuso como `models/gemini-3.5-flash-lite` y una generacion minima respondio correctamente.

## Prueba de Flash Lite

- Fecha: 2026-09-02.
- Identificador usado: `gemini-3.5-flash-lite`.
- Prompt de prueba: `Responde unicamente: prueba OK`.
- Resultado: `prueba OK`.
- Tokens reportados por el SDK: 7 de entrada, 2 de salida, 9 totales.
- Conclusión: el modelo esta habilitado para la API key actual y es compatible con el SDK `google-genai` usado por la app.

## Configuracion actual

La app queda configurada con:

```env
GEMINI_MODEL=gemini-3.5-flash-lite
MODEL_NAME=gemini-3.5-flash-lite
```

El servicio conserva la configuracion por variable de entorno, por lo que se puede volver a `gemini-3.5-flash` sin cambiar codigo. Reinicia Uvicorn despues de modificar `.env`.

## Interpretacion del limite

El agotamiento tras 2 o 3 turnos no demuestra por si solo que el modelo tenga un limite de dos o tres conversaciones. Puede depender de la cuota vigente del proyecto, solicitudes por minuto, tokens consumidos, concurrencia y del estado del free tier de Google AI Studio. Flash Lite se selecciona como alternativa de menor costo/cuota mas amplia, pero sus limites exactos deben comprobarse en la pantalla **Usage** de Google AI Studio.

Esta bitacora registra resultados observados durante estas pruebas; no sustituye la tabla de cuotas y precios vigente del proveedor.
