"""Punto de composición: aquí se eligen adaptadores y se inyectan puertos."""
from app.application.auth_service import AuthService
from app.application.document_service import DocumentService
from app.adapters.persistence.json_user_store import JsonUserStore, ScryptPasswordVerifier
from app.adapters.validation.file_validator import DocumentFileValidator

def compose(config, repository=None):
    if repository is None:
        if config['STORAGE_BACKEND'] == 'memory':
            from app.adapters.persistence.memory_repository import MemoryRepository
            repository = MemoryRepository()
        else:
            from app.adapters.persistence.s3_repository import S3Repository
            repository = S3Repository(config['S3_BUCKET'],config['S3_PREFIX'],config['AWS_REGION'], aws_options=config['AWS_OPTIONS'])
    documents = DocumentService(repository,DocumentFileValidator(),config['CATALOG'],config['CENTRO'],config['MAX_FILE_BYTES'])
    auth = AuthService(JsonUserStore(config['USERS_FILE']),ScryptPasswordVerifier())
    return documents, auth
