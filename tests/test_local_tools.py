"""Asistentes locales y garantías de arranque; sin credenciales reales ni red."""
import getpass
import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock
import warnings
import pytest
from dotenv import dotenv_values
from botocore.exceptions import ClientError

ROOT=Path(__file__).resolve().parents[1]

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def test_prepare_idempotent_secret_private(tmp_path,monkeypatch):
    prepare=module('scripts/preparar_local.py','prepare_test')
    (tmp_path/'.env.example').write_text('SECRET_KEY=REEMPLAZAR_POR_UNA_CLAVE_ALEATORIA\n')
    monkeypatch.setattr(prepare,'ROOT',tmp_path)
    assert prepare.prepare()
    first=(tmp_path/'.env').read_bytes()
    assert len(dotenv_values(tmp_path/'.env')['SECRET_KEY'])==64
    assert not prepare.prepare() and (tmp_path/'.env').read_bytes()==first
    import os
    if os.name!='nt':assert (tmp_path/'.env').stat().st_mode & 0o077 == 0


def test_create_user_does_not_overwrite_or_store_plaintext(tmp_path,monkeypatch):
    users=module('scripts/crear_usuario.py','users_test');monkeypatch.setattr(users,'ROOT',tmp_path)
    users.create_user('lector','contraseña-local-de-prueba',reader=True)
    path=tmp_path/'instance/users.json';before=path.read_bytes()
    assert b'contrase' not in before and json.loads(before)['lector']['permissions']==['read']
    assert json.loads(before)['lector']['password_hash'].startswith('scrypt:')
    with pytest.raises(ValueError):users.create_user('lector','otra-clave-de-prueba')
    with pytest.raises(ValueError):users.create_user('nuevo','corta')
    assert path.read_bytes()==before

@pytest.mark.parametrize('kind',['unhidden','invalid_session','valid'])
def test_aws_assistant_atomic_and_secret_safe(kind,tmp_path,monkeypatch,capsys):
    aws=module('scripts/configurar_aws.py','aws_test');monkeypatch.setattr(aws,'ROOT',tmp_path)
    env=tmp_path/'.env';env.write_text('SECRET_KEY=local-existing-key\nS3_BUCKET=bucket-test\nAWS_DEFAULT_REGION=us-east-1\nS3_PREFIX=programaciones-hexagonal\nAWS_PROFILE=old-profile\n')
    before=env.read_bytes()
    inputs=iter(['synthetic-access','synthetic-secret','synthetic-token'])
    if kind=='unhidden':
        def unhidden(*a):warnings.warn('Not hidden',getpass.GetPassWarning)
        monkeypatch.setattr(aws.getpass,'getpass',unhidden)
    else:monkeypatch.setattr(aws.getpass,'getpass',lambda *a:next(inputs))
    client=Mock();client.get_caller_identity.return_value={'Account':'123456789012'}
    session=Mock();session.client.return_value=client
    monkeypatch.setattr(aws.boto3,'Session',lambda **kw:session)
    if kind=='invalid_session':client.get_caller_identity.side_effect=ClientError({'Error':{'Code':'ExpiredToken'}},'GetCallerIdentity')
    result=aws.main();out=capsys.readouterr().out
    assert all(secret not in out for secret in ['synthetic-access','synthetic-secret','synthetic-token'])
    client.put_object.assert_not_called()
    if kind=='valid':
        assert result==0
        values=dotenv_values(env)
        assert values['AWS_SESSION_TOKEN']=='synthetic-token' and 'AWS_PROFILE' not in values
        assert values['SECRET_KEY']=='local-existing-key'
        client.head_bucket.assert_called_once_with(Bucket='bucket-test',ExpectedBucketOwner='123456789012')
    else:assert result==1 and env.read_bytes()==before


def test_single_installation_cannot_start_two_writers(tmp_path,monkeypatch):
    run=module('run.py','run_test');monkeypatch.setattr(run,'ROOT',tmp_path)
    config=dict(STORAGE_BACKEND='s3',S3_BUCKET='bucket',S3_PREFIX='prefix')
    with run.acquire_lock(config):
        with pytest.raises(RuntimeError):run.acquire_lock(config)
    with run.acquire_lock(config):pass
