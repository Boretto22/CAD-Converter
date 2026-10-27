# Método de ingeniería

## Evidencia y metrología

Separar cuatro afirmaciones:

| Afirmación | Evidencia necesaria |
|---|---|
| Una cota nominal es 25 mm | Cota legible, unidad y vista identificadas o archivo nativo autorizado |
| El CAD contiene 25 mm | Medición al reabrir el archivo exportado |
| El objeto físico mide 25 mm | Medición trazable con incertidumbre declarada |
| La pieza cumple una especificación | Criterios de aceptación y comprobaciones aplicables documentados |

No sustituir una por otra. Un vector PDF puede recuperar geometría gráfica, pero el PDF puede estar deformado, reducido o contener símbolos fuera de escala; las cotas nominales y la autoridad de la fuente mandan. Conservar la diferencia y preguntar si se contradicen.

Mantener por parámetro: fuente y hash, página/vista, localizador, lectura literal, unidad, valor normalizado, papel (definición, calibración o control), incertidumbre o tolerancia y su fundamento. Transcribir únicamente lo legible. Confirmar decimal, símbolo de diámetro/radio, multiplicidad, rosca, ajuste y signo; no dejar que OCR decida solo.

Una incertidumbre de medición debe ser adecuada al criterio de aceptación. No imponer una proporción metrológica universal sin especificación del trabajo. Si no se conoce, bloquear el uso dimensional físico y pedir la información mínima.

## Suficiencia geométrica

- Comprobar origen, sistema de ejes y correspondencia entre vistas; distinguir coordenadas locales de georreferenciación.
- Formar un inventario de parámetros necesarios y restricciones disponibles. Comprobar que no queden grados de libertad y que las restricciones no se contradigan.
- Resolver relaciones derivadas únicamente de datos explícitos: una perpendicularidad dibujada a mano no es una restricción probada. Documentar ecuaciones y unidades.
- No usar una cota aplicada al mismo modelo como control independiente. Una referencia de calibración solo comprueba que se aplicó la escala; reservar cotas externas al ajuste.
- Para curvas libres sin definición analítica/nativa suficiente, pedir CAD original o medición adecuada; no sustituir por una spline ajustada a píxeles.
- No usar una captura cartográfica para declarar bordillos, edificios o parcelas exactos. Solicitar cartografía vectorial con sistema de referencia, precisión conocida o levantamiento si el uso exige medidas reales.

## Capturas múltiples y fotos

Tratar cada vista como una fuente independiente. Confirmar que representan el mismo estado y revisión. Usar puntos comunes comprobables y más controles que los necesarios para ajustar la transformación. Registrar residuales, incertidumbre y controles fuera del ajuste. Un residual bajo no demuestra fidelidad del resto de la imagen.

En papel fotografiado, comprobar alabeo, perspectiva, distorsión óptica y sombras. Una rectificación de plano no corrige un papel ondulado ni revela dimensiones desconocidas. Si la fuente no soporta la tolerancia requerida, pedir escaneo mejor, plano original o cotas.

## Plano a escala

Trabajar siempre 1:1 en modelo. Definir la escala en layout o PDF, no multiplicando todas las coordenadas del modelo.

Para unidades en metros y escala 1:n:
- Longitud en papel (mm) = longitud modelo (m) × 1000 / n.
- Altura de vista modelo (m) = altura de viewport papel (mm) × n / 1000.
- Ejemplo de comprobación, nunca valor por defecto: 20 m a 1:250 deben medir 80 mm.

Elegir formato y orientación que contengan el alcance; dividir en láminas si procede. Marcar cualquier impresión "al 100 %, sin ajustar". Verificar una longitud en las coordenadas del PDF y dimensiones reales de página. Diferenciar PDF de revisión ajustado al papel de PDF para imprimir a escala.

## Reconstrucción 3D

Exigir definición suficiente de cada volumen, corte, taladro, espesor, posición, radio, orientación, relación y unidad. Aceptar restricciones geométricas explícitas que completen dimensiones. No extruir una planta con espesor imaginado ni producir STEP por apariencia.

Conservar modelo paramétrico cuando exista. Reimportar STEP en motor CAD; comprobar validez, sólidos, caja, volumen y propiedades/dimensiones de cada característica crítica. Caja y volumen correctos no prueban la pieza completa. Registrar revisión de todas las vistas.

No confundir malla STL con sólido paramétrico o STEP verificado. No inventar material, rugosidad, ajuste, tolerancias geométricas o tratamiento térmico. Si la entrega requiere una norma concreta, usar la edición indicada o verificar documentación oficial vigente; no atribuir cumplimiento por una plantilla genérica.

## Comprobación final

Reabrir el archivo real, no solo volver a renderizar los datos previos. Comparar coordenadas, unidades y medidas nominales con las fuentes. Revisar:

- Dimensiones y restricciones definidoras; controles independientes y cierre de cadenas.
- Continuidad/cierre, intersecciones, duplicados, islas y orientación cuando afecten a la función.
- Correspondencia semántica de cotas, textos, símbolos, bloques, rayados, capas y todas las vistas.
- Superposición con transformación fija; investigar discrepancias, nunca reajustar localmente para esconderlas.
- Presentación y escala física únicamente en las páginas declaradas a escala.
- Compatibilidad en un segundo lector cuando esté disponible; comunicar qué lector se usó y si falta.

El motor base genera siempre un PDF provisional. Mantenerlo así hasta finalizar la revisión; crear un informe final separado que cite su hash y la evidencia de revisión. No cambiar un rótulo a "validado" sin hacer las comprobaciones. No usar porcentajes de coincidencia de tinta como porcentajes de precisión o de exactitud.

Entregar un registro de incidencias resueltas y un inventario de alcance. Si se acuerda excluir una zona, nombrarla expresamente; nunca hacerla desaparecer del informe.

