# Usarlo únicamente desde ChatGPT en el navegador

El servicio gratuito está en https://engineering-cad-converter-web.onrender.com. El acceso OAuth, la recepción de PDF y dos conversiones sintéticas completas (DXF/PDF y STEP) están comprobados en una cuenta Plus, con descarga HTTPS y reapertura de los CAD. No se declara publicado en el directorio público ni probado desde una segunda cuenta.

## Primera conexión

En la cuenta del propietario ya se ha preparado la conexión web **Engineering CAD Converter**. Abrir el complemento, pulsar **Probar en el chat** y adjuntar el plano. Si se solicita acceso, usar **Sign up** cuando todavía no se tenga una cuenta de usuario del conversor. Esta cuenta es distinta de la cuenta administradora de Auth0. No enviar contraseñas al chat.

Para otra persona con una cuenta de ChatGPT que permita servidores personalizados:

1. Abrir [Complementos](https://chatgpt.com/plugins), pulsar **Añadir → Añadir servidor MCP personalizado**.
2. Nombre: `Engineering CAD Converter`. URL: `https://engineering-cad-converter-web.onrender.com/mcp`. Autenticación: **OAuth**.
3. Abrir **Ajustes avanzados de OAuth** y elegir **Cliente OAuth definido por el usuario**. ID público: `tpc_bCqGHRjZvk7L3wB438rkxr`. Método de autenticación del token: **none**. Dejar el secreto vacío; no se necesita una clave de OpenAI.
4. Usar `cad:read` y `cad:write` como ámbitos básicos, uno por línea. Mantener PKCE S256. El recurso debe ser exactamente la URL `/mcp`. El retorno detectado y autorizado es `https://chatgpt.com/connector_platform_oauth_redirect`; si ChatGPT muestra otro, el propietario debe registrarlo antes de continuar, sin comodines.
5. Revisar el aviso del servidor propio, crear el complemento y conectar. Iniciar sesión o registrarse gratuitamente y autorizar únicamente los permisos mostrados para el conversor. No introducir tarjetas ni contratar mejoras.

La disponibilidad de esta opción depende de la cuenta y sus políticas. El ZIP del plugin con skill se ha importado correctamente como complemento personal en la nube, pero su botón de inicio abrió escritorio en la cuenta probada. Para uso exclusivamente web se ha preparado la conexión MCP anterior. Las instrucciones técnicas también están disponibles mediante `get_cad_model_guide` en el servidor. [Procedimiento oficial](https://developers.openai.com/plugins/deploy/connect-chatgpt).

## Convertir un plano

Abrir una conversación nueva, seleccionar `@Engineering CAD Converter` y adjuntar el PDF o imagen. Pedir:

> Convierte este plano a DXF. Comprueba cotas, escala y unidades. No inventes medidas: pregunta por cualquier referencia que falte. Entrega el CAD, un PDF de comprobación y el informe de incertidumbre. Genera STEP solo si la geometría está completamente definida y dentro del alcance admitido.

El servidor limita los adjuntos a 5 MiB y cuatro páginas; también limita resolución, complejidad y trabajos. Si se necesita reducir una imagen, comprobar que las cotas siguen siendo legibles. STEP admite únicamente extrusiones rectangulares o circulares completamente definidas. Ninguna comprobación automática certifica precisión física o aptitud para fabricación.

Descargar los resultados inmediatamente. Los enlaces duran como máximo diez minutos; pueden renovarse mientras exista el trabajo. Los archivos se retienen como máximo una hora y desaparecen antes si Render se suspende o reinicia. El plan Free se suspende tras 15 minutos sin tráfico y puede tardar aproximadamente un minuto en despertar. Puede ser necesario volver a subir el plano. [Límites oficiales de Render Free](https://render.com/docs/free).

El alojamiento y el acceso se configuran con planes gratuitos, sin método de pago. Las cuotas pueden suspender el servicio; no se promete capacidad ilimitada. El plan existente de ChatGPT se gestiona por separado. El propietario puede compartir esta guía y el código; no debe compartir credenciales, enlaces temporales de acceso ni planos privados.

Si aparece un dominio de archivos no admitido, el propietario debe revisarlo; no cambiar la URL ni contratar otro plan para superar el bloqueo. Para comunicar errores, usar [Issues](https://github.com/Boretto22/CAD-Converter/issues) e incluir solo el mensaje y la versión, sin planos privados, contraseñas ni enlaces firmados.
