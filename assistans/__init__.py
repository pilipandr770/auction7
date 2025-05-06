
from flask import Blueprint

assistant_bp = Blueprint('assistant', __name__, template_folder='templates', static_folder='static')

from . import routes
