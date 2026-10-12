from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from app.adapters.web.security import csrf_token

auth = Blueprint("auth", __name__)

@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        limiter = current_app.extensions["login_limiter"]
        ip = request.remote_addr or "local"
        if limiter.blocked(ip):
            return render_template("auth/login.html", error="Demasiados intentos. Espera cinco minutos."), 429
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = current_app.extensions["auth_service"].authenticate(username, password)
        if user and len(password) <= 256:
            session.clear()
            session["username"] = username
            session.permanent = True
            csrf_token()
            return redirect(url_for("documents.catalog"))
        limiter.fail(ip)
        return render_template("auth/login.html", error="Usuario o contraseña incorrectos, o cuenta desactivada."), 401
    return render_template("auth/login.html")

@auth.post("/logout")
def logout():
    session.clear()
    flash("Has cerrado la sesión.", "info")
    return redirect(url_for("auth.login"))
