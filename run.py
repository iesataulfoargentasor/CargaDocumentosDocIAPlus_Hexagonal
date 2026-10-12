"""Waitress: un proceso, cuatro hilos. Iniciar desde cualquier directorio."""
import argparse
import hashlib
import os
from pathlib import Path
import threading
import webbrowser
from waitress import serve
from app import create_app
from app.config import ROOT, settings

def acquire_lock(config):
    # Impide dobles lanzamientos de ESTA instalación, incluso en puertos diferentes.
    key = hashlib.sha256((config['STORAGE_BACKEND']+'|'+config['S3_BUCKET']+'|'+config['S3_PREFIX']).encode()).hexdigest()[:20]
    path = ROOT/'instance'/f'writer-{key}.lock'
    path.parent.mkdir(mode=0o700,exist_ok=True)
    handle = open(path,'a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            handle.write(b'0'); handle.flush(); handle.seek(0)
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise RuntimeError('Esta instalación ya tiene un servidor para ese destino. Cierra su terminal antes de reiniciar.')
    return handle

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--demo',action='store_true')
    parser.add_argument('--open',action='store_true')
    args = parser.parse_args()
    config = settings()
    if args.demo:
        config.update(STORAGE_BACKEND='memory',USERS_FILE=str(ROOT/'instance/users-demo.json'))
    if config['STORAGE_BACKEND']=='s3' and not config['S3_BUCKET']:
        raise RuntimeError('Configura S3_BUCKET en .env antes de iniciar con AWS.')
    if not Path(config['USERS_FILE']).exists():
        raise RuntimeError('Crea una cuenta con Crear_usuario.command (o inicia Iniciar_demo.command para la demostración).')
    with acquire_lock(config):
        app = create_app(config)
        host,port = config['HOST'],config['PORT']
        url = f'http://{host}:{port}'
        print(f'DocIA+ Hexagonal · {config["STORAGE_BACKEND"]} · {url}',flush=True)
        print('Para detener: Ctrl+C. Mantén una única instancia escritora por bucket/prefijo.',flush=True)
        if args.open:
            timer=threading.Timer(1.0,lambda:webbrowser.open(url)); timer.daemon=True; timer.start()
        serve(app,host=host,port=port,threads=4,max_request_body_size=app.config['MAX_CONTENT_LENGTH'])

if __name__=='__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except (RuntimeError,OSError) as exc:
        raise SystemExit(str(exc))
