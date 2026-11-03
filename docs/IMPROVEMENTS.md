# Flujos de revisión, recuperación y geometría ampliada

Estas funciones conservan revisión pendiente y precisión física desconocida. No convierten una fotografía sin referencias en un modelo nominal certificado. No añaden servicios de pago ni requieren una API de modelos.

## Revisar y corregir un borrador

`engcad preview modelo.json carpeta-nueva` genera `review.html`, `coverage.json`, `draft-report.json` y `session.zip`. El HTML es autónomo: incluye las imágenes, opacidad, zoom, desplazamiento con las barras del navegador y lista de revisión. Permite editar y descargar el JSON. La modificación del JSON no actualiza el CAD existente: vuelve a generar la vista previa y ejecuta `engcad check` antes de exportar.

La herramienta MCP `prepare_cad_draft` ofrece este flujo para la página inspeccionada de un usuario. Puede conservar un modelo incompleto, por ejemplo con `issues: ["Falta profundidad"]`. El agente debe preguntar por ese dato, conservar lo ya definido y no marcar el borrador como validado.

## Comprobar cobertura

El campo opcional `coverage.inventory` vincula elementos de la fuente con entidades CAD:

```json
{"inventory": [
  {"id": "vista1-linea1", "locator": "página 1, línea inferior", "disposition": "included", "entity_ids": ["L1"]},
  {"id": "vista1-etiqueta", "locator": "página 1, título", "disposition": "excluded", "entity_ids": [], "reason": "Anotación fuera del alcance"}
]}
```

`included` exige entidades existentes. `excluded` exige un motivo. `unresolved` bloquea una exportación nominal; guárdalo como borrador. Cuando hay inventario, toda entidad CAD debe estar vinculada. Sin inventario se informa `DECLARED_ENTITIES_ONLY`: la cobertura completa no está demostrada. Un objeto nunca inventariado tampoco puede detectarse con este control; revisa todas las vistas y páginas.

## Recuperar trabajo sin almacenamiento de pago

`engcad checkpoint modelo.json session.zip` guarda modelo y fuentes locales, incluidos los datos sin resolver. Las fuentes deben estar dentro de la carpeta del modelo. `engcad resume session.zip carpeta-nueva` comprueba rutas y hashes y recupera archivos de datos, sin ejecutar código ni aprobar el modelo. Los hashes detectan cambios respecto al manifiesto del archivo, no acreditan autenticidad externa.

El servicio prepara `recovery.zip` antes de comprobar un modelo. Si la exportación queda bloqueada, el propietario puede descargar esa sesión para corregirla. El ZIP recuperable nunca se presenta como CAD válido. Un tercero no puede consultar el trabajo ni generar sus enlaces.

Descarga la sesión antes de que caduque o se reinicie el alojamiento. Un ZIP ya descargado permite recuperar trabajo localmente. **No hay persistencia garantizada en Render Free**: un fallo antes de preparar/descargar la sesión puede perderlo. La persistencia automática en nube necesita un almacenamiento externo duradero; no se ha contratado ninguno.

## Trazos de PDF, sin aproximaciones encubiertas

`engcad vectors entrada.pdf carpeta-nueva --page 1` produce `pdf-strokes-UNCALIBRATED.dxf` y `vector-inventory.json`. La inspección MCP de PDF incluye esos artefactos por página.

Se conservan líneas, límites de rectángulos/cuadriláteros y los puntos de control y nudos de curvas Bézier cúbicas como splines. No se ajustan círculos a curvas ni se rasterizan los trazos para reconstruirlos. Las coordenadas corresponden a la página PDF sin rotar, con Y reflejada. Una unidad representa un punto PDF; `$INSUNITS=0` evita presentarlo como milímetros del objeto.

La salida es evidencia gráfica sin calibrar, **no CAD nominal para fabricación**. Se inventarían exclusiones de texto, imágenes, rellenos, recortes y operaciones no compatibles. Una máscara de recorte puede hacer que se extraigan trazos no visibles; se mantiene esa limitación. La escala física, la autoridad de la fuente y las tolerancias deben justificarse aparte en el modelo nominal.

## STEP ampliado

Se conservan los perfiles `rectangle` y `circle`. Se añaden:

- `polygon`: `dimensions.depth` y `vertices: [{x: dimension, y: dimension}, ...]`. Cierre implícito, 3–200 vértices distintos, sin autointersecciones. XY y extrusión +Z desde cero.
- `revolution`: sección XZ definida por esos vértices, donde X es radio y Y es coordenada axial global Z. `dimensions.angle` debe definir expresamente 360 grados. Radios no negativos y cota axial mínima cero. No admite cortes posteriores ni revoluciones parciales.
- `features` sobre extrusiones: `through_hole`, `blind_hole` y `rectangular_pocket`, cada una con `id` único y `dimensions` con `x`, `y`, `depth` y `radius`, o `width`/`height` para el vaciado rectangular. Se posicionan respecto al origen del perfil y se cortan desde la cara superior hacia abajo. La profundidad de un agujero pasante debe coincidir con la del cuerpo; los cortes ciegos deben ser menos profundos.

Cada `dimension` es `{value, source_id, locator, statement}`. Las coordenadas pueden ser negativas; radios, tamaños y profundidades son positivos. Se comprueba que el volumen retirado por cada operación coincide con el volumen analítico de su herramienta y que queda un sólido válido: se rechazan cortes recortados por el borde, solapados o que dividen el cuerpo. Los controles finales siguen reimportando STEP y contrastando volumen y caja con valores esperados calculados independientemente. Esos controles no demuestran por sí solos todas las dimensiones o la interpretación del plano.

## Validar contra un CAD de referencia

`engcad benchmark casos.json carpeta-nueva` compara candidatos y referencias independientes, incluyendo posición, longitud/radio y extremos de arcos, con correspondencia uno a uno. Se admiten LINE, CIRCLE y ARC; tipos no medidos se informan y no pasan silenciosamente. Cada DXF debe declarar las unidades correspondientes. Límite de 500 entidades por caso; divide alcances mayores.

```json
{"cases": [{
  "id": "pieza-01", "kind": "real", "source": "plano.pdf",
  "reference_dxf": "referencia-revisada.dxf", "candidate_dxf": "resultado.dxf",
  "units": "mm", "tolerance": 0.02,
  "reference_basis": "Procedencia y revisión independiente de la referencia; justificar el criterio numérico"
}]}
```

El ejemplo es un contrato, no una prueba ejecutada. `kind: real` es una declaración del responsable del caso. La referencia, el permiso para usarla y sus medidas deben verificarse aparte. Las pruebas automatizadas incluidas son sintéticas. **La batería con planos reales y referencias independientes sigue pendiente de disponer de esos pares de archivos**; no se ha generado ni certificado una referencia real a partir de su propio resultado.

## Errores y documentación

La inspección publica la carpeta únicamente al terminar. Un PDF corrupto produce un mensaje legible por CLI, sin traceback ni una carpeta parcial presentada como resultado. El prefijo `BLOQUEADO:` se imprime una sola vez. Los números históricos de pruebas están fechados; la ejecución de CI vinculada al commit es la referencia para el estado actual.
