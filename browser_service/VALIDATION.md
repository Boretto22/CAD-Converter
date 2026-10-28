# Validación del servicio web

Las pruebas usan el SDK MCP 2.3.0 con transporte HTTP real dentro del cliente ASGI de pruebas. El contrato actual MCP 2026-07-28 se comprueba con su sobre de metadatos y encabezados. El transporte y la autenticación son los del SDK, no una simulación del protocolo.

La autenticación de los ensayos HTTP usa un verificador de prueba inyectado exclusivamente desde los tests. La verificación JWT de producción tiene pruebas separadas con claves RSA generadas para la prueba: firma, issuer, audiencia, vencimiento y sujeto. No se habilita un modo anónimo de producción ni existe una contraseña de prueba en el servidor.

El adjunto de los tests de integración es una fixture sintética copiada al almacenamiento por un sustituto del descargador. Después, la inspección, imágenes, procesos de conversión, archivos DXF/STEP, PDF, controles, ZIP y descargas son reales. Se prueba también el descargador HTTP con respuestas controladas: redirección, archivo vacío y exceso de tamaño; no se ha usado una URL de adjunto real de ChatGPT.

Se verifican separación de propietarios, vínculos firmados manipulados o caducados, cuotas, recuperación tras reinicio y eliminación de trabajos caducados. El modelo intenta pasar rutas externas en una prueba; el servidor las sustituye por la fuente de ese usuario. No hay ejecución de código del usuario.

Pendientes externos: segunda cuenta real, otros orígenes regionales no observados, capacidad bajo carga, apertura en una aplicación CAD independiente y revisión pública del directorio. El equipo local no dispone de Docker; Render sí ha construido y arrancado la imagen Linux. La CI permite repetir la construcción manualmente.

El aislamiento local por usuario y trabajador no demuestra resistencia completa ante vulnerabilidades de todas las bibliotecas nativas. La imagen se ejecuta con usuario sin privilegios y necesita los límites, actualizaciones, controles de red y almacenamiento del proveedor.

Los resultados finales se guardan en `validation-results.json` sin rutas, credenciales o identificadores de cuenta. La validación de software no certifica cotas físicas ni tolerancias de fabricación.

Resultado local del 28/10/2026: **46 pruebas superadas, 0 fallos, 0 errores y 0 omitidas**. Incluye 44 pruebas del servicio web y dos del empaquetado de la base. Se verifican perfiles gratuito/completo, límites, controles, separación de propietarios, JWT, descargas, orígenes admitidos y rechazo de otras cuentas Azure o dominios engañosos. Las pruebas locales usan archivos sintéticos y sustitutos de autenticación/descarga donde se indica arriba; la comprobación real siguiente es independiente de esos sustitutos.

## Prueba real en ChatGPT web y Render Free

El usuario ha completado el acceso OAuth de producción con PKCE. ChatGPT ha descubierto seis herramientas y ha enviado dos PDF sintéticos mediante sus referencias de adjunto reales. Se han usado enlaces firmados suministrados por la plataforma, sin inventar URL ni usar claves de la API de OpenAI.

- STEP: inspección y revisión de página, exportación y reimportación válidas en Render Free de 512 MB. Prisma nominal de 20 × 10 × 5 mm, un sólido y volumen 999,9999999999998 mm³ frente a 1.000 mm³ esperado. Después se ha descargado el ZIP por HTTPS (200), comprobado la fuente por SHA-256 y reimportado localmente el STEP con los mismos controles.
- DXF: nueva inspección de PDF vectorial, dos trazados fuente, exportación y reapertura de dos entidades. Línea (0,0)-(100,0) de longitud 100 mm y círculo de centro (25,25) y radio 10 mm. Se ha descargado el ZIP por HTTPS (200), verificado el PDF fuente por SHA-256 y reabierto el DXF localmente. El PDF de comprobación tiene cinco páginas, todas renderizadas y revisadas visualmente. El registro usa 4,7244 píxeles por mm: su residuo de ajuste no representa incertidumbre física.
- El primer modelo DXF se bloqueó por vinculación insuficiente de evidencias de calibración. ChatGPT corrigió esa vinculación y repitió la exportación; las cotas y el alcance permanecieron iguales. Los bloqueos no se presentaron como exportaciones válidas.

La observación del evento de descarga del navegador integrado agotó su espera; por eso la descarga se verificó directamente por HTTPS, sin afirmar que aquel evento funcionara. La copia de resultados al almacenamiento interno de la conversación tampoco se ha validado: usar los enlaces originales entregados por el servicio.

Las pruebas reales detectaron dos cuentas de almacenamiento regionales de adjuntos de ChatGPT, incluidas ahora como dominios exactos. No hay comodín para Azure ni admisión automática de destinos nuevos. Otros orígenes permanecen bloqueados hasta verificarlos; no se declara compatibilidad universal con todas las regiones.

Los dos casos son sintéticos y conservan `DEFINED_REVIEW_PENDING` y precisión física desconocida. No demuestran fidelidad de cualquier plano real ni aptitud para fabricación. Volumen, caja y controles numéricos no certifican toda la geometría. No se ha probado una segunda cuenta real ni una aplicación CAD independiente.

Servicio: https://engineering-cad-converter-web.onrender.com

Repositorio: https://github.com/Boretto22/CAD-Converter

El servicio usa una instancia Free, Frankfurt, almacenamiento temporal sin disco y despliegues por cambios de Git desactivados. La plantilla pasa el esquema público de Render. `/health` responde 200 con perfil `free`; el acceso sin sesión a `/mcp` responde 401. La plataforma usa la comprobación TCP predeterminada en el alta directa. No se han contratado recursos de pago. GitHub Actions es manual. La publicación en el directorio público no se ha solicitado.
