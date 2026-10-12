"""Configuración exterior al núcleo; las pruebas no leen .env ni AWS del equipo."""
import json
import os
from datetime import timedelta
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]

def settings(test_config=None):
    env = {} if test_config is not None else {**dotenv_values(ROOT / '.env'), **os.environ}
    values = dict(
        SECRET_KEY=env.get('SECRET_KEY'), CENTRO=env.get('CENTRO', 'IES Ataúlfo Argenta'),
        S3_BUCKET=env.get('S3_BUCKET',''), S3_PREFIX=env.get('S3_PREFIX','programaciones-hexagonal').strip('/'),
        AWS_REGION=env.get('AWS_DEFAULT_REGION','us-east-1'), STORAGE_BACKEND=env.get('STORAGE_BACKEND','s3'),
        MAX_FILE_BYTES=int(env.get('MAX_FILE_MB','20')) * 1024 * 1024,
        HOST=env.get('HOST','127.0.0.1'), PORT=int(env.get('PORT','5053')),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=env.get('COOKIE_SECURE','false').lower() == 'true',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
        USERS_FILE=str(ROOT / 'instance/users.json'),
        CATALOG=json.loads((ROOT / 'config/catalogo.json').read_text(encoding='utf-8')),
        AWS_OPTIONS={k:env[k] for k in ('AWS_PROFILE','AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_SESSION_TOKEN') if env.get(k)},
    )
    if test_config is not None:
        values.update(test_config)
    if not values['SECRET_KEY'] or len(values['SECRET_KEY']) < 32 or values['SECRET_KEY'].startswith('REEMPLAZAR'):
        raise RuntimeError('Ejecuta scripts/preparar_local.py para generar .env con una SECRET_KEY privada.')
    if not values['S3_PREFIX'] or any(p in ('.','..','') for p in values['S3_PREFIX'].split('/')):
        raise RuntimeError('S3_PREFIX debe ser un prefijo no vacío, sin segmentos . o ...')
    if values['STORAGE_BACKEND'] not in ('s3','memory'):
        raise RuntimeError('STORAGE_BACKEND debe ser s3 o memory.')
    if values['MAX_FILE_BYTES'] <= 0 or not 1 <= values['PORT'] <= 65535:
        raise RuntimeError('Revisa MAX_FILE_MB y PORT.')
    values.update(MAX_CONTENT_LENGTH=values['MAX_FILE_BYTES'] + 1024 * 1024, MAX_FORM_MEMORY_SIZE=128 * 1024, MAX_FORM_PARTS=30)
    return values
