# Cómo leer el código

## MVC y hexagonal: dos perspectivas compatibles

En MVC, el controlador de documentos transforma un formulario en `UploadCommand`. La vista Jinja representa los datos y los errores. El modelo está formado por documentos, usuarios y políticas de dominio. El controlador no guarda objetos ni aplica por su cuenta las reglas de duplicados.

La arquitectura hexagonal pone al núcleo (`domain` y `application`) en el centro. Sus dependencias apuntan hacia dentro. Los `Protocol` de `application/ports.py` declaran lo que el núcleo necesita; no crean SDK ni conexiones. Los adaptadores externos implementan esos contratos por coincidencia de métodos.

El punto de composición `bootstrap.py` elige `S3Repository` o `MemoryRepository`, `DocumentFileValidator`, `JsonUserStore` y `ScryptPasswordVerifier`. Crea un solo `DocumentService` compartido por los hilos. La factoría Flask registra rutas y traduce errores del núcleo a HTTP. `app/__init__.py` carga la factoría de forma diferida para poder importar dominio sin Flask.

## Recorrido de una carga

1. `security.py` obtiene el usuario activo desde el caso de uso de autenticación y comprueba CSRF/permisos HTTP.
2. `document_controller.py` admite solo campos previstos. Extrae un stream estándar y un nombre del FileStorage de Flask. No entrega `request` o `FileStorage` al núcleo.
3. `DocumentService.create` comprueba `upload`, valida metadatos con políticas puras y llama al puerto de inspección de formatos.
4. El validador devuelve bytes originales, extensión, MIME, nombre saneado y SHA-256. Es una inspección técnica, no una extracción del ETL.
5. Bajo el bloqueo del servicio se listan documentos, se detecta copia exacta y se valida la relación.
6. `new_document` genera UUID, metadatos, identidad de archivo sin ruta S3 y registro de autor/fecha.
7. `S3Repository.save` llama al mapeador para convertir el documento a ficha v1 y generar las claves de S3. Escribe con precondición de no existencia y resuelve fallos parciales.
8. El caso de uso retorna el documento confirmado. El controlador redirige y Jinja presenta el detalle. Ante copia exacta devuelve 409, validación 422 y fallo de persistencia 503.

Listado, consulta y descarga también pasan por casos de uso. Los permisos HTTP no sustituyen la comprobación del núcleo. Para llamar al núcleo desde otro adaptador hay que autenticar al actor en ese adaptador: el objeto `User` no es por sí mismo una credencial transportable.

## Contratos de persistencia

`DocumentRepository` tiene cuatro operaciones: listar, consultar por UUID, guardar documento/bytes y descargar bytes con límite. Los registros del núcleo son diccionarios de datos, para mantener sencillo el piloto; los mensajes de entrada/salida y el usuario son dataclasses. El esquema externo se valida en el único mapeador, evitando repartir conocimiento de claves S3 entre capas.

El mapeador convierte `archivo.extension` ↔ `archivo.clave_s3`. La ficha de S3 no tiene el campo interno `extension`. Mantiene `schema_version=1` y las claves españolas del gestor original. Se valida tipo y longitud de campos, UUID, clave exacta del original, MIME, tamaño, hash, registro UTC y relación. Una ficha corrupta no se omite silenciosamente.

El adaptador en memoria devuelve copias para que una vista no pueda alterar accidentalmente el repositorio. Desaparece con el proceso. Sirve para demostración y pruebas, no sustituye un almacén duradero.

## Concurrencia y límites

La exclusión mutua engloba leer candidatas, detectar duplicado, comprobar relación y guardar. La inspección binaria ocurre antes del bloqueo. El bloqueo del lanzador es un refuerzo local contra dos arranques de la misma instalación. No convierte el diseño en distribuido: dos instalaciones con el mismo destino no están coordinadas.

S3 garantiza operaciones por objeto, pero no una transacción original+ficha. Las escrituras condicionales previenen sobrescribir una clave, no duplicar bytes bajo UUID distintos. La aplicación no promete exactamente una vez frente a todos los fallos: identifica resultados inciertos para revisión.

## Extensión futura

Un nuevo adaptador documental puede implementar el mismo puerto sin importar Flask al núcleo. Si cambia la semántica de persistencia o se añade búsqueda distribuida, deben cambiar también las pruebas y las garantías documentadas. La hexagonal reduce acoplamiento; no resuelve automáticamente deduplicación distribuida, vigencia o aprobación.

Para ETL, incorporar extracción, transformación e indexación como nuevos casos de uso y contratos explícitos. Mantener original/UUID/hash y trazabilidad; no cambiar el estado técnico `guardado` para fingir que significa «aprobado para RAG».
