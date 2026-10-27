# STEP v1

El generador soporta únicamente un sólido extruido desde un rectángulo o círculo, sin agujeros, redondeos, chaflanes ni geometría oculta. El perfil queda centrado en XY y se extruye desde Z=0 hacia +Z. Registrar este datum y su relación con la fuente. Un croquis frontal no autoriza a inventar profundidad.

El modelo requiere `units: mm`, `fully_defined: true`, `issues: []`, `scope`, `datum`, `physical_accuracy: unknown`, fuentes con ID/ruta/SHA-256 y `profile` rectangle/circle. `dimensions` contiene width/height/depth o radius/depth. Cada dimensión es un objeto con value, source_id, locator y statement.

`expected` contiene units=mm, solids=1, volume_mm3, bbox_mm=[x,y,z], tolerances con volume_mm3 y bbox_mm, y basis. Calcular expectativas desde las cotas por un procedimiento independiente; nunca leerlas del STEP para usarlo como su propia referencia. Para un prisma nominal, V=ancho*alto*profundidad; para cilindro, V=pi*r²*profundidad. Conservar cálculo y fuente.

El helper reimporta STEP y verifica validez, número de sólidos, volumen y caja. No basta para probar todos los detalles o la exactitud física. La salida incluye `pieza.step`, `model-step.json`, `parametric.py`, fuentes, `step-check.json` y estado. Los fallos conservan evidencia parcial con `INCOMPLETE_DO_NOT_USE` y devuelven error.
