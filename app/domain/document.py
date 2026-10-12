"""Modelo documental: documento independiente de su destino de almacenamiento."""
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

@dataclass(frozen=True)
class ValidatedFile:
    content: bytes
    filename: str
    extension: str
    mime: str
    sha256: str

def identity(record):
    return tuple(record[k] for k in ("centro", "ensenanza", "modulo", "curso_academico"))

def new_document(metadata, upload, username, relation=None):
    document_id = str(uuid4())
    return {
        "schema_version": 1, "id": document_id, **metadata,
        "archivo": {"extension": upload.extension,
                    "nombre_original": upload.filename, "tipo_mime": upload.mime,
                    "tamano_bytes": len(upload.content), "sha256": upload.sha256},
        "relacion": relation,
        "registro": {"usuario": username, "fecha": datetime.now(timezone.utc).isoformat(), "estado": "guardado"},
    }
