"""Único adaptador de persistencia documental. No requiere acceso público al bucket."""
import json
import logging
import uuid
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

log = logging.getLogger(__name__)

from app.domain.errors import StorageError, NotFound
from .record_mapper import to_record, from_record, canonical_id

class S3Repository:
    def __init__(self, bucket, prefix="programaciones", region=None, client=None, aws_options=None):
        self.bucket, self.prefix = bucket, prefix.strip("/")
        self.region, self._client = region, client
        self.aws_options = aws_options or {}

    @property
    def client(self):
        if not self.bucket:
            raise StorageError("Falta configurar S3_BUCKET en el servidor.")
        if self._client is None:
            options = self.aws_options
            if options.get('AWS_PROFILE') and options.get('AWS_ACCESS_KEY_ID'):
                raise StorageError('Usa un perfil AWS o credenciales directas, no ambos.')
            session = boto3.Session(profile_name=options.get('AWS_PROFILE'),
                aws_access_key_id=options.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=options.get('AWS_SECRET_ACCESS_KEY'),
                aws_session_token=options.get('AWS_SESSION_TOKEN'),region_name=self.region)
            self._client = session.client("s3", config=Config(
                connect_timeout=5, read_timeout=20, retries={"max_attempts": 2, "mode": "standard"}))
        return self._client

    def ficha_key(self, document_id):
        try:
            if str(uuid.UUID(document_id)) != document_id:
                raise ValueError()
        except (ValueError, AttributeError):
            raise NotFound()
        return f"{self.prefix}/fichas/{document_id}.json"

    def _read_record(self, key):
        obj = self.client.get_object(Bucket=self.bucket, Key=key)
        try:
            data = obj["Body"].read(128 * 1024 + 1)
        finally:
            obj["Body"].close()
        if len(data) > 128 * 1024:
            raise ValueError("Ficha demasiado grande")
        record = json.loads(data)
        if self.ficha_key(record["id"]) != key:
            raise ValueError("Identificador incoherente")
        return from_record(record, self.prefix)

    def list_all(self):
        try:
            result = []
            pages = self.client.get_paginator("list_objects_v2").paginate(
                Bucket=self.bucket, Prefix=f"{self.prefix}/fichas/")
            for page in pages:
                for obj in page.get("Contents", []):
                    if obj["Key"].endswith(".json"):
                        result.append(self._read_record(obj["Key"]))
            return sorted(result, key=lambda r: r["registro"]["fecha"], reverse=True)
        except (BotoCoreError, ClientError, ValueError, KeyError, TypeError, AttributeError, NotFound) as exc:
            log.warning("No se pudo leer el catálogo: %s", type(exc).__name__)
            raise StorageError("No se pudo leer el catálogo. Revisa conexión, credenciales, permisos y fichas de S3.") from exc

    def get(self, document_id):
        key = self.ficha_key(document_id)
        try:
            return self._read_record(key)
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("NoSuchKey", "404"):
                raise NotFound() from exc
            raise StorageError("No se pudo acceder al documento en S3.") from exc
        except (BotoCoreError, ValueError, KeyError, TypeError, AttributeError, NotFound) as exc:
            raise StorageError("No se pudo leer la ficha del documento.") from exc

    def save(self, document, content):
        """Original primero; ficha como confirmación. Nunca reemplaza originales."""
        record = to_record(document, self.prefix)
        key = record["archivo"]["clave_s3"]
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=content,
                ContentType=record["archivo"]["tipo_mime"], ServerSideEncryption="AES256", IfNoneMatch="*")
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"No se confirmó la subida del original. No se ha creado la ficha; revisa posibles archivos huérfanos antes de reintentar. Operación: {document['id']}") from exc
        try:
            self.client.put_object(Bucket=self.bucket, Key=self.ficha_key(record["id"]),
                Body=json.dumps(record, ensure_ascii=False).encode("utf-8"),
                ContentType="application/json", ServerSideEncryption="AES256", IfNoneMatch="*")
        except (BotoCoreError, ClientError) as exc:
            # Una respuesta perdida no demuestra que el PUT haya fallado.
            # Antes de borrar el original, comprobamos si la ficha se guardó.
            try:
                saved = self.get(record["id"])
            except NotFound:
                try:
                    self.client.delete_object(Bucket=self.bucket, Key=key)
                except (BotoCoreError, ClientError):
                    log.error("Original sin ficha pendiente de limpieza: %s", key)
                    raise StorageError(f"No se guardó la ficha y no se pudo retirar el original. Incidencia {document['id']}: requiere revisión técnica.") from exc
                raise StorageError("No se guardó la ficha. La carga no se ha confirmado; puedes reintentar.") from exc
            except StorageError:
                log.error("Carga con resultado incierto: %s", record["id"])
                raise StorageError(f"No se pudo confirmar la carga. Consulta el catálogo antes de reintentar; el original se conserva. Operación: {document['id']}.") from exc
            if saved != document:
                raise StorageError("Conflicto al confirmar la ficha. Requiere revisión técnica.") from exc

    def download(self, document, max_bytes):
        try:
            record = to_record(document, self.prefix)
        except (ValueError, KeyError, TypeError, AttributeError, NotFound) as exc:
            raise StorageError("La ficha contiene una referencia no permitida.") from exc
        key = record["archivo"]["clave_s3"]
        if not key.startswith(f"{self.prefix}/originales/{record['id']}/original."):
            raise StorageError("La ficha contiene una referencia no permitida.")
        try:
            obj = self.client.get_object(Bucket=self.bucket, Key=key)
            try:
                data = obj["Body"].read(max_bytes + 1)
            finally:
                obj["Body"].close()
            import hashlib
            if len(data) > max_bytes or len(data) != record["archivo"]["tamano_bytes"] or hashlib.sha256(data).hexdigest() != record["archivo"]["sha256"]:
                raise StorageError("El original no coincide con la huella o supera el límite configurado.")
            return data
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("No se pudo descargar el original desde S3.") from exc
