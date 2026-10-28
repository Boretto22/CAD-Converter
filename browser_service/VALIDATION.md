# Validación del servicio web

Las pruebas usan el SDK MCP 2.3.0 con transporte HTTP real dentro del cliente ASGI de pruebas. El contrato actual MCP 2026-07-28 se comprueba con su sobre de metadatos y encabezados. El transporte y la autenticación son los del SDK, no una simulación del protocolo.

La autenticación de los ensayos HTTP usa un verificador de prueba inyectado exclusivamente desde los tests. La verificación JWT de producción tiene pruebas separadas con claves RSA generadas para la prueba: firma, issuer, audiencia, vencimiento y sujeto. No se habilita un modo anónimo de producción ni existe una contraseña de prueba en el servidor.

El adjunto de los tests de integración es una fixture sintética copiada al almacenamiento por un sustituto del descargador. Después, la inspección, imágenes, procesos de conversión, archivos DXF/STEP, PDF, controles, ZIP y descargas son reales. Se prueba también el descargador HTTP con respuestas controladas: redirección, archivo vacío y exceso de tamaño; no se ha usado una URL de adjunto real de ChatGPT.

Se verifican separación de propietarios, vínculos firmados manipulados o caducados, cuotas, recuperación tras reinicio y eliminación de trabajos caducados. El modelo intenta pasar rutas externas en una prueba; el servidor las sustituye por la fuente de ese usuario. No hay ejecución de código del usuario.

Pendientes externos: conversiones autenticadas en Render, inicio de sesión real del conversor, adjunto real desde ChatGPT, segunda cuenta, capacidad bajo carga y revisión pública. El equipo local no dispone de Docker; Render sí ha construido y arrancado la imagen Linux. La CI permite repetir la construcción manualmente.

El aislamiento local por usuario y trabajador no demuestra resistencia completa ante vulnerabilidades de todas las bibliotecas nativas. La imagen se ejecuta con usuario sin privilegios y necesita los límites, actualizaciones, controles de red y almacenamiento del proveedor.

Los resultados finales se guardan en `validation-results.json` sin rutas, credenciales o identificadores de cuenta. La validación de software no certifica cotas físicas ni tolerancias de fabricación.

Resultado local del 28/10/2026: **39 pruebas superadas, 0 fallos, 0 errores y 0 omitidas**. Incluye 37 pruebas del servicio web y dos del empaquetado de la base. Los dos perfiles, `free` y `full`, recorren inspección de adjunto sintético, revisión de página, DXF/PDF, bloqueo por escala desconocida, STEP de un prisma nominal definido en PDF y descarga firmada. Se comprueban los nuevos límites gratuitos y que la plantilla no incluya recursos de pago.

Con autorización expresa del usuario, el código se ha publicado y se ha creado un único servicio Render Free. El primer despliegue del 28/10/2026 está `live`: `/health` devuelve 200 y perfil `free`; la metadata OAuth devuelve 200 con el recurso exacto `/mcp`; acceder a `/mcp` sin sesión devuelve 401. La imagen Docker se ha construido y arrancado en Linux dentro del plan Free de 512 MB. Esto verifica el arranque, no la memoria de una conversión completa. OAuth real y el flujo de ChatGPT siguen pendientes de completar.

Servicio: https://engineering-cad-converter-web.onrender.com

Repositorio: https://github.com/Boretto22/CAD-Converter

El Blueprint usa `plan: free`, una instancia, Frankfurt, almacenamiento temporal sin disco y despliegues automáticos desactivados. Pasa el esquema JSON público de Render. El alta directa MCP utiliza la comprobación TCP predeterminada de la plataforma; `/health` se ha probado por HTTPS. No se han contratado discos ni otros recursos de pago. GitHub Actions solo se ejecuta manualmente. La URL proporcionada por Render se usa automáticamente si no se define `CAD_BASE_URL`; hay pruebas de esa precedencia.
