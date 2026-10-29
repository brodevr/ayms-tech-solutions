import os

import click
from dotenv import load_dotenv
from flask import Flask, render_template
from flask_login import current_user

from auth.routes import auth_bp, init_oauth
from extensions import db, login_manager
from models import Servicio, Solicitud, Usuario, ESTADOS
from utils import admin_required, roles_required

load_dotenv()


def create_app(config=None):
    app = Flask(__name__)

    secret = os.getenv("SECRET_KEY")
    if not secret and not (config and config.get("TESTING")):
        raise RuntimeError("Falta la variable de entorno SECRET_KEY.")
    app.config["SECRET_KEY"] = secret or "test"
    app.config["GOOGLE_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID")
    app.config["GOOGLE_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.getenv("FLASK_ENV") == "production"

    database_url = os.getenv("DATABASE_URL", "sqlite:///techsolutions.db")
    # Render entrega "postgres://" pero SQLAlchemy requiere "postgresql://"
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    if config:
        app.config.update(config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    init_oauth(app)
    app.register_blueprint(auth_bp)

    # Las tablas se crean al arrancar; el seed es un comando explicito (flask seed).
    with app.app_context():
        db.create_all()

    registrar_rutas(app)
    registrar_comandos(app)
    return app


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))


def registrar_rutas(app):
    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/mis-solicitudes")
    @roles_required("cliente", "admin")
    def mis_solicitudes():
        servicios = Servicio.query.filter_by(cliente_id=current_user.id).all()
        solicitudes = (Solicitud.query.filter_by(cliente_id=current_user.id)
                       .order_by(Solicitud.creado.desc()).all())
        return render_template("profile.html", servicios=servicios, solicitudes=solicitudes)

    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        conteo = {e: Solicitud.query.filter_by(estado=e).count() for e in ESTADOS}
        recientes = Solicitud.query.order_by(Solicitud.creado.desc()).limit(10).all()
        return render_template("admin/dashboard.html",
                               conteo=conteo,
                               total_clientes=Usuario.query.filter_by(rol="cliente").count(),
                               total_servicios=Servicio.query.count(),
                               recientes=recientes)

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(_e):
        db.session.rollback()
        return render_template("500.html"), 500


def registrar_comandos(app):
    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Borra todos los datos antes de cargar el seed.")
    def seed_command(reset):
        """Carga datos de ejemplo (idempotente)."""
        from seed import run_seed
        run_seed(reset=reset)
        click.echo("Seed completado.")


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
