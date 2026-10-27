# Evidencia de validación de v1.0

Fecha de comprobación: 27/10/2026. Estado: validación de software y ejemplos sintéticos; no certificación de planos reales.

## Pruebas incluidas

- Gate original: una exportación nominal y 24 casos de rechazo (25 comprobaciones).
- Pruebas adicionales: incertidumbre por intervalos, referencias de la imagen, datos no finitos, tipos no admitidos, unidades, portabilidad, no sobrescritura, registro de render, PDF multipágina y archivo corrupto.
- STEP: profundidad ausente, geometría no soportada, fuentes sin referencia, unidades inválidas, expectativas incompletas; reimportación de prisma y cilindro, y fallo intencionado de volumen.
- Distribución: contenido de los ZIP, ausencia de rutas absolutas de archivo dentro del ZIP, exclusión de archivos privados fuera de la lista y hashes idénticos al repetir empaquetado.

## Ejemplos

`examples/nominal` contiene una línea nominal de 100 mm y un círculo de radio 10 mm. El texto de cota es evidencia gráfica, fuera del alcance CAD de ese ejemplo. Por eso la diferencia visual conserva texto cian: es una exclusión declarada, no un error dimensional oculto. El ejemplo no representa una pieza completa.

`examples/step` contiene una especificación sintética de prisma de 20 x 10 x 5 mm. Se espera un sólido y volumen de 1000 mm³. Se entrega fuente paramétrica y modelo trazable. Ninguna dimensión proviene de un plano privado.

## Límites de esta validación

No se ha validado una fuente de cliente, la precisión física, el reconocimiento automático de símbolos, un conjunto completo de GD&T, ni apertura externa en AutoCAD/LibreCAD/FreeCAD. Los hashes y el gate comprueban consistencia de datos, no la verdad de cada afirmación del modelo.

No se ha instalado el plugin en una segunda cuenta Plus ni se ha enviado al portal público. Las pruebas CI remotas están preparadas, no ejecutadas en GitHub. Las versiones y resultados locales finales se registran abajo al cerrar la entrega.

## Resultado local final

- Windows, Python 3.12.14; instalación en un entorno nuevo y reinstalación del wheel final.
- 44 pruebas pytest superadas, sin fallos ni omisiones. Una prueba ejecuta las 25 comprobaciones de la base; no sumarlas como si fueran 25 pruebas pytest adicionales.
- Conversión explícita mm -> cm, m e in comprobada sobre DXF reabierto.
- Bloqueo de incertidumbre incompatible con la escala registrada o un máximo de longitud insuficiente.
- Reimportación STEP de prisma, cilindro y conjunto de dos sólidos; detección del fallo intencionado de volumen.
- Cinco páginas del PDF revisadas visualmente; la página inicial incluye incertidumbre y las otras cuatro conservan la revisión original. Sin recortes o solapamientos observados en esta demo.
- Skill validada con `quick_validate.py`. Manifiesto portable comprobado con el esquema Agent Plugins 1.0.0; esto no valida requisitos adicionales del portal ni equivale a aprobación.
- Versiones directas: PyMuPDF 2.0, ezdxf 1.4.5, Pillow 13.0.0, NumPy 2.5.4, Matplotlib 3.11.2, ReportLab 5.1.0, CadQuery 2.8.0.

`validation-results.json` conserva un resumen sin rutas de usuario. Los resultados brutos locales están fuera del paquete público. Los ZIP se comprueban también tras su generación final.
