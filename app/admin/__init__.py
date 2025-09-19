from flask import Blueprint

bp = Blueprint('admin', __name__, url_prefix='/admin')

# Import routes after creating the blueprint to avoid circular imports
from app.admin import routes
