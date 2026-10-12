"""Asistente interactivo: las credenciales se introducen ocultas, fuera del chat."""
from pathlib import Path
import getpass
import json
import os
import sys
import warnings
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]

def main():
    path = ROOT / '.env'
    settings = dict(dotenv_values(path))
    bucket = settings.get('S3_BUCKET')
    region = settings.get('AWS_DEFAULT_REGION', 'us-east-1')
    if not bucket:
        print('Configura antes S3_BUCKET en .env.'); return 1
    print('Configuración local de AWS Academy')
    print('Bucket:', bucket, '· Región:', region)
    print('Pega solo los valores. Se guardarán en el .env privado de este ordenador; nunca se mostrarán.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            access = getpass.getpass('AWS Access Key ID: ').strip()
            secret = getpass.getpass('AWS Secret Access Key: ').strip()
            token = getpass.getpass('AWS Session Token: ').strip()
        if not all((access, secret, token)):
            print('Falta alguna de las tres credenciales. No se guardó nada.'); return 1
        session = boto3.Session(aws_access_key_id=access, aws_secret_access_key=secret,
                               aws_session_token=token, region_name=region)
        cfg = Config(connect_timeout=8, read_timeout=15, retries={'max_attempts':1})
        account = session.client('sts',config=cfg).get_caller_identity()['Account']
        client = session.client('s3',config=cfg)
        client.head_bucket(Bucket=bucket,ExpectedBucketOwner=account)
        client.list_objects_v2(Bucket=bucket,Prefix=settings.get('S3_PREFIX','programaciones')+'/fichas/',MaxKeys=1,ExpectedBucketOwner=account)
    except getpass.GetPassWarning:
        print('Usa un terminal con entrada oculta. No se guardó nada.'); return 1
    except (BotoCoreError, ClientError, ValueError):
        print('No se pudo validar el acceso. Revisa credenciales vigentes, red y permisos del laboratorio. No se guardó nada.'); return 1
    except (KeyboardInterrupt, EOFError):
        print('\nConfiguración cancelada.'); return 1
    settings.pop('AWS_PROFILE',None)
    settings.update(AWS_ACCESS_KEY_ID=access,AWS_SECRET_ACCESS_KEY=secret,AWS_SESSION_TOKEN=token)
    tmp = path.with_suffix('.env.tmp')
    with os.fdopen(os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600),'w') as output:
        output.write('\n'.join(k+'='+json.dumps(v,ensure_ascii=False) for k,v in settings.items() if v is not None)+'\n')
    os.replace(tmp,path);os.chmod(path,0o600)
    print('Credenciales verificadas y guardadas. Reinicia la aplicación para utilizarlas.')
    print('Se ha comprobado el acceso al bucket y su catálogo; todavía no se han subido archivos.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
