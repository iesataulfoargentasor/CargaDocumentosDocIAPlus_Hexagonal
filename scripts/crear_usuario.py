"""Con el servidor detenido. Contraseña oculta, sin argumentos ni valores comunes."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import tempfile
import warnings
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]

def create_user(username,password,reader=False):
    if not re.fullmatch(r'[a-zA-Z0-9_.-]{3,40}',username) or not 12 <= len(password) <= 256:
        raise ValueError('Usuario de 3–40 letras/números/._- y contraseña de 12–256 caracteres.')
    path = ROOT/'instance/users.json'
    path.parent.mkdir(mode=0o700,exist_ok=True)
    users = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if username in users:
        raise ValueError('La cuenta ya existe; no se sobrescribirá.')
    users[username] = dict(password_hash=generate_password_hash(password,method='scrypt'),active=True,permissions=['read'] if reader else ['read','upload'])
    fd,temp = tempfile.mkstemp(dir=path.parent,prefix='.users-')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as output:
            json.dump(users,output,indent=2)
        os.replace(temp,path)
    finally:
        if os.path.exists(temp): os.unlink(temp)

def main():
    parser = argparse.ArgumentParser(description='Crear una cuenta autorizada')
    parser.add_argument('usuario',nargs='?')
    parser.add_argument('--solo-lectura',action='store_true')
    args = parser.parse_args()
    try:
        username = args.usuario or input('Nombre de usuario: ').strip()
        with warnings.catch_warnings():
            warnings.simplefilter('error',getpass.GetPassWarning)
            password = getpass.getpass('Contraseña (12–256 caracteres): ')
            if password != getpass.getpass('Repite la contraseña: '):
                raise ValueError('Las contraseñas no coinciden.')
        create_user(username,password,args.solo_lectura)
    except (ValueError,OSError,getpass.GetPassWarning,EOFError,KeyboardInterrupt) as exc:
        print('No se creó la cuenta. Usa un terminal con entrada oculta y revisa usuario/contraseña y permisos del archivo.')
        return 1
    print('Cuenta creada. No se han enviado datos a AWS.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
