"""Preparación idempotente: nunca lee ni copia secretos de otra aplicación."""
from pathlib import Path
import os
import secrets

ROOT = Path(__file__).resolve().parents[1]

def prepare():
    (ROOT/'instance').mkdir(mode=0o700,exist_ok=True)
    path = ROOT/'.env'
    if path.exists():
        return False
    text = (ROOT/'.env.example').read_text(encoding='utf-8').replace('REEMPLAZAR_POR_UNA_CLAVE_ALEATORIA',secrets.token_hex(32))
    with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as file:
        file.write(text)
    return True

if __name__ == '__main__':
    print('Configuración privada creada.' if prepare() else '.env ya existe; se conserva sin cambios.')
