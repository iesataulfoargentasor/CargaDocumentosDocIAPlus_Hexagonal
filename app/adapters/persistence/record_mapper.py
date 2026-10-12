"""Único mapeador entre el documento del núcleo y la ficha JSON S3 v1."""
from copy import deepcopy
from datetime import datetime
import re
from uuid import UUID
from app.domain.errors import NotFound

MIMES = {'pdf': 'application/pdf', 'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'txt': 'text/plain'}

def canonical_id(value):
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError()
    except (ValueError, AttributeError, TypeError) as exc:
        raise NotFound() from exc
    return value

def original_key(prefix, document_id, extension):
    canonical_id(document_id)
    if extension not in MIMES:
        raise ValueError('Formato no permitido')
    return f'{prefix}/originales/{document_id}/original.{extension}'

def validate_record(record, prefix):
    if not isinstance(record, dict) or type(record.get('schema_version')) is not int or record['schema_version'] != 1:
        raise ValueError('Esquema no compatible')
    canonical_id(record['id'])
    limits = {'titulo': (5,150), 'centro': (1,200), 'ensenanza': (1,100), 'modulo': (1,100), 'curso_academico': (1,30), 'procedencia': (3,200), 'observaciones': (0,2000)}
    for key, (low, high) in limits.items():
        value = record[key]
        if not isinstance(value,str) or not low <= len(value) <= high:
            raise ValueError('Campo inválido')
    if record['estado_declarado'] not in ('borrador','final'):
        raise ValueError('Estado no permitido')
    file = record['archivo']
    name = file['nombre_original']
    if not isinstance(name,str) or not 1 <= len(name) <= 200 or any(ord(c)<32 or ord(c)==127 for c in name) or '/' in name or '\\' in name:
        raise ValueError('Nombre inválido')
    extension = name.rsplit('.',1)[-1].lower()
    if file['clave_s3'] != original_key(prefix, record['id'], extension) or file['tipo_mime'] != MIMES[extension]:
        raise ValueError('Referencia incoherente')
    if type(file['tamano_bytes']) is not int or file['tamano_bytes'] <= 0 or not isinstance(file['sha256'],str) or not re.fullmatch(r'[0-9a-f]{64}',file['sha256']):
        raise ValueError('Integridad inválida')
    reg = record['registro']
    if reg['estado'] != 'guardado' or not isinstance(reg['usuario'],str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{3,40}',reg['usuario']):
        raise ValueError('Registro inválido')
    when = datetime.fromisoformat(reg['fecha'])
    if when.utcoffset() is None or when.utcoffset().total_seconds() != 0:
        raise ValueError('Fecha no UTC')
    relation = record['relacion']
    if relation is not None:
        if relation['tipo'] not in ('revision','complemento') or canonical_id(relation['documento_id']) == record['id'] or not isinstance(relation['motivo'],str) or not 5 <= len(relation['motivo']) <= 500:
            raise ValueError('Relación inválida')
    return record

def to_record(document, prefix):
    record = deepcopy(document)
    extension = record['archivo'].pop('extension')
    record['archivo']['clave_s3'] = original_key(prefix,record['id'],extension)
    return validate_record(record,prefix)

def from_record(record, prefix):
    validate_record(record,prefix)
    document = deepcopy(record)
    key = document['archivo'].pop('clave_s3')
    document['archivo']['extension'] = key.rsplit('.',1)[-1]
    return document
