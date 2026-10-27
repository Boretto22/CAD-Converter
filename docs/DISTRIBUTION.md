# Distribución comprobada el 27/10/2026

## Resultado

La documentación actual de OpenAI admite plugins públicos con skills, MCP o ambos. Un plugin portable usa `plugin.json` en raíz y descubre `skills/`. Este proyecto elige **skills-only con ejecución local**, sin servidor MCP ni hooks. [Formato oficial](https://developers.openai.com/plugins/build/plugins).

Los plugins que necesitan ejecutar programas locales deben marcarse `requires_local_executor: true` en `extensions.com.openai`; se presentan como Desktop only. La documentación distingue los MCP locales, cuyas solicitudes requieren autorización de partner. Esta v1 no lleva MCP. [Requisitos de escritorio](https://developers.openai.com/plugins/deploy/desktop-only).

Publicación: seleccionar organización/proyecto y una identidad verificada, subir el ZIP al portal, resolver hallazgos automáticos, enviar a revisión y publicar tras aprobación. Las skills deben superar los controles. El ZIP preparado no equivale a aprobación. [Proceso oficial](https://developers.openai.com/plugins/deploy/submission).

La referencia de errores permite omitir las URL públicas en paquetes skills-only; para un MCP remoto exige otros datos y verificaciones. No se han inventado dominio, correo, identidad verificada ni URL de repositorio. [Validación del portal](https://developers.openai.com/plugins/deploy/submission-errors).

## Alcance para Plus

El objetivo son usuarios Plus con la aplicación y ejecución local disponibles. No se ha comprobado la habilitación de cada cuenta Plus ni se ha instalado este plugin en una cuenta de prueba independiente. La documentación consultada no permite prometer disponibilidad universal por el mero nombre del plan.

El directorio permite instalar plugins desde superficies compatibles. Un plugin Desktop only requiere escritorio; no equivale a una integración operativa en cualquier chat web o móvil. [Instalación oficial](https://learn.chatgpt.com/docs/plugins).

## Decisión de producto

La CLI local y la skill son la alternativa independiente y funcional. No dependen de un servicio de conversión alojado ni de créditos API. La conversación en ChatGPT usa los recursos y límites del plan del usuario.

Una futura versión web/móvil requeriría un backend que reciba archivos, gestione aislamiento, autenticación, retención y descarga, además del MCP y sus pruebas de integración. No forma parte de v1. No incluir un MCP ficticio en el paquete.

## Estado de entrega

- Archivos y ZIP: preparados localmente y verificables.
- GitHub: código, CI y guía preparados; no hay repositorio remoto creado ni URL pública.
- Portal OpenAI: no se ha subido ni enviado a revisión.
- Identidad del publicador y prueba de instalación en una segunda cuenta: pendientes de quien publique.

Revisar estas fuentes antes de cada publicación porque los requisitos pueden cambiar.
