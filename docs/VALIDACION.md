# Verificación de esta implementación

Fecha: 12 de octubre de 2026. Entorno: macOS arm64, Python 3.12.14, entorno virtual propio de `CargaDocumentosDocIAPlus_Hexagonal` y versiones fijadas en `requirements-lock.txt`.

## Resultados ejecutados

- `python -m pytest -q`: **68 pruebas superadas en 8,86 segundos**, ejecutadas desde una copia limpia de los archivos preparados para Git, sin configuración ni cuentas de la instalación.
- `python -m compileall -q app scripts run.py`: sin errores de compilación.
- `python -m pip check`: sin incompatibilidades de dependencias.
- Waitress iniciado en `127.0.0.1:5053` en modo memoria.
- Recorrido de navegador: login con cuenta sintética temporal, catálogo, formulario, carga TXT y presentación del documento con ID, tamaño, SHA-256, autor y fecha. Catálogo posterior con una carga.
- Comprobación visual de ficha/formulario a 360 px: ancho del documento igual al viewport, sin desbordamiento horizontal global. Comprobación del catálogo a 1280 px; las capturas se conservan solo en la instalación local.
- Los archivos versionados de la aplicación anterior se compararon mediante SHA-256 antes/después: no se modificaron.
- Lanzadores `.command` con permiso de ejecución, entorno independiente y configuración privada preparada. No se copiaron credenciales ni cuentas del gestor anterior.

La cuenta temporal `verificacion` del navegador se retiró tras la comprobación. El modo demo conserva exclusivamente su cuenta local aleatoria. Los documentos de verificación eran sintéticos y estaban solo en memoria.

## Qué cubren las pruebas

| Área | Casos comprobados |
|---|---|
| HTTP y cuentas | Acceso sin sesión, CSRF ausente e inválido, lector sin permiso de carga, revocación, logout, login incorrecto y límite de intentos. |
| Incorporación | TXT, BOM y bytes originales, nombres con rutas, PDF válido sin texto, PDF con imagen real, DOCX; metadatos y tamaños. |
| Rechazos | Vacío, binario disfrazado, TXT no UTF-8, PDF cifrado, DOCX con macros/objetos y exceso de entradas ZIP. |
| Duplicados | Igual contenido con otro nombre o identidad, revisión explícita, destino inventado, relación sin candidatas, altas idénticas en dos hilos. |
| Lectura | Filtros, ficha, descarga, escape HTML, hash y tamaño; UUID inválido. |
| S3 simulado | Paginación, precondiciones/cifrado, cierre de streams, JSON corrupto/excesivo, clave exacta, esquema v1, campos y tipos inválidos. |
| Fallos de dos objetos | Ficha denegada, compensación, compensación fallida, respuesta de ficha perdida, resultado incierto, precondición original y ficha conflictiva, respuesta original perdida. |
| Arquitectura | Mismo contrato memoria/S3 simulado, permisos al llamar directamente al caso de uso, importación del núcleo sin frameworks/parsers y análisis de sus dependencias. |
| Entorno | Test config no lee `.env` ni construye sesión AWS; conexiones de red bloqueadas durante la suite. |
| Asistentes | Preparación idempotente, secreto privado, usuario sin contraseña en claro, no sobrescritura, entrada AWS no oculta, sesión inválida, guardado verificado sin revelar secretos. |
| Arranque | Doble escritor de la misma instalación rechazado; bloqueo liberado al cerrar. |
| Colab | Notebook limpio/compilable, región, creación/reutilización simulada, 403 no tratado como ausencia, privacidad y negativa a cambiar KMS. |

## Límites de esta evidencia

La suite automatizada utiliza un doble de S3 y no acredita por sí sola los permisos efectivos de AWS. Además, en el entorno del docente se realizó una comprobación con S3 real: carga sintética, ficha, descarga idéntica, SHA-256, cifrado AES256, duplicado rechazado y lectura desde otro cliente. Se utilizó el cliente HTTP de pruebas de Flask y una cuenta temporal; esto no sustituye la comprobación del despliegue de cada alumno. Los identificadores del bucket y de sus objetos se conservan únicamente en informes locales excluidos de Git.

No se ha ejecutado el programa en Windows o Ubuntu, ni el notebook dentro de Colab. Sus instrucciones y lógica de preparación se incluyen; la ejecución local comprobada es macOS. La revisión visual no equivale a auditoría completa WCAG: no se ha completado una evaluación con lector de pantalla ni zoom real del navegador al 200 %.

Las 68 pruebas son funciones/casos parametrizados de esta implementación; no significan 65 requisitos diferentes ni una certificación de seguridad. La matriz de la skill es una referencia de aceptación más amplia. Esta evidencia no atribuye OCR, extracción, aprobación, chunks, embeddings o RAG a un gestor que no los implementa.
