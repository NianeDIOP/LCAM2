from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
import os

# Initialiser les extensions
db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialiser les extensions avec l'application
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Créer le dossier d'uploads s'il n'existe pas
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Enregistrer les blueprints
    from app.controllers.main import main_bp
    from app.controllers.auth import auth_bp
    from app.controllers.admin import admin_bp
    from app.controllers.semestre1 import semestre1_bp
    from app.controllers.semestre2 import semestre2_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(semestre1_bp, url_prefix='/semestre1')
    app.register_blueprint(semestre2_bp, url_prefix='/semestre2')
    
    # Inject active school year into all templates
    @app.context_processor
    def inject_active_annee():
        from app.models.models import AnneeScolaire
        annee = AnneeScolaire.query.filter_by(etat='actif').first()
        return dict(annee_active=annee.libelle if annee else '')

    # Initialiser la base de données au démarrage de l'application
    with app.app_context():
        try:
            from app.models import initialize_db
            initialize_db()
            print("Base de données initialisée avec succès")
        except Exception as e:
            print(f"Erreur lors de l'initialisation de la base de données: {e}")
    
    return app