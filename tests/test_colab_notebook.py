"""Validación del cuaderno sin credenciales, red ni recursos AWS."""
import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from botocore.exceptions import ClientError

PATH = Path(__file__).resolve().parents[1] / 'Crear_bucket_S3_AWS_Academy.ipynb'

def functions():
    notebook = json.loads(PATH.read_text())
    source = next(''.join(c['source']) for c in notebook['cells']
                  if c['cell_type'] == 'code' and 'def parametros_creacion' in ''.join(c['source']))
    namespace = {}
    exec(compile(source, 'funciones_colab', 'exec'), namespace)
    return namespace


def test_notebook_clean_and_compiles():
    nb = json.loads(PATH.read_text())
    assert nb['nbformat'] == 4
    for c in nb['cells']:
        if c['cell_type'] == 'code':
            assert c['outputs'] == [] and c['execution_count'] is None
            code = ''.join(c['source'])
            if not code.startswith('%pip'):
                compile(code, c['id'], 'exec')
    source = '\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code')
    assert source.count('getpass.getpass(') == 3
    assert 'aws_session_token=token' in source
    assert 'write_text(' not in source


def test_creation_region_and_names():
    ns = functions()
    p = ns['parametros_creacion']('docia-prueba-1234','us-east-1')
    assert 'CreateBucketConfiguration' not in p
    assert p['ObjectOwnership'] == 'BucketOwnerEnforced'
    p = ns['parametros_creacion']('docia-prueba-1234','eu-west-1')
    assert p['CreateBucketConfiguration'] == {'LocationConstraint':'eu-west-1'}
    for invalid in ['AA', 'nombre.con.puntos', 'nombre_', 'xn--reservado', 'docia--x-s3']:
        with pytest.raises(ns['ErrorCuaderno']): ns['validar_nombre_bucket'](invalid)


def test_403_never_creates_or_modifies_bucket():
    ns=functions(); client=Mock()
    client.head_bucket.side_effect=ClientError({'Error':{'Code':'403'}},'HeadBucket')
    with pytest.raises(ClientError): ns['crear_o_reutilizar'](client,'docia-prueba','us-east-1','123456789012')
    client.create_bucket.assert_not_called()


def test_missing_creates_and_existing_reuses():
    ns=functions(); client=Mock()
    client.head_bucket.side_effect=ClientError({'Error':{'Code':'404'}},'HeadBucket')
    assert ns['crear_o_reutilizar'](client,'docia-prueba','us-east-1','123456789012')=='creado'
    client.create_bucket.assert_called_once_with(Bucket='docia-prueba',ObjectOwnership='BucketOwnerEnforced')
    client=Mock(); client.head_bucket.return_value={'BucketRegion':'eu-west-1'}
    assert ns['crear_o_reutilizar'](client,'docia-prueba','eu-west-1','123456789012')=='reutilizado'
    client.create_bucket.assert_not_called()
    with pytest.raises(ns['ErrorCuaderno']): ns['crear_o_reutilizar'](client,'docia-prueba','us-east-1','123456789012')


def configured_client(ns):
    c=Mock()
    c.get_public_access_block.return_value={'PublicAccessBlockConfiguration':ns['CONFIG_BLOQUEO']}
    c.get_bucket_ownership_controls.return_value={'OwnershipControls':{'Rules':[{'ObjectOwnership':'BucketOwnerEnforced'}]}}
    c.get_bucket_encryption.return_value={'ServerSideEncryptionConfiguration':{'Rules':[{'ApplyServerSideEncryptionByDefault':{'SSEAlgorithm':'AES256'}}]}}
    return c


def test_defaults_verified_without_extra_write_permissions():
    ns=functions(); c=configured_client(ns)
    assert ns['configurar_y_verificar'](c,'docia-prueba','123456789012')
    c.put_public_access_block.assert_not_called()
    c.put_bucket_encryption.assert_not_called()
    c.put_bucket_ownership_controls.assert_not_called()


def test_refuses_kms_change_or_unverified_privacy():
    ns=functions(); c=configured_client(ns)
    c.get_bucket_encryption.return_value={'ServerSideEncryptionConfiguration':{'Rules':[{'ApplyServerSideEncryptionByDefault':{'SSEAlgorithm':'aws:kms'}}]}}
    with pytest.raises(ns['ErrorCuaderno']): ns['configurar_y_verificar'](c,'docia-prueba','123456789012')
    c.put_bucket_encryption.assert_not_called()
    c=configured_client(ns)
    c.get_public_access_block.return_value={'PublicAccessBlockConfiguration':{}}
    with pytest.raises(ns['ErrorCuaderno']): ns['configurar_y_verificar'](c,'docia-prueba','123456789012')
    c.put_public_access_block.assert_called_once()
