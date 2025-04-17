import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'cle-secrete-par-defaut'
    # Utiliser un chemin absolu pour éviter les problèmes d'accès
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.abspath(os.path.join(os.path.dirname(__file__), 'lcams.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    APP_NAME = 'LCAMS - Logiciel de Calcul et Analyse des Moyennes Semestrielles'
    APP_VERSION = '1.0.0'
    UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads')
    
    # Niveaux d'enseignement disponibles
    NIVEAUX = [
        '6ème', '5ème', '4ème', '3ème',  # Collège
        'Seconde', 'Première', 'Terminale'  # Lycée
    ]
    
    # Configuration par défaut de l'établissement
    DEFAULT_ETABLISSEMENT = {
        'nom': '',
        'adresse': '',
        'telephone': '',
        'inspection_academique': '',
        'inspection_education': '',
    }
    
    # Thème de couleurs
    THEME_COLORS = {
        'primary': '#3498db',
        'secondary': '#2c3e50',
        'success': '#2ecc71',
        'danger': '#e74c3c',
        'warning': '#f39c12',
        'info': '#1abc9c',
        'light': '#ecf0f1',
        'dark': '#2c3e50',
    }