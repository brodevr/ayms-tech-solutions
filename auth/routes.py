import os

from flask import Blueprint, redirect, url_for, session, flash
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db, oauth
from models import Usuario, ROL_ADMIN, ROL_CLIENTE

auth_bp = Blueprint("auth", __name__)


def init_oauth(app):
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def _emails_admin():
    raw = os.getenv("ADMIN_EMAILS") or os.getenv("ADMIN_EMAIL", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def destino_por_rol(usuario):
    return url_for("admin_dashboard" if usuario.es_admin else "mis_solicitudes")


@auth_bp.route("/login")
def login():
    if current_user.is_authenticated:
        return redirect(destino_por_rol(current_user))
    return oauth.google.authorize_redirect(url_for("auth.authorize", _external=True))


@auth_bp.route("/authorize")
def authorize():
    token = oauth.google.authorize_access_token()
    info = token.get("userinfo") or oauth.google.userinfo()

    if not info.get("email_verified", True):
        flash("Tu email de Google no esta verificado.", "error")
        return redirect(url_for("home"))

    email = info["email"].lower()

    # Primero por google_id; si no, por email (adopta usuarios creados por el seed).
    usuario = Usuario.query.filter_by(google_id=info["sub"]).first()
    if not usuario:
        usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        usuario = Usuario(google_id=info["sub"], email=email, rol=ROL_CLIENTE)
        db.session.add(usuario)

    usuario.google_id = info["sub"]
    usuario.nombre = info.get("name") or email
    usuario.foto = info.get("picture", "")
    # El admin se promueve por configuracion; nunca se degrada aqui a un admin ya existente.
    if email in _emails_admin():
        usuario.rol = ROL_ADMIN
    db.session.commit()

    if not usuario.activo:
        flash("Tu cuenta esta desactivada. Contacta a un administrador.", "error")
        return redirect(url_for("home"))

    login_user(usuario)
    return redirect(destino_por_rol(usuario))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("home"))
