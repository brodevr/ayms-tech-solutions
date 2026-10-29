from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def roles_required(*roles):
    """Exige sesion iniciada y que el usuario tenga alguno de los roles dados."""
    def decorador(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            if current_user.rol not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorador


def admin_required(f):
    from models import ROL_ADMIN
    return roles_required(ROL_ADMIN)(f)
