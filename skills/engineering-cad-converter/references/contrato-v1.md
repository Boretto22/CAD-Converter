# Contrato v1 y límites verificables

El JSON de `examples/nominal/model.json` (en la distribución fuente) es ejecutable. Los ejemplos son sintéticos y sus números no son valores por defecto para proyectos reales.

## Imagen de revisión y fuentes

`engineering.review_image` contiene `source_id`, `sha256` del PNG exacto y `transformation` (render, página, recorte, resolución, giro o matriz). El hash detecta sustituciones; la descripción de la transformación debe revisarse, no se demuestra automáticamente.

El paquete de salida conserva los originales citados en `sources/` y actualiza las rutas de `modelo-reproducible.json`. `modelo-original.json` conserva la entrada para auditoría y puede contener rutas privadas: no publicarlo sin revisión. El repositorio público no incluye planos de usuarios.

## Incertidumbre obligatoria

En `engineering.uncertainty` elegir una modalidad:

- `nominal_definition`: requiere `physical_accuracy: "unknown"` y `basis` con procedencia. Modela definiciones nominales legibles; no asigna cero a la incertidumbre física.
- `bounded_measurement`: requiere `units`, `basis`, `localization_px`, `reference_length`, `reference_length_bound`, `reference_span_px`, `reference_span_bound_px`, `max_span_px`, `distortion_bound`. Las cotas usadas como mediciones deben incluir método y evidencia. No elegir límites para forzar aceptación.

Con L longitud de referencia, P distancia en píxeles y límites dL y dP:

`s = L/P; s_min = (L-dL)/(P+dP); s_max = (L+dL)/(P-dP)`

`E = 2*localization_px*s_max + max_span_px*max(s_max-s, s-s_min) + distortion_bound`

Es una cota conservadora de error de longitud condicionada a los componentes declarados, no un intervalo estadístico. No demuestra errores angulares, de posición, de lente o deformación no incluidos. Exige P>dP y L>dL. Si E supera `comparison_tolerance`, bloquea. Un criterio numérico de prueba sintética no es una tolerancia de fabricación.

La escala del registro debe quedar dentro del intervalo calculado. `max_span_px` debe cubrir al menos las longitudes de LINE y los diámetros de CIRCLE/ARC exportados; para un arco se usa conservadoramente el diámetro completo. Esto no sustituye comprobar posiciones relativas o contornos complejos.

## Cobertura real del comprobador

Se comprueban hashes, referencias, valores finitos, unidades, anclajes no colineales, estados, duplicados exactos y controles medibles. Se reabre DXF y se mide longitud/radio/diámetro/cota. No se resuelve automáticamente todo el sistema de restricciones ni se prueba la verdad del texto de evidencia. Un ID distinto no garantiza independencia física. Posición, ángulo, topología, contornos auto-intersecados y asociaciones requieren controles especializados y revisión.

El exportador interno admite más entidades que las que el gate v1 puede medir. LINE, CIRCLE y ARC cuentan con medidas básicas; para polilíneas, elipses, splines o rayados, el gate bloqueará la entrega si no existe un control compatible. No degradar estas entidades silenciosamente. TEXT, MTEXT y DIMENSION conservan semántica básica pero requieren revisión visual.

`coverage.review=complete` significa que el autor ha completado su inventario del alcance; el software no inspecciona semánticamente todas las vistas. La salida permanece provisional. `engineering-check.json` contiene el resultado de incertidumbre. Revisar junto a `informe.json`, el PDF y las fuentes.
