from app.adapters.persistence.record_mapper import to_record
import io
import json
import pytest
from docx import Document
from pypdf import PdfWriter
from conftest import login, upload


def test_access_csrf_permissions(env):
    _, c, s3, _ = env
    assert c.get('/').status_code == 302
    assert c.get('/programaciones/nueva').status_code == 302
    assert c.get('/programaciones/no-id/descargar').status_code == 302
    assert c.post('/login', data={'username': 'docente'}).status_code == 400
    login(c, 'lector')
    assert c.get('/programaciones/nueva').status_code == 403
    assert upload(c).status_code == 403
    assert not s3.objects


def test_upload_catalog_detail_download_and_duplicate(env):
    _, c, s3, repo = env
    login(c)
    result = upload(c)
    assert result.status_code == 302
    detail = c.get(result.location)
    assert 'Programación de SBD'.encode() in detail.data
    record = repo.list_all()[0]
    assert record['registro']['usuario'] == 'docente'
    assert len(record['archivo']['sha256']) == 64
    assert c.get(result.location+'/descargar').data == b'Programacion de prueba para SBD'
    assert 'attachment' in c.get(result.location+'/descargar').headers['Content-Disposition']
    assert upload(c, filename='otro_nombre.txt').status_code == 409
    assert len(repo.list_all()) == 1
    assert len(s3.objects) == 2
    assert b'No hay documentos' in c.get('/?modulo=PIA').data
    assert b'nosniff' == c.get('/').headers['X-Content-Type-Options'].encode()


def test_duplicate_context_mismatch(env):
    _, c, _, _ = env
    login(c); upload(c)
    r = upload(c, curso_academico='2025-2026')
    assert r.status_code == 409
    assert b'no coinciden' in r.data


def test_revision_requires_explicit_relation_preserves_original(env):
    _, c, _, repo = env
    login(c); upload(c)
    first = repo.list_all()[0]
    r = upload(c, content=b'Nueva programacion corregida')
    assert r.status_code == 422
    assert b'relacion_id' in r.data
    assert len(repo.list_all()) == 1
    assert upload(c, content=b'Nueva programacion corregida', relacion_id=first['id'],
                  relacion_tipo='revision', relacion_motivo='Correcciones del apartado dos').status_code == 302
    records = repo.list_all()
    assert len(records) == 2
    assert records[0]['relacion']['documento_id'] == first['id']
    assert repo.download(first, 1000) == b'Programacion de prueba para SBD'


def test_forged_relation_rejected(env):
    _, c, _, repo = env
    login(c); upload(c)
    assert upload(c, content=b'Documento diferente', relacion_id='inventado', relacion_tipo='revision', relacion_motivo='Un motivo').status_code == 422
    assert len(repo.list_all()) == 1


@pytest.mark.parametrize('filename,content', [('vacío.txt',b''), ('falso.pdf',b'no es PDF'),
    ('macro.docm',b'contenido'),('falso.docx',b'no es DOCX'),('binario.txt',b'abc\x00\x01'),('latin.txt',b'\xff\xfe')])
def test_rejected_files(env, filename, content):
    _, c, s3, _ = env
    login(c)
    assert upload(c, content=content, filename=filename).status_code == 422
    assert not s3.objects


def test_metadata_mismatch_and_limits(env):
    app, c, s3, _ = env
    login(c)
    for fields in [{'titulo': 'a'}, {'procedencia': ''}, {'modulo': 'INVENTADO'}, {'ensenanza': 'otra'}, {'curso_academico': '2020'}, {'estado_declarado': 'aprobado'}]:
        assert upload(c, **fields).status_code == 422
    app.config['MAX_FILE_BYTES'] = 10
    app.extensions['documents'].max_bytes = 10
    assert upload(c).status_code == 422
    app.config['MAX_CONTENT_LENGTH'] = 100
    assert upload(c).status_code == 413
    assert not s3.objects


def test_blank_pdf_and_docx_accepted_encrypted_rejected(env):
    _, c, _, repo = env
    login(c)
    writer = PdfWriter(); writer.add_blank_page(width=100,height=100)
    buf = io.BytesIO(); writer.write(buf)
    assert upload(c, content=buf.getvalue(), filename='pagina_blanca.pdf').status_code == 302
    doc = Document(); doc.add_paragraph('Programacion de ejemplo')
    buf = io.BytesIO(); doc.save(buf)
    assert upload(c, content=buf.getvalue(), filename='texto.docx', modulo='BDA').status_code == 302
    writer.encrypt('secreto'); buf = io.BytesIO(); writer.write(buf)
    assert upload(c, content=buf.getvalue(), filename='protegido.pdf').status_code == 422
    assert len(repo.list_all()) == 2


def test_s3_failures_no_false_success_and_cleanup(env):
    _, c, s3, _ = env
    login(c)
    s3.fail_ficha = True
    r = upload(c)
    assert r.status_code == 503
    assert not s3.objects
    assert b'correctamente' not in r.data
    s3.fail_ficha = False; s3.fail_catalog = True
    assert c.get('/').status_code == 503
    assert upload(c).status_code == 503
    assert not s3.objects


def test_lost_success_response_keeps_valid_original(env):
    _, c, s3, repo = env
    login(c); s3.lose_response = True
    assert upload(c).status_code == 302
    assert len(s3.objects) == 2
    record = repo.list_all()[0]
    assert repo.download(record, 1000)


def test_xss_escaped_and_download_integrity(env):
    _, c, s3, repo = env
    login(c); r=upload(c, titulo='<script>alert(1)</script>')
    assert b'<script>' not in c.get(r.location).data
    assert b'&lt;script&gt;' in c.get(r.location).data
    record=repo.list_all()[0]
    s3.objects[to_record(record,repo.prefix)['archivo']['clave_s3']]=b'alterado'
    assert c.get(r.location+'/descargar').status_code == 503
    assert c.get('/programaciones/no-id').status_code == 404


def test_logout_and_revoked_permissions(env):
    app,c,_,_=env
    login(c)
    with c.session_transaction() as session: token=session['csrf']
    assert c.post('/logout',data={'csrf_token':token}).status_code==302
    assert c.get('/').status_code==302
    login(c)
    from pathlib import Path
    p=Path(app.config['USERS_FILE']); users=json.loads(p.read_text()); users['docente']['active']=False; p.write_text(json.dumps(users))
    assert c.get('/').status_code==302


def test_parallel_duplicate_only_saves_once(env):
    from concurrent.futures import ThreadPoolExecutor
    from app.application.dto import UploadCommand
    from app.domain.errors import Duplicate
    from app.domain.user import User
    app,_,_,repo=env
    service=app.extensions['documents']
    metadata={'ensenanza':'IABD','modulo':'SBD','curso_academico':'2026-2027','titulo':'Una prueba','estado_declarado':'final','procedencia':'Departamento'}
    def execute():
        try:
            service.create(User('docente',frozenset({'read','upload'})),UploadCommand(metadata,io.BytesIO(b'contenido'),'a.txt'))
            return 'saved'
        except Duplicate:
            return 'duplicate'
    with ThreadPoolExecutor(2) as pool: results=list(pool.map(lambda _:execute(),range(2)))
    assert sorted(results)==['duplicate','saved']
    assert len(repo.list_all())==1
