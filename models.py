from datetime import datetime, timezone

from flask_login import UserMixin

from extensions import db


def ahora():
    return datetime.now(timezone.utc)


# Roles
ROL_CLIENTE = "cliente"
ROL_ADMIN = "admin"

# Estados de una solicitud: pendiente -> en_curso -> realizado / rechazada
PENDIENTE = "pendiente"
EN_CURSO = "en_curso"
REALIZADO = "realizado"
RECHAZADA = "rechazada"

ESTADOS = (PENDIENTE, EN_CURSO, REALIZADO, RECHAZADA)

# Unica fuente de verdad de las transiciones validas.
TRANSICIONES = {
    PENDIENTE: (EN_CURSO, RECHAZADA),
    EN_CURSO: (REALIZADO,),
    REALIZADO: (),
    RECHAZADA: (),
}


class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    nombre = db.Column(db.String(200))
    foto = db.Column(db.String(500))
    rol = db.Column(db.String(20), nullable=False, default=ROL_CLIENTE)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado = db.Column(db.DateTime, default=ahora)

    servicios = db.relationship("Servicio", backref="cliente", lazy=True)
    solicitudes = db.relationship("Solicitud", backref="cliente", lazy=True)

    @property
    def es_admin(self):
        return self.rol == ROL_ADMIN

    @property
    def is_active(self):
        # Flask-Login rechaza la sesion de un usuario desactivado.
        return self.activo


class Plan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.String(500))
    precio_mensual = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    servicios = db.relationship("Servicio", backref="plan", lazy=True)


class Servicio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado = db.Column(db.DateTime, default=ahora)

    cliente_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("plan.id"), nullable=False)

    solicitudes = db.relationship("Solicitud", backref="servicio", lazy=True)


class Solicitud(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default=PENDIENTE, index=True)
    respuesta_admin = db.Column(db.Text)
    creado = db.Column(db.DateTime, default=ahora)
    actualizado = db.Column(db.DateTime, default=ahora, onupdate=ahora)

    servicio_id = db.Column(db.Integer, db.ForeignKey("servicio.id"), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)

    def puede_pasar_a(self, nuevo_estado):
        return nuevo_estado in TRANSICIONES.get(self.estado, ())

    def cambiar_estado(self, nuevo_estado):
        if not self.puede_pasar_a(nuevo_estado):
            raise ValueError(f"Transicion invalida: {self.estado} -> {nuevo_estado}")
        self.estado = nuevo_estado
