"""Entrada diferida: importar app.domain no importa Flask ni adaptadores."""
def create_app(test_config=None, repository=None):
    from app.adapters.web.factory import create_web_app
    return create_web_app(test_config, repository)
