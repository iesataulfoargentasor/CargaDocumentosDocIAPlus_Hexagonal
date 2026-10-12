import io
import json
import pytest
from botocore.exceptions import ClientError
from werkzeug.security import generate_password_hash
from app import create_app
from app.adapters.persistence.s3_repository import S3Repository

class FakeS3:
    """Doble S3 en memoria SOLO para pruebas; nunca conecta con AWS."""
    def __init__(self):
        self.objects = {}
        self.fail_ficha = False
        self.lose_response = False
        self.fail_catalog = False
        self.calls = []

    def put_object(self, **kw):
        self.calls.append(('put', kw))
        key = kw['Key']
        if self.fail_ficha and '/fichas/' in key:
            raise ClientError({'Error': {'Code': 'AccessDenied'}}, 'PutObject')
        if kw.get('IfNoneMatch') == '*' and key in self.objects:
            raise ClientError({'Error': {'Code': 'PreconditionFailed'}}, 'PutObject')
        self.objects[key] = kw['Body']
        if self.lose_response and '/fichas/' in key:
            raise ClientError({'Error': {'Code': 'RequestTimeout'}}, 'PutObject')
        return {}

    def get_object(self, **kw):
        if kw['Key'] not in self.objects:
            raise ClientError({'Error': {'Code': 'NoSuchKey'}}, 'GetObject')
        return {'Body': io.BytesIO(self.objects[kw['Key']])}

    def delete_object(self, **kw):
        self.objects.pop(kw['Key'], None)

    def get_paginator(self, operation):
        assert operation == 'list_objects_v2'
        return self

    def paginate(self, **kw):
        if self.fail_catalog:
            raise ClientError({'Error': {'Code': 'ExpiredToken'}}, 'ListObjectsV2')
        # Deliberadamente una ficha por página para verificar la paginación.
        for key in sorted(self.objects):
            if key.startswith(kw['Prefix']):
                yield {'Contents': [{'Key': key}]}

@pytest.fixture
def env(tmp_path):
    userfile = tmp_path/'users.json'
    userfile.write_text(json.dumps({'docente': {'password_hash': generate_password_hash('una-clave-de-pruebas'),
        'active': True, 'permissions': ['read', 'upload']},
        'lector': {'password_hash': generate_password_hash('una-clave-de-pruebas'), 'active': True, 'permissions': ['read']}}))
    s3 = FakeS3()
    repository = S3Repository('bucket-test', client=s3)
    app = create_app({'TESTING': True, 'SECRET_KEY': 't'*64, 'USERS_FILE': str(userfile)}, repository=repository)
    return app, app.test_client(), s3, repository

def login(client, username='docente'):
    client.get('/login')
    with client.session_transaction() as session:
        token = session['csrf']
    return client.post('/login', data={'csrf_token': token, 'username': username, 'password': 'una-clave-de-pruebas'})

def upload(client, content=b'Programacion de prueba para SBD', filename='programacion.txt', **extra):
    with client.session_transaction() as session:
        token = session.get('csrf', '')
    data = {'csrf_token': token, 'titulo': 'Programación de SBD', 'ensenanza': 'IABD', 'modulo': 'SBD',
        'curso_academico': '2026-2027', 'estado_declarado': 'final', 'procedencia': 'Departamento de informática',
        'archivo': (io.BytesIO(content), filename), **extra}
    return client.post('/programaciones/nueva', data=data, content_type='multipart/form-data')


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket
    monkeypatch.setenv('AWS_EC2_METADATA_DISABLED','true')
    def forbidden(*args,**kwargs):
        raise AssertionError('Prueba no aislada: intento de red')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
