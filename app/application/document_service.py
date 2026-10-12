"""Casos de uso independientes de Flask, S3 y parsers de documentos."""
from threading import Lock
from app.application.ports import DocumentRepository, FileValidator
from app.application.dto import UploadCommand, DownloadResult
from app.domain.document import identity, new_document
from app.domain.errors import Duplicate, PossibleRevision, ValidationError
from app.domain.policies import validate_metadata
from app.domain.user import User

class DocumentService:
    def __init__(self, repository: DocumentRepository, validator: FileValidator, catalog, center, max_bytes):
        self._repository, self._validator = repository, validator
        self.catalog, self.center, self.max_bytes = catalog, center, max_bytes
        self.upload_lock = Lock()

    def create(self, actor: User, command: UploadCommand):
        actor.require('upload')
        metadata = validate_metadata(command.metadata, self.catalog, self.center)
        upload = self._validator.validate(command.stream, command.filename, self.max_bytes)
        with self.upload_lock:
            records = self._repository.list_all()
            for existing in records:
                if existing['archivo']['sha256'] == upload.sha256:
                    raise Duplicate(existing, identity(existing) != identity(metadata))
            candidates = [r for r in records if identity(r) == identity(metadata)]
            relation = None
            target = command.relation.get('relacion_id', '')
            kind = command.relation.get('relacion_tipo', '')
            reason = command.relation.get('relacion_motivo', '').strip()
            if candidates:
                if not target or not kind:
                    raise PossibleRevision(candidates)
                if target not in {r['id'] for r in candidates} or kind not in ('revision', 'complemento') or not 5 <= len(reason) <= 500:
                    raise ValidationError({'relacion': 'Selecciona un documento coincidente, un tipo de relación y un motivo de 5–500 caracteres.'})
                relation = {'tipo': kind, 'documento_id': target, 'motivo': reason}
            elif target or kind or reason:
                raise ValidationError({'relacion': 'No hay documentos de esta identidad con los que establecer esa relación.'})
            record = new_document(metadata, upload, actor.username, relation)
            self._repository.save(record, upload.content)
            return record

    def list(self, actor: User, filters=None):
        actor.require('read')
        filters = {k: v.strip() for k, v in (filters or {}).items()
                   if k in ('q', 'modulo', 'curso_academico', 'estado_declarado')}
        records = self._repository.list_all()
        selected = [r for r in records if all(not v or (v.casefold() in r['titulo'].casefold() if k == 'q' else r.get(k) == v) for k, v in filters.items())]
        return sorted(selected, key=lambda r: r['registro']['fecha'], reverse=True)

    def get(self, actor: User, document_id):
        actor.require('read')
        return self._repository.get(document_id)

    def download(self, actor: User, document_id):
        record = self.get(actor, document_id)
        content = self._repository.download(record, self.max_bytes)
        return DownloadResult(content, record['archivo']['nombre_original'], record['archivo']['tipo_mime'])
