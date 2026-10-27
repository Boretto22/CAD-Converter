# Componentes externos

MIT se aplica a los archivos originales de este proyecto, incluidos los helpers desarrollados previamente para el flujo CAD del usuario. Las bibliotecas externas conservan sus licencias. No se distribuye un entorno Python ni binarios de terceros en los ZIP.

Dependencias directas: PyMuPDF, ezdxf, Pillow, NumPy, Matplotlib y ReportLab. CadQuery es opcional y depende de Open CASCADE y otros componentes. Las herramientas de desarrollo incluyen setuptools, wheel, build, pytest, jsonschema y PyYAML.

PyMuPDF se distribuye bajo AGPL o licencia comercial según su proveedor. No presentar el conjunto de dependencias como íntegramente MIT ni suponer que la licencia de este repositorio sustituye sus condiciones. Consultar los archivos de licencia de las versiones efectivamente instaladas antes de redistribuir binarios o construir un servicio.

Se incluyen versiones de la validación en `docs/VALIDATION.md`. Los rangos de requisitos no constituyen un bloqueo de todas las dependencias transitivas. `requirements-tested.txt` registra las versiones directas utilizadas para reproducir las comprobaciones locales.
