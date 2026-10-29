"""
Datos de ejemplo para la demo de Tech Solutions.

Uso:  flask seed            (idempotente: no duplica lo que ya existe)
      flask seed --reset    (borra todo y vuelve a cargar)

Los usuarios del seed se enlazan con Google por email en su primer login,
asi que el admin debe coincidir con ADMIN_EMAIL(S).
"""
import os

from extensions import db
from models import (
    Usuario, Plan, Servicio, Solicitud,
    ROL_ADMIN, ROL_CLIENTE, PENDIENTE, EN_CURSO, REALIZADO, RECHAZADA,
)

PLANES = [
    {"nombre": "Basico", "descripcion": "Soporte por correo y 2 modificaciones al mes.", "precio_mensual": 49},
    {"nombre": "Profesional", "descripcion": "Soporte prioritario y 8 modificaciones al mes.", "precio_mensual": 149},
    {"nombre": "Enterprise", "descripcion": "Soporte 24/7 y modificaciones ilimitadas.", "precio_mensual": 399},
]

CLIENTES = [
    {"email": "cliente1@example.com", "nombre": "Ana Torres"},
    {"email": "cliente2@example.com", "nombre": "Luis Mendez"},
]

# (cliente, plan, nombre del servicio, descripcion)
SERVICIOS = [
    ("cliente1@example.com", "Profesional", "Sitio web corporativo", "Mantenimiento del sitio institucional."),
    ("cliente1@example.com", "Basico", "Correo empresarial", "Cuentas de correo del dominio."),
    ("cliente2@example.com", "Enterprise", "Plataforma de ventas", "Tienda online y paneles de reporte."),
]

# (cliente, servicio, titulo, descripcion, estado, respuesta)
SOLICITUDES = [
    ("cliente1@example.com", "Sitio web corporativo", "Cambiar banner de inicio",
     "Reemplazar el banner por la campana de fin de ano.", PENDIENTE, None),
    ("cliente1@example.com", "Sitio web corporativo", "Agregar pagina de contacto",
     "Formulario con mapa y telefono.", EN_CURSO, "Aprobada, entrega estimada en 3 dias."),
    ("cliente1@example.com", "Correo empresarial", "Crear 5 cuentas nuevas",
     "Para el equipo de ventas.", REALIZADO, "Cuentas creadas y credenciales enviadas."),
    ("cliente2@example.com", "Plataforma de ventas", "Integrar nueva pasarela de pago",
     "Agregar un segundo proveedor de pagos.", RECHAZADA, "Fuera del alcance del plan actual."),
]


def _primer_email_admin():
    raw = os.getenv("ADMIN_EMAILS") or os.getenv("ADMIN_EMAIL", "")
    emails = [e.strip().lower() for e in raw.split(",") if e.strip()]
    return emails[0] if emails else "admin@example.com"


def _obtener_o_crear(modelo, filtro, **valores):
    obj = modelo.query.filter_by(**filtro).first()
    if not obj:
        obj = modelo(**filtro, **valores)
        db.session.add(obj)
        db.session.flush()
    return obj


def run_seed(reset=False):
    if reset:
        for modelo in (Solicitud, Servicio, Plan, Usuario):
            modelo.query.delete()
        db.session.commit()

    admin_email = _primer_email_admin()
    _obtener_o_crear(Usuario, {"email": admin_email},
                     google_id=f"seed-{admin_email}", nombre="Administrador", rol=ROL_ADMIN)

    clientes = {}
    for c in CLIENTES:
        clientes[c["email"]] = _obtener_o_crear(
            Usuario, {"email": c["email"]},
            google_id=f"seed-{c['email']}", nombre=c["nombre"], rol=ROL_CLIENTE)

    planes = {p["nombre"]: _obtener_o_crear(Plan, {"nombre": p["nombre"]},
                                           descripcion=p["descripcion"],
                                           precio_mensual=p["precio_mensual"])
              for p in PLANES}

    servicios = {}
    for email, plan, nombre, desc in SERVICIOS:
        servicios[nombre] = _obtener_o_crear(
            Servicio, {"nombre": nombre, "cliente_id": clientes[email].id},
            descripcion=desc, plan_id=planes[plan].id)

    for email, servicio, titulo, desc, estado, respuesta in SOLICITUDES:
        _obtener_o_crear(
            Solicitud, {"titulo": titulo, "cliente_id": clientes[email].id},
            descripcion=desc, estado=estado, respuesta_admin=respuesta,
            servicio_id=servicios[servicio].id)

    db.session.commit()
