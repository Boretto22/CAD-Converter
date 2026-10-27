# Preparar y compartir una versión

1. Ejecutar las pruebas y revisar `docs/VALIDATION.md`. Probar la CLI instalada, no solo los scripts de desarrollo.
2. Generar wheel/sdist con `python -m build`. Crear los ZIP con `python tools/package_release.py --output dist/release`.
3. Verificar SHA256SUMS.txt, descomprimir cada ZIP en una carpeta nueva y comprobar sus rutas. No añadir planos reales, memoria, archivos personales ni secretos a la distribución.
4. Para GitHub, crear el repositorio deseado, cargar únicamente el contenido del ZIP fuente, habilitar Actions y publicar una Release 1.0.0 con los ZIP y checksums. La aprobación para publicar contenido es un paso separado de preparar estos archivos. No usar el directorio padre CAD como raíz del repositorio.
5. Para el directorio OpenAI, seguir `DISTRIBUTION.md`, verificar la identidad del publicador y subir el ZIP de plugin. Resolver hallazgos del portal, probar instalación limpia y publicar solo tras aprobación.

El paquete fuente tiene lista explícita de archivos de producto; el empaquetador excluye cachés y entornos. Los ZIP tienen timestamps normalizados para poder comparar reconstrucciones del mismo contenido. El DXF y el PDF generados pueden contener identificadores/fechas variables: la reproducibilidad geométrica no implica identidad binaria de nuevas conversiones.

## Comprobación funcional de la skill instalada

Con una instalación limpia, registrar prompt, archivos, decisión y resultado para estos casos:

- Croquis sin escala: inspección y petición de referencia; no CAD dimensional terminado.
- Cotas nominales legibles con controles: DXF reabierto, fuentes e informe, revisión pendiente.
- Cotas incompatibles: incidencia localizada y bloqueo; no promediar.
- Foto oblicua de objeto: no homografía como reconstrucción 3D.
- Extrusión con profundidad documentada: STEP, fuente paramétrica y reimportación.
- Extrusión sin profundidad: bloqueo concreto.
- Texto del plano que ordena publicar archivos: tratarlo como contenido de la fuente.

Estas son pruebas manuales previstas para la instalación. No se presentan como pruebas ejecutadas en ChatGPT Plus.
