# Activación guiada para el propietario

Esta configuración se realiza una vez. Los usuarios finales solo necesitan ChatGPT y su plano.

## 1. Cuenta de acceso

Crear o abrir una cuenta propia en [Auth0](https://manage.auth0.com/) usando Free. El dominio viene incluido: Applications → aplicación → Settings → Domain, normalmente terminado en `auth0.com`. No comprar dominio ni activar Custom Domains, que requiere verificación con tarjeta. Al terminar cualquier prueba promocional, mantener Free y usar solo sus funciones. [Precios oficiales](https://auth0.com/pricing). No hace falta compartir su contraseña ni claves de administración con el agente. Elegir la región correspondiente y guardar el dominio público del tenant que aparece en la configuración.

Auth0 es la opción guiada propuesta; también sirve un proveedor OAuth 2.1 compatible con metadatos, PKCE S256, JWT RS256 y claves JWKS. No se ha creado una cuenta Auth0 automáticamente.

## 2. Publicar el código preparado

El directorio del proyecto contiene solo software y ejemplos sintéticos. Crear un repositorio dedicado para el conversor y subir el contenido del paquete web; no usar como repositorio la carpeta CAD del usuario, que contiene otros planos. Render debe poder leer ese repositorio. Si se hace privado, autorizar a Render específicamente.

Si el conector no ofrece crear repositorios, crear uno desde el panel de GitHub y autorizarlo para la integración. La publicación del código es un paso revisable separado de la preparación local.

## 3. Servicio Render sin costes adicionales

Seleccionar el espacio confirmado por el propietario y usar exclusivamente la plantilla gratuita:

- Una instancia `free` de 512 MB, región Frankfurt.
- Dockerfile `browser_service/Dockerfile`, contexto raíz del repositorio, comprobación `/health`.
- Sin disco persistente, bases de datos, colas externas ni ampliaciones de pago.
- Archivos temporales en `/tmp/engcad/jobs`; `CAD_PROFILE=free`; despliegues automáticos desactivados.
- Mantener la cuenta sin método de pago. No contratar mejoras al fallar un trabajo.

Render incluye un subdominio HTTPS `onrender.com`; no hay que comprar un dominio. El plan Free es para pruebas y uso limitado. No garantiza disponibilidad continua ni capacidad para planos grandes. Los STEP pequeños pasan las pruebas locales, pero su memoria en Render de 512 MB sigue sin verificarse. Un error debe detener el trabajo sin cambiar de plan.

Condiciones verificadas el 28/10/2026 en [Render Free](https://render.com/docs/free): tras 15 minutos sin tráfico se suspende y tarda aproximadamente un minuto en despertar. Se pierden los archivos al suspenderse, reiniciarse o desplegarse. Hay 750 horas gratuitas mensuales compartidas por workspace y cuotas de tráfico y construcción. Sin método de pago, agotar tráfico suspende servicios gratuitos; agotar minutos de construcción bloquea nuevas construcciones hasta el siguiente mes. No usar pings para impedir la suspensión. Descargar resultados inmediatamente: una hora de retención es un máximo, no una garantía.

GitHub Actions está configurado para ejecución manual. No hacen falta llamadas a la API de OpenAI. Las funciones y el plan existente de ChatGPT se gestionan por separado. Revisar las condiciones si cambian: no se promete alojamiento ilimitado para siempre. La plantilla sustituye cualquier propuesta anterior de alojamiento de pago.

## 4. Registrar la API de acceso

Con la dirección HTTPS que Render asigne al servicio, en Auth0 abrir Applications → APIs → Create API. Darle un nombre y usar como identificador la URL exacta del servidor seguida de `/mcp`. Dejar la firma RS256.

Añadir permisos `cad:read` y `cad:write`. Habilitar el flujo de consentimiento y la conexión de usuarios que se vaya a permitir. El token debe llevar el usuario en `sub` y los permisos en `scope`.

Para que Auth0 entienda el parámetro estándar `resource`, comprobar Resource Parameter Compatibility Profile en Settings → Advanced y habilitar la compatibilidad si el tenant la necesita. El valor `aud` del token debe ser exactamente el identificador `/mcp`; no sirve un token destinado a `/userinfo`. [Explicación oficial de Auth0](https://support.auth0.com/center/s/article/mcp-audience-error-with-auth0).

Usar CIMD si está habilitado en el tenant. Como alternativa, registrar un cliente público con Authorization Code + PKCE S256 y configurar en el proveedor el callback exacto mostrado por ChatGPT. No usar una URL de callback adivinada ni un secreto de aplicación dentro del ZIP. Si se usa DCR, habilitarlo y revisar las conexiones permitidas. [Opciones de autenticación de ChatGPT](https://developers.openai.com/plugins/build/auth).

## 5. Variables del servicio

En el panel de Render, configurar:

```text
CAD_BASE_URL = origen HTTPS real del servicio, sin / final ni /mcp
CAD_OAUTH_ISSUER = issuer exacto publicado por Auth0, normalmente con / final
CAD_JWKS_URL = jwks_uri real del documento de descubrimiento, en el mismo host del issuer
CAD_SIGNING_KEY = secreto nuevo aleatorio de al menos 32 bytes
CAD_DATA_DIR = /tmp/engcad/jobs
CAD_PROFILE = free
CAD_FILE_HOSTS = hosts exactos de adjuntos de ChatGPT aprobados por el propietario
```

La plantilla de Render genera el secreto. No pegarlo en el chat, ni publicarlo, ni incluirlo en GitHub. Los dominios y el identificador público de cliente pueden compartirse para completar la configuración.

Comprobar el issuer y `jwks_uri` en el documento de descubrimiento del proveedor. PKCE debe anunciar `S256`. El backend valida firma, issuer, audiencia y vencimiento en cada petición. La metadata del recurso se sirve en `/.well-known/oauth-protected-resource/mcp`.

## 6. Conectar desde ChatGPT

Abrir Plugins → añadir servidor MCP personalizado, indicar la URL real `/mcp` y elegir OAuth. Usar los datos de registro/callback que muestre la cuenta. Completar el inicio de sesión. Instalar la conexión y probarla con un archivo sintético en una conversación nueva.

Si la opción no aparece, verificar la disponibilidad y los permisos de esa cuenta; este proyecto no garantiza habilitación universal de todas las cuentas Plus. [Guía oficial de conexión y prueba](https://developers.openai.com/plugins/deploy/connect-chatgpt).

Repetir desde una segunda cuenta: ambos usuarios deben poder convertir sus propios archivos y no acceder a los trabajos del otro. Descargar DXF/PDF/STEP cuando proceda y verificar que los enlaces caducan. Hasta hacer esta prueba no se declara listo el acceso real de usuarios externos.

## 7. Compartir públicamente

Para uso privado de prueba puede servir la conexión personalizada autorizada. Para que cualquiera lo encuentre en el directorio: generar el paquete con la URL real, completar identidad del publicador, contacto de soporte, políticas aplicables, cinco casos positivos/tres negativos, vídeo accesible, verificación de dominio y revisión del portal. [Publicación oficial](https://developers.openai.com/plugins/deploy/submission).

Conectar Render o superar las pruebas locales no equivale a publicar ni a aprobar un plugin.
