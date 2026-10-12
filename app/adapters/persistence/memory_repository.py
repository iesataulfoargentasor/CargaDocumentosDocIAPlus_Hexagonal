"""Adaptador de demostración y pruebas: nada se envía a AWS ni se persiste."""
from copy import deepcopy
from hashlib import sha256
from uuid import UUID
from app.domain.errors import NotFound, StorageError

class MemoryRepository:
    def __init__(self):
        self.records, self.files = {}, {}

    def list_all(self):
        return deepcopy(list(self.records.values()))

    def get(self, document_id):
        try:
            if str(UUID(document_id)) != document_id:
                raise ValueError()
            return deepcopy(self.records[document_id])
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            raise NotFound() from exc

    def save(self, document, content):
        if document['id'] in self.records:
            raise StorageError('Identificador ya existente; no se sobrescribe.')
        self.files[document['id']] = bytes(content)
        self.records[document['id']] = deepcopy(document)

    def download(self, document, max_bytes):
        try:
            content = self.files[document['id']]
        except KeyError as exc:
            raise StorageError('No se encuentra el original.') from exc
        if len(content) > max_bytes or len(content) != document['archivo']['tamano_bytes'] or sha256(content).hexdigest() != document['archivo']['sha256']:
            raise StorageError('El original no coincide con su ficha.')
        return content
