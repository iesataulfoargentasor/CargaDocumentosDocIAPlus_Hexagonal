"""Sesiones, permisos, CSRF y límite básico de intentos para el piloto local."""
import hmac
import secrets
import time
from functools import wraps
from threading import Lock
from flask import abort, current_app, g, redirect, request, session, url_for

class LoginLimiter:
    def __init__(self):
        self.attempts = {}
        self.lock = Lock()

    def blocked(self, ip):
        with self.lock:
            now = time.monotonic()
            self.attempts = {k: [t for t in ts if now-t < 300] for k, ts in self.attempts.items() if ts and now-ts[-1] < 300}
            return len(self.attempts.get(ip, [])) >= 10

    def fail(self, ip):
        with self.lock:
            self.attempts.setdefault(ip, []).append(time.monotonic())

def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]

def protect_request():
    g.user = current_app.extensions["auth_service"].get_user(session.get("username", ""))
    if request.method == "POST":
        expected = session.get("csrf", "")
        if not expected or not hmac.compare_digest(expected.encode("utf-8"), request.form.get("csrf_token", "").encode("utf-8")):
            abort(400, description="La sesión del formulario ha caducado. Recarga la página e inténtalo de nuevo.")

def permission_required(permission):
    def decorate(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not g.user:
                return redirect(url_for("auth.login"))
            if permission not in g.user.permissions:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorate
