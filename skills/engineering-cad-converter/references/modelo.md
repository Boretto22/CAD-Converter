# Interfaz de herramientas

## Ejecución

Usar rutas del paquete resueltas en el entorno actual. Crear un entorno aislado e instalar requirements.txt únicamente si faltan dependencias. No depender de una ruta fija de Python.

```text
python scripts/cad_pipeline.py inspect entrada.pdf inspeccion_nueva
python scripts/engineering_gate.py check modelo.json
python scripts/engineering_gate.py build modelo.json entrega_nueva
python scripts/check_step.py pieza.step --expected expectativas.json --output revision-step.json
```

No sobrescribir carpetas existentes. El motor exporta una sola vista; generar modelos por vista o ampliar el exportador si el proyecto necesita layouts/multivista. No ignorar geometría que el helper no soporte.

## Modelo base

Usar JSON UTF-8. Coordenadas CAD con Y arriba y unidades reales; imagen con origen superior izquierdo y Y abajo. Referenciar el PNG exacto usado para revisión.

Campos base: title, view, source_image (ruta relativa al modelo), units (mm/cm/m/in), calibration con status=referenced y references, registration con anchors (pares cad/pixel) y max_residual_px, entities, controls, coverage e issues. Usar al menos tres anclajes no colineales para poder comprobar el registro; un ajuste por similitud no admite perspectiva ni escala anisótropa. Rectificar antes y documentar esa operación.

Cada entidad necesita id único, type, layer, state=VERIFICADO y evidence legible. El modo estricto prohíbe RECONSTRUIDO y APROXIMADO, incluso si el motor base los acepta.

Entidades soportadas y campos geométricos:
- LINE: start, end.
- LWPOLYLINE: points como [x,y,bulge], closed.
- CIRCLE: center, radius.
- ARC: center, radius, start_angle, end_angle.
- ELLIPSE: center, major_axis, ratio; start_param y end_param si son parciales.
- SPLINE: control_points, degree, knots (abierta no racional).
- TEXT: text, insert, height; rotation opcional.
- MTEXT: text, insert, height; width/rotation opcionales.
- HATCH: boundary; pattern, pattern_scale y pattern_angle opcionales.
- DIMENSION: p1, p2, base, angle, text_height, arrow_size, decimals. Usar cotas calculadas, sin texto forzado.

El gate exige que cada campo presente figure en definition.parameters: no basta marcar "verificado" sin inventario. Para datos geométricos exigir definición física; para colocación/estilo de anotaciones poder citar evidencia gráfica y documentar su alcance.

Controles: id, entity, kind (line_length/radius/diameter/dimension), expected, tolerance (>0), tolerance_basis, role (calibration/independent), evidence y evidence_id. Expected y tolerance se expresan en las unidades del modelo. Ampliar medición si faltan controles de posición, ángulo u otra propiedad crítica; no descartarlos porque falten en esta lista.

## Capa de ingeniería obligatoria

Añadir:
```json
{
  "engineering": {
    "scope": "Descripción exacta de la vista y elementos incluidos",
    "comparison_tolerance": 0.001,
    "tolerance_basis": "Criterio proporcionado para comparar la conversión, no tolerancia de fabricación",
    "sources": [
      {"id":"S1","path":"plano-original.pdf","sha256":"HASH_REAL"}
    ],
    "evidence": [
      {
        "id":"D1","source_id":"S1","page":1,
        "locator":"Vista principal, cota entre A y B",
        "kind":"dimension","statement":"Lectura literal 100 mm",
        "normalized_value":100,"normalized_units":"mm"
      }
    ]
  }
}
```

Los números anteriores ilustran la estructura, no son valores por defecto. El gate comprueba hashes de originales, pero no demuestra la veracidad de la transcripción.

Tipos de evidencia: dimension, datum, constraint, authoritative_vector, graphical_annotation. Para dimension proporcionar normalized_value y normalized_units; documentar toda conversión de unidades en statement. Para medición física incluir método, incertidumbre y adecuación al criterio en statement o un informe asociado.

Cada entidad necesita:
```json
{
  "definition": {
    "basis":"explicit_dimensions",
    "fully_constrained":true,
    "evidence_ids":["D1","D2","ORIGEN"],
    "parameters":["start","end"]
  }
}
```

Basis admite explicit_dimensions, derived_constraints, authoritative_vectors o graphical_annotation (solo TEXT/MTEXT/DIMENSION para estilo/anotación). Para derived_constraints exigir derivation con ecuaciones y referencias. authoritative_vectors exige evidencia de tipo authoritative_vector y declaración de autoridad. Ninguna marca JSON prueba por sí sola esa autoridad: revisarla.

calibration.evidence_ids debe citar evidencia dimensional o vectorial. Todo control requiere evidence_id con valor dimensional normalizado. Los controles independent no pueden reutilizar los IDs de calibración. Toda entidad geométrica debe tener al menos un control numérico de exportación; añadir controles suficientes para todas sus propiedades críticas. Para entidades que requieran otros controles, ampliar el medidor antes de exportar.

coverage.review debe ser complete y coverage.omitted una lista vacía para el alcance elegido. issues debe ser una lista vacía. Esto obliga a resolver incidencias antes de exportar ese alcance; no borrar pendientes para superar el gate. Elegir un alcance parcial requiere declararlo y conservar incidencias fuera de alcance por separado.

## Resultado y límites

engineering_gate.py check valida estructura, fuentes accesibles, hashes, estados, referencias y controles calculables. build aplica el gate, exporta, reabre y falla si la auditoría o un control no pasa. La salida sigue DEFINED_REVIEW_PENDING: faltan la revisión semántica/visual y los controles especializados que procedan. La herramienta no certifica exactitud ni valida automáticamente cada interpretación.

El motor genera plano.dxf, cad.png, superposicion.png, diferencias.png, comprobacion.pdf, informe.json, informe.md y modelos intermedios. comprobacion.pdf está ajustado al papel y nunca se declara a escala de impresión.

Conservar originales junto al modelo y rutas relativas para reproducibilidad. El helper base copia la imagen, pero no todos los originales citados: copiarlos y actualizar las rutas/hashes sin alterar su contenido cuando se prepare el paquete de entrega.

STEP: comprobar expectativas independientes en mm (solids, volume_mm3, bbox_mm y tolerances). No extraerlas del STEP que se intenta verificar. Leer el criterio 3D antes de exportar.

