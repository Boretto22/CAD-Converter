# Engineering CAD Converter Web 1.0

Servidor remoto para convertir adjuntos desde ChatGPT en el navegador. La persona que usa el conversor no instala Python ni prepara JSON: ChatGPT inspecciona el plano con las herramientas y prepara el modelo respaldado por evidencia. El servidor ejecuta el gate y genera archivos reales.

**Estado:** servicio alojado en [Render Free](https://engineering-cad-converter-web.onrender.com), con salud pública comprobada. Falta completar OAuth y probar la conexión real desde ChatGPT. No se afirma publicación en el directorio ni instalación en una segunda cuenta.

## Para la persona que convierte un plano

Después de que el propietario active el servicio:

1. Instala o conecta Engineering CAD Converter Web en ChatGPT con el enlace del propietario.
2. Inicia sesión cuando ChatGPT lo solicite.
3. Adjunta tu PDF, imagen o croquis. Escribe: «Convierte este plano a DXF. Comprueba las unidades, las cotas y la escala; pregunta por cualquier dato que falte».
4. Responde las preguntas sobre referencias o criterio de aceptación.
5. Descarga el ZIP, DXF y PDF. STEP se entrega únicamente para una extrusión rectangular/circular completamente definida.

El informe conserva el estado REVISIÓN PENDIENTE. Una prueba automática no certifica precisión física o fabricación. Los enlaces duran diez minutos y pueden renovarse mientras el trabajo esté retenido. En el perfil gratuito, los trabajos caducan como máximo en una hora y se limpian en el siguiente ciclo, normalmente en 60 segundos. Render pierde los archivos al suspenderse, reiniciarse o desplegarse: pueden desaparecer antes. Descargar resultados al terminar.

## Para quien activa el servicio

Seguir [ACTIVAR.md](ACTIVAR.md). La configuración predeterminada usa Render Free, Auth0 Free y sus dominios incluidos, sin discos ni recursos de pago. No añadir tarjetas ni contratar mejoras. El plan existente de ChatGPT se gestiona por separado. Se necesita una URL HTTPS estable, un repositorio que Render pueda leer y un proveedor de inicio de sesión. No se necesita clave de OpenAI: la interpretación la hace el ChatGPT de la persona que llama a las herramientas.

Instalación de desarrollo desde la raíz del proyecto:

```text
python -m pip install ".[dev,step]" ./browser_service
python -m pytest -q browser_service/tests
```

Configurar las variables de `deploy/env.example` en el entorno, sin guardar secretos en el repositorio. Ejecutar `engcad-web --check-config` y `engcad-web`. La CLI del servidor escucha el puerto `PORT`, por defecto 8000. Las rutas públicas son `/`, `/health`, `/privacy`, `/terms` y `/support`; las herramientas están en `/mcp` y requieren OAuth.

El Dockerfile se construye desde la raíz: `docker build -f browser_service/Dockerfile -t engcad-web .`. El programa de conversión se ejecuta con un usuario sin privilegios. Para despliegue, usar `deploy/render.yaml` o crear el servicio con los mismos parámetros.

## Flujo remoto

`get_cad_model_guide` → `inspect_cad_source` → `get_cad_job` → `read_cad_page` → `export_cad_dxf` o `export_cad_step` → `get_cad_job` → descarga.

El contrato de archivos declara `openai/fileParams` y recibe `download_url`, `file_id`, con `mime_type` y `file_name` opcionales. No admite rutas del equipo del usuario. Las rutas del modelo se reemplazan por las de la fuente realmente subida. Se reabren las exportaciones y se miden los controles.

## Límites operativos

- Un servicio, una réplica y un proceso ASGI; SQLite local. No escalar horizontalmente sin cambiar catálogo y almacenamiento.
- Perfil `free` predeterminado: un trabajador activo, dos trabajos en espera, seis retenidos por usuario, 24 en total y 90 llamadas por minuto y usuario. Inspecciones y exportaciones cuentan como trabajos separados. Máximo 250 entidades por modelo.
- Adjuntos de hasta 5 MiB; cuatro páginas/fotogramas; PDF de hasta dos megapíxeles renderizados por página a 120 DPI, seis megapíxeles en conjunto e imágenes de hasta cuatro megapíxeles. Complejidad vectorial acotada. Dividir o reducir una fuente puede hacer ilegibles las cotas: comprobarlas de nuevo.
- Tiempo máximo de trabajador de 120 segundos. En Linux se aplican límites de CPU, memoria virtual, archivos abiertos y tamaño de archivo. También se requiere el límite de recursos del contenedor/proveedor. Un proceso separado no es por sí solo un aislamiento de seguridad completo.
- Descargas HTTPS directas desde hosts explícitos autorizados; sin redirecciones. `CAD_FILE_HOSTS` debe coincidir con los hosts reales usados por los adjuntos de ChatGPT. No ampliar a dominios arbitrarios para superar un error.
- La revisión muestra PNG de hasta 1800 × 1800 píxeles, con dimensiones y transformación registradas. La fuente y el render original permanecen como evidencia. Una imagen reducida puede resultar insuficiente para el criterio requerido.

Render Free se suspende tras 15 minutos sin tráfico y tarda aproximadamente un minuto en despertar. Sin método de pago, agotar las cuotas suspende servicios o bloquea nuevas construcciones. [Condiciones oficiales](https://render.com/docs/free). No se garantiza que 512 MB admitan todas las conversiones STEP; falta probar el contenedor en Render Free. Un fallo se comunica sin cambiar a un plan de pago.

El perfil opcional `full` conserva los límites anteriores de 20 MiB, 12 páginas y 24 horas; no es la configuración del despliegue gratuito. No contratar capacidad adicional automáticamente.

## Entrega y validación

[VALIDATION.md](VALIDATION.md) detalla las pruebas y sus límites. `review-cases.json` prepara cinco casos positivos y tres negativos para revisión del plugin. El vídeo y las pruebas reales de OAuth/ChatGPT no se inventan.

Para generar el plugin después de obtener la URL real:

```text
python browser_service/configure_plugin.py --base-url URL_HTTPS_REAL --publisher "Identidad real del publicador" --output dist/plugin-web
```

Se genera `plugin.json`, `mcp.json`, la skill remota y su ZIP. CIMD es el valor predeterminado; puede indicarse `--oauth-client-id` para un cliente público previamente registrado con PKCE. El proveedor debe soportar el modo elegido. El generador no crea cuentas OAuth ni acredita una identidad pública.

Para empaquetar todo el servicio y el motor: `python browser_service/package_browser_service.py --output dist/web-release`.
