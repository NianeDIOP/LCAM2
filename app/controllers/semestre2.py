from flask import Blueprint

semestre2_bp = Blueprint('semestre2', __name__)

@semestre2_bp.route('/')
def index():
    return "Module Semestre 2"