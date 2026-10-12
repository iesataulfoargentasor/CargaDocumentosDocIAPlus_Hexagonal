"""Cuenta exclusiva de demostración. Credenciales aleatorias, locales y privadas."""
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash
from preparar_local import prepare

ROOT = Path(__file__).resolve().parents[1]

def prepare_demo():
    prepare()
    path = ROOT/'instance/demo-access.json'
    users = ROOT/'instance/users-demo.json'
    if not path.exists() or not users.exists():
        access = dict(username='demo',password=secrets.token_urlsafe(18))
        for target,data in [(users,{'demo':dict(password_hash=generate_password_hash(access['password']),active=True,permissions=['read','upload'])}),(path,access)]:
            with os.fdopen(os.open(target,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600),'w',encoding='utf-8') as output:
                json.dump(data,output)
            os.chmod(target,0o600)
    access = json.loads(path.read_text())
    return access

def main():
    access = prepare_demo()
    print('\nDEMOSTRACIÓN LOCAL: los documentos se pierden al cerrar; no utiliza AWS.')
    print('Usuario:',access['username'])
    print('Contraseña local de demostración:',access['password'],flush=True)
    try:
        return subprocess.call([sys.executable,str(ROOT/'run.py'),'--demo','--open'],cwd=ROOT)
    except KeyboardInterrupt:
        return 0

if __name__ == '__main__':
    raise SystemExit(main())
