from .models import *
from app import db

def initialize_db():
    """Initialise la base de données avec les valeurs par défaut si nécessaire."""
    # Création des tables si elles n'existent pas
    db.create_all()
    
    # Vérifier si des niveaux existent déjà
    niveaux_count = Niveau.query.count()
    if niveaux_count == 0:
        # Ajouter les niveaux par défaut
        niveaux_default = ['6ème', '5ème', '4ème', '3ème', 'Seconde', 'Première', 'Terminale']
        for niveau_libelle in niveaux_default:
            niveau = Niveau(libelle=niveau_libelle, etat='actif')
            db.session.add(niveau)
        
        # Ajouter une année scolaire active par défaut
        annee_scolaire = AnneeScolaire(libelle='2024-2025', etat='actif')
        db.session.add(annee_scolaire)
        
        # Valider les changements
        db.session.commit()