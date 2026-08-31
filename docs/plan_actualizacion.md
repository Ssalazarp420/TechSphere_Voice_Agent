# Plan de Acción: Demo Tech Sphere Challenge 
**Presentación al Jurado de Source Meridian (Sábado 5 de septiembre)**

## 1. Identidad y Contexto del Paciente (Criterio 3.2)
*   **Qué cambiar:** Inyectar variables específicas como el nombre del paciente y el tipo de procedimiento al iniciar la llamada.
*   **Por qué hacerlo:** Un agente postoperatorio carece de viabilidad médica si no sabe con quién habla ni qué cirugía le practicaron. Esto da contexto real, permite rastrear historiales y hace que la demostración en vivo sea mucho más personalizada ante el jurado.
*   **Cómo implementarlo:** 
    1. Ajustar el payload de inicio de sesión en tu backend (ej. `{"nombre_paciente": "Carlos", "cirugia": "apendicectomía"}`).
    2. Pasar estas variables directamente al *System Prompt* antes de generar la primera respuesta.

## 2. Reducción de Verbosidad en Respuestas (Criterio 4.1)
*   **Qué cambiar:** Restringir las respuestas del LLM para que duren menos de 15 segundos al ser verbalizadas.
*   **Por qué hacerlo:** En tu video tuviste que cortar al bot porque hablaba demasiado. Los párrafos de contención más explicaciones funcionan en chat de texto, pero en voz suenan robóticos y arruinan la experiencia de usuario.
*   **Cómo implementarlo:** Agregar una instrucción absoluta en el prompt del sistema, como: *"CRÍTICO: Tus respuestas deben tener máximo dos oraciones cortas. Sé directo y conversacional."*

## 3. Caso de Negocio y Costos (Criterio 5.2)
*   **Qué cambiar:** Cuantificar el costo de usar el agente frente al seguimiento humano en la presentación de 5 minutos.
*   **Por qué hacerlo:** Los jurados técnicos y de negocio necesitan ver ROI (Retorno de Inversión). Si no hay números que comparen el ahorro, la solución queda como un proyecto académico y no como un producto de mercado.
*   **Cómo implementarlo:** 
    1. Calcula el costo en la nube: precio por 1K tokens de Gemini 3.5 Flash + precio de los segundos consumidos en TTS.
    2. En tu demo, proyecta una diapositiva que compare el costo de tu llamada (centavos) vs. el costo de 5 minutos de tiempo de una enfermera registrada.

## 4. Profundidad del Resumen Estructurado (Criterio 2.3)
*   **Qué cambiar:** Ampliar el JSON de salida que se genera al terminar la llamada.
*   **Por qué hacerlo:** Tu resumen actual solo arroja 3 campos. Para que la herramienta sea útil en una clínica real, el informe debe estructurar los hallazgos críticos del triaje.
*   **Cómo implementarlo:** Modificar el esquema de extracción final del LLM para incluir variables clave como: `nivel_dolor (1-10)`, `sintomas_anomalos`, `accion_tomada` y `prioridad_escalamiento`.