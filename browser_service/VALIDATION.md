# Validación del servicio web

Las pruebas usan el SDK MCP 2.3.0 con transporte HTTP real dentro del cliente ASGI de pruebas. El contrato actual MCP 2026-07-28 se comprueba con su sobre de metadatos y encabezados. El transporte y la autenticación son los del SDK, no una simulación del protocolo.

La autenticación de los ensayos HTTP usa un verificador de prueba inyectado exclusivamente desde los tests. La verificación JWT de producción tiene pruebas separadas con claves RSA generadas para la prueba: firma, issuer, audiencia, vencimiento y sujeto. No se habilita un modo anónimo de producción ni existe una contraseña de prueba en el servidor.

El adjunto de los tests de integración es una fixture sintética copiada al almacenamiento por un sustituto del descargador. Después, la inspección, imágenes, procesos de conversión, archivos DXF/STEP, PDF, controles, ZIP y descargas son reales. Se prueba también el descargador HTTP con respuestas controladas: redirección, archivo vacío y exceso de tamaño; no se ha usado una URL de adjunto real de ChatGPT.

Se verifican separación de propietarios, vínculos firmados manipulados o caducados, cuotas, recuperación tras reinicio y eliminación de trabajos caducados. El modelo intenta pasar rutas externas en una prueba; el servidor las sustituye por la fuente de ese usuario. No hay ejecución de código del usuario.

Pendientes externos: construcción y prueba del Docker en Linux/Render, inicio de sesión de un proveedor real, adjunto real desde ChatGPT, conexión de una segunda cuenta, capacidad bajo carga y revisión pública. El equipo de esta sesión no dispone de Docker. La CI incorpora su construcción para cuando se publique el repositorio.

El aislamiento local por usuario y trabajador no demuestra resistencia completa ante vulnerabilidades de todas las bibliotecas nativas. La imagen se ejecuta con usuario sin privilegios y necesita los límites, actualizaciones, controles de red y almacenamiento del proveedor.

Los resultados finales se guardan en `validation-results.json` sin rutas, credenciales o identificadores de cuenta. La validación de software no certifica cotas físicas ni tolerancias de fabricación.

Resultado local del 28/10/2026: **37 pruebas superadas, 0 fallos, 0 errores y 0 omitidas**. Incluye 35 pruebas del servicio web y dos del empaquetado de la base. Los dos perfiles, `free` y `full`, recorren inspección de adjunto sintético, revisión de página, DXF/PDF, bloqueo por escala desconocida, STEP de un prisma nominal definido en PDF y descarga firmada. Se comprueban los nuevos límites gratuitos y que la plantilla no incluya recursos de pago.

Render está conectado y el espacio de destino confirmado. Se ha verificado acceso a un repositorio vacío; no se ha subido código ni creado el servicio. El dominio público de identidad responde con descubrimiento OIDC y PKCE S256, pero no se ha completado OAuth real con el conversor. La guía `ACTIVAR.md` prepara los pasos restantes.

El Blueprint fija `plan: free`, una instancia, `region: frankfurt`, almacenamiento temporal sin disco y `autoDeployTrigger: "off"`. Su estructura pasa el esquema JSON público de Render consultado el 28/10/2026. La validación CLI y el despliegue siguen pendientes. Docker no está disponible en este equipo; no se ha medido el contenedor en Linux ni bajo los 512 MB de Render. Superar pruebas locales no garantiza capacidad en ese plan. GitHub Actions queda disponible solo para ejecución manual.
