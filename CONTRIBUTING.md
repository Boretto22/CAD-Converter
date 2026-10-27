# Contribuir

Trabajar en una rama y probar cambios con fixtures sintéticos o material cuyo uso esté autorizado. Nunca incorporar planos privados a una incidencia o prueba pública.

Para ampliar entidades, incorporar evidencia por parámetro, medidas sobre el archivo reabierto y pruebas de rechazo. No añadir un tipo de exportación que el gate acepte sin poder comprobar sus propiedades críticas. Documentar qué aspectos requieren revisión humana.

Antes de una contribución: instalar `.[dev]`, ejecutar `python -m pytest -q`, validar ejemplos y revisar la documentación de alcance. Para cambios 3D instalar además `.[step]`. La matriz CI cubre Windows/Linux y STEP por separado; los flujos se ejecutan manualmente para evitar consumos automáticos. Revisar la cuota gratuita antes de lanzarlos; las pruebas locales no requieren GitHub Actions.
