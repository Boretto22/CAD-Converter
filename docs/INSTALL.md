# Instalación

## Uso inmediato sin plugin

Descomprime el ZIP fuente, instala Python 3.12 y sigue el README. Abre esa carpeta con tu agente y solicita que use `skills/engineering-cad-converter/SKILL.md`. El paquete no descarga modelos ni llama a APIs. La instalación de bibliotecas sí usa el índice de paquetes configurado.

Para probar antes de instalar como plugin: ejecuta `engcad demo work/demo`, abre el DXF y el PDF y lee el informe. Para STEP instala el extra `step` y ejecuta el ejemplo del README. Los archivos de demostración son sintéticos.

## Skill independiente

El ZIP de skill contiene una carpeta `engineering-cad-converter` con `SKILL.md`, referencias, scripts y requisitos. En un agente con soporte Agent Skills, utiliza su flujo de instalación de skills y selecciona esa carpeta. No basta con pegar el nombre ni adjuntar el ZIP a un chat normal.

En Codex CLI se puede copiar esa carpeta a `~/.codex/skills/engineering-cad-converter` (en Windows, bajo el perfil del usuario). Si existe una instalación, conservarla y comparar antes de sustituir. Reiniciar sesión y seleccionar `$engineering-cad-converter`. En superficies ChatGPT que lo permitan, seleccionar la skill con `@`.

## Plugin en desarrollo

El ZIP de plugin tiene `plugin.json` en la raíz. Para probarlo en escritorio antes de publicación, usar el flujo local de Plugin Creator disponible en la cuenta con la carpeta del plugin y solicitar una entrada de marketplace personal. No introducir una URL de servidor porque esta versión no contiene MCP. Si ese flujo no aparece, usar la skill o CLI independiente.

No se modifica automáticamente la configuración del usuario al descomprimir o ejecutar el empaquetador. La instalación del plugin y la de Python son pasos diferentes. Dar al agente una carpeta de trabajo escribible y conservar el paquete instalado sin cambios.

## Plugin publicado

Después de aprobación y publicación reales, buscar Engineering CAD Converter en el directorio y comprobar el publicador antes de instalar. Iniciar un chat local nuevo e invocar el plugin. Hoy no se proporciona un enlace de instalación porque aún no está publicado.

La v1 se declara Desktop only. [Guía oficial de plugins](https://learn.chatgpt.com/docs/plugins). [Formato y prueba local](https://developers.openai.com/plugins/build/plugins).

## Resolución de errores

- Falta módulo: ejecutar `doctor` y reinstalar requisitos en el mismo entorno que ejecuta la CLI.
- Salida ya existe: elegir una carpeta nueva; no borrar el resultado previo para continuar.
- Hash diferente: volver a identificar la fuente real; no copiar el hash nuevo para ocultar una sustitución.
- Gate bloqueado: corregir el dato o aportar evidencia. No cambiar `fully_constrained` a true por conveniencia.
- CadQuery no disponible: continuar con DXF; instalar el extra compatible para STEP.
