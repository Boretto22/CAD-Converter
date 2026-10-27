# Engineering CAD Converter v1.0

**PDF, imágenes y croquis a CAD editable con evidencia dimensional.** Proyecto local distribuible, skill reutilizable y paquete de plugin para ChatGPT/Codex. No requiere una clave API.

Estado: versión 1.0.0 del software. Reconstrucción **asistida**, no reconocimiento automático universal. Ninguna prueba sintética certifica la precisión de un plano real.

La versión de servicio para usar adjuntos desde ChatGPT en navegador está en [browser_service/README.md](browser_service/README.md). Incluye MCP remoto, autenticación, trabajos y descargas. Su activación pública requiere completar alojamiento e inicio de sesión; los paquetes locales 1.0 ya entregados conservan su alcance de escritorio.

## Empieza aquí

En Windows con Python 3.12, desde esta carpeta:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install ".[dev]"
.\.venv\Scripts\engcad doctor
.\.venv\Scripts\engcad demo work\primera-demo
```

En macOS/Linux:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install '.[dev]'
.venv/bin/engcad demo work/primera-demo
```

`demo` crea una imagen sintética, un modelo documentado y una entrega con DXF, PNG, PDF e informes. Usa una carpeta nueva en cada ejecución. Python admitido: 3.11-3.13; probado aquí con 3.12. Para STEP: `python -m pip install '.[step]'` usando el Python del entorno.

## Para una fuente real

1. `engcad inspect entrada.pdf work/inspeccion` conserva original y SHA-256 y extrae las páginas, textos, vectores y anotaciones. También admite imágenes leídas por Pillow. No inventa el modelo.
2. Con la skill y el agente, inspecciona el material y prepara el JSON siguiendo [el contrato](skills/engineering-cad-converter/references/modelo.md) y [la ampliación v1](skills/engineering-cad-converter/references/contrato-v1.md). Un técnico puede editarlo manualmente. Confirma unidades, cotas, fuentes y criterio de aceptación.
3. `engcad check modelo.json` bloquea referencias insuficientes o controles fallidos.
4. `engcad build modelo.json work/entrega` exporta y reabre el DXF, mide controles y genera comprobaciones. La salida queda **DEFINIDO; REVISIÓN PENDIENTE**.
5. Revisa fuentes, superposición, todas las páginas PDF, cobertura y el archivo en tu CAD antes de aceptarlo para el uso previsto.

Si falta una cota o el criterio, entrega el inventario pendiente y pide ese dato. No uses una puerta o un objeto de tamaño supuesto como regla. El PDF de comprobación está ajustado al papel y no sirve para medir con regla.

Para una extrusión rectangular o circular completamente definida: `engcad step examples/step/model-step.json work/step-demo`. [Alcance STEP](skills/engineering-cad-converter/references/step.md).

## Servicio para ChatGPT en el navegador

La implementación remota está en [browser_service](browser_service/README.md), con [activación gratuita guiada](browser_service/ACTIVAR.md). Usa Render Free y Auth0 Free, sin recursos de pago ni clave de API de OpenAI. Falta completar el despliegue y la conexión real de ChatGPT. El alojamiento gratuito tiene suspensión y almacenamiento temporal; descargar resultados al terminar.

## ChatGPT Plus y distribución

El plugin v1 requiere ejecución **local de escritorio**. Tener Plus no garantiza que una función concreta esté habilitada en una cuenta o superficie. No funciona como convertidor alojado en cualquier chat web o móvil. Consulta [instalación](docs/INSTALL.md) y [distribución verificada](docs/DISTRIBUTION.md).

Se distribuyen tres ZIP: fuente preparada para GitHub, plugin con `plugin.json` en la raíz y skill independiente. El repositorio local es utilizable sin ChatGPT. Subir un ZIP a un chat no demuestra que se haya instalado un plugin. La publicación oficial requiere el proceso del portal; este proyecto no afirma estar aprobado ni publicado.

El paquete completo `Engineering-CAD-Converter-v1.0.0.zip` reúne los tres ZIP, wheel/sdist cuando se han construido, instrucciones y checksums. Validación local: **44 pruebas superadas**, con los límites descritos en [VALIDATION.md](docs/VALIDATION.md).

## Qué contiene

- Skill técnica con flujo de inspección, reconstrucción, bloqueos y revisión.
- CLI `engcad`: inspect, check, build, step, demo y doctor.
- Fuentes preservadas, modelos reproducibles, incertidumbre declarada y controles de exportación.
- Pruebas negativas y sintéticas, CI para GitHub y empaquetador reproducible con SHA-256.
- [Validación](docs/VALIDATION.md), [privacidad](docs/PRIVACY.md), [licencias](THIRD_PARTY_NOTICES.md), [cambios](CHANGELOG.md) y [guía de contribución](CONTRIBUTING.md).

No incluye OCR universal, rectificación automática, reconstrucción 3D arbitraria, DWG ni certificación metrológica. Las comprobaciones de estructura no prueban la veracidad de la transcripción. El uso con planos reales requiere validar cada entrada y el CAD de destino.

## Desarrollo y paquetes

```text
python -m pytest -q
python -m build
python tools/package_release.py --output dist/release
```

No ejecutar sobre directorios de salida existentes. El empaquetador usa una lista explícita de carpetas; no incorpora archivos vecinos del usuario. Consulta `docs/RELEASE.md` antes de publicar.
