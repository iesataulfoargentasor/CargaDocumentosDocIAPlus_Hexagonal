from flask import Flask, render_template
from app.config import ROOT, settings
from app.bootstrap import compose
from app.domain.errors import StorageError, NotFound, PermissionDenied
from app.adapters.web.security import LoginLimiter, csrf_token, protect_request

def create_web_app(test_config=None, repository=None):
    app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static', instance_path=str(ROOT/'instance'))
    app.config.update(settings(test_config))
    documents, auth = compose(app.config, repository)
    app.extensions.update(documents=documents, auth_service=auth, login_limiter=LoginLimiter())
    app.before_request(protect_request)
    app.jinja_env.globals['csrf_token'] = csrf_token

    @app.context_processor
    def context():
        return dict(catalog=app.config['CATALOG'], center=app.config['CENTRO'], max_file_mb=app.config['MAX_FILE_BYTES']//(1024*1024), demo_mode=app.config['STORAGE_BACKEND']=='memory')

    from app.adapters.web.controllers.auth_controller import auth as auth_blueprint
    from app.adapters.web.controllers.document_controller import documents as documents_blueprint
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(documents_blueprint)

    @app.after_request
    def headers(response):
        response.headers.update({'X-Content-Type-Options':'nosniff', 'X-Frame-Options':'DENY', 'Referrer-Policy':'same-origin', 'Cache-Control':'no-store', 'Content-Security-Policy':"default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"})
        return response

    @app.errorhandler(StorageError)
    def storage_error(error):
        return render_template('error.html',title='No se pudo completar la operación',message=str(error)),503

    @app.errorhandler(NotFound)
    def not_found(error):
        return render_template('error.html',title='Documento no encontrado',message='Revisa el enlace o vuelve al catálogo.'),404

    @app.errorhandler(PermissionDenied)
    def forbidden(error):
        return render_template('error.html',title='Acceso denegado',message=str(error)),403

    for code,title,message in [(400,'Formulario no válido','Recarga la página y vuelve a intentarlo.'),(403,'Acceso denegado','Tu cuenta no tiene permiso para esta operación.'),(404,'Página no encontrada','Vuelve al catálogo para continuar.'),(413,'Carga demasiado grande','El archivo o la petición supera el límite configurado.'),(500,'Error interno','No se ha confirmado la operación. Consulta el catálogo antes de repetirla.')]:
        def handler(error,code=code,title=title,message=message):
            return render_template('error.html',title=title,message=message),code
        app.register_error_handler(code,handler)
    return app
