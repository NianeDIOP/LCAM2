from app import db
from datetime import datetime

# Modèle pour les configurations de l'établissement
class Configuration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom_etablissement = db.Column(db.String(100))
    adresse = db.Column(db.String(200))
    telephone = db.Column(db.String(20))
    inspection_academique = db.Column(db.String(100))
    inspection_education = db.Column(db.String(100))

# Modèle pour les années scolaires
class AnneeScolaire(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    libelle = db.Column(db.String(20), nullable=False)
    etat = db.Column(db.String(10), default='inactif')
    date_debut = db.Column(db.Date)
    date_fin = db.Column(db.Date)

# Modèle pour les niveaux scolaires
class Niveau(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    libelle = db.Column(db.String(50), nullable=False)
    etat = db.Column(db.String(10), default='actif')
    
    # Relations
    classes = db.relationship('Classe', backref='niveau', lazy=True)

# Modèle pour les classes
class Classe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    niveau_id = db.Column(db.Integer, db.ForeignKey('niveau.id'), nullable=False)
    libelle = db.Column(db.String(50), nullable=False)
    effectif = db.Column(db.Integer, default=0)
    etat = db.Column(db.String(10), default='actif')
    
    # Relations
    eleves = db.relationship('Eleve', backref='classe', lazy=True)

# Modèle pour les élèves
class Eleve(db.Model):
    ien = db.Column(db.String(50), primary_key=True)
    prenom = db.Column(db.String(50), nullable=False)
    nom = db.Column(db.String(50), nullable=False)
    sexe = db.Column(db.String(1))
    date_naissance = db.Column(db.Date)
    lieu_naissance = db.Column(db.String(100))
    classe_id = db.Column(db.Integer, db.ForeignKey('classe.id'))
    annee_scolaire = db.Column(db.String(20))

# Modèle pour les disciplines
class Discipline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    libelle = db.Column(db.String(100), nullable=False)
    coefficient = db.Column(db.Float, default=1.0)
    type = db.Column(db.String(20), default='principale')
    discipline_parent_id = db.Column(db.Integer, db.ForeignKey('discipline.id'))

# Modèle pour les notes du semestre 1
class NoteS1(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    eleve_ien = db.Column(db.String(50), db.ForeignKey('eleve.ien'))
    discipline_id = db.Column(db.Integer, db.ForeignKey('discipline.id'))
    moy_dd = db.Column(db.Float)
    comp_d = db.Column(db.Float)
    moy_d = db.Column(db.Float)
    rang_d = db.Column(db.Integer)
    annee_scolaire = db.Column(db.String(20))

# Modèle pour les notes du semestre 2
class NoteS2(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    eleve_ien = db.Column(db.String(50), db.ForeignKey('eleve.ien'))
    discipline_id = db.Column(db.Integer, db.ForeignKey('discipline.id'))
    moy_dd = db.Column(db.Float)
    comp_d = db.Column(db.Float)
    moy_d = db.Column(db.Float)
    rang_d = db.Column(db.Integer)
    annee_scolaire = db.Column(db.String(20))

# Modèle pour les moyennes générales du semestre 1
class MoyenneGeneraleS1(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    eleve_ien = db.Column(db.String(50), db.ForeignKey('eleve.ien'))
    moyenne = db.Column(db.Float)
    rang = db.Column(db.Integer)
    retard = db.Column(db.Integer)
    absence = db.Column(db.Integer)
    conseil_discipline = db.Column(db.String(10))
    appreciation = db.Column(db.Text)
    observation = db.Column(db.Text)
    annee_scolaire = db.Column(db.String(20))

# Modèle pour les moyennes générales du semestre 2
class MoyenneGeneraleS2(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    eleve_ien = db.Column(db.String(50), db.ForeignKey('eleve.ien'))
    moyenne = db.Column(db.Float)
    rang = db.Column(db.Integer)
    retard = db.Column(db.Integer)
    absence = db.Column(db.Integer)
    conseil_discipline = db.Column(db.String(10))
    appreciation = db.Column(db.Text)
    observation = db.Column(db.Text)
    annee_scolaire = db.Column(db.String(20))

# Modèle pour les décisions finales
class DecisionFinale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    eleve_ien = db.Column(db.String(50), db.ForeignKey('eleve.ien'))
    decision = db.Column(db.String(100))
    moyenne_annuelle = db.Column(db.Float)
    rang_annuel = db.Column(db.Integer)
    annee_scolaire = db.Column(db.String(20))