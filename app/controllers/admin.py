from flask import Blueprint, render_template, current_app, request, flash, redirect, url_for
from app import db
from app.models.models import Configuration, AnneeScolaire, Niveau, Classe
from datetime import datetime
import os
import shutil
import sqlite3

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
def index():
    """Page d'administration principale"""
    # Récupérer la configuration
    config = Configuration.query.first()
    if not config:
        config = Configuration()
        db.session.add(config)
        db.session.commit()
    
    # Récupérer les années scolaires
    annees = AnneeScolaire.query.order_by(AnneeScolaire.id.desc()).all()
    
    # Récupérer les niveaux
    niveaux = Niveau.query.order_by(Niveau.libelle).all()
    
    # Récupérer les classes
    classes = Classe.query.join(Niveau).order_by(Niveau.libelle, Classe.libelle).all()
    
    # Récupérer les sauvegardes disponibles
    backups = []
    backup_dir = os.path.join(os.path.dirname(current_app.root_path), 'backups')
    if (os.path.exists(backup_dir)):
        for filename in os.listdir(backup_dir):
            if filename.endswith('.db'):
                # Extraire la date du nom de fichier
                try:
                    date_str = filename.replace('lcams_backup_', '').replace('.db', '')
                    date_obj = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                    display_name = date_obj.strftime('%d/%m/%Y à %H:%M:%S')
                except:
                    display_name = filename
                
                backups.append({
                    'filename': filename,
                    'display_name': display_name
                })
        
        # Trier par plus récent
        backups = sorted(backups, key=lambda x: x['filename'], reverse=True)
    
    return render_template('admin/index.html', 
                          title='Paramètres',
                          app_name=current_app.config['APP_NAME'],
                          app_version=current_app.config['APP_VERSION'],
                          config=config,
                          annees=annees,
                          niveaux=niveaux,
                          classes=classes,
                          backups=backups)

@admin_bp.route('/etablissement/update', methods=['POST'])
def update_etablissement():
    """Mettre à jour les informations de l'établissement"""
    # Récupérer la configuration existante
    config = Configuration.query.first()
    if not config:
        config = Configuration()
        db.session.add(config)
    
    # Mettre à jour les champs
    config.nom_etablissement = request.form.get('nom_etablissement', '')
    config.adresse = request.form.get('adresse', '')
    config.telephone = request.form.get('telephone', '')
    config.inspection_academique = request.form.get('inspection_academique', '')
    config.inspection_education = request.form.get('inspection_education', '')
    
    # Sauvegarder les modifications
    try:
        db.session.commit()
        flash('Informations de l\'établissement mises à jour avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la mise à jour: {str(e)}', 'danger')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/annee/add', methods=['POST'])
def add_annee():
    """Ajouter une nouvelle année scolaire"""
    try:
        libelle = request.form.get('libelle')
        date_debut = request.form.get('date_debut') or None
        date_fin = request.form.get('date_fin') or None
        etat = 'actif' if request.form.get('etat') == 'actif' else 'inactif'
        
        # Vérifier si le libellé existe déjà
        if AnneeScolaire.query.filter_by(libelle=libelle).first():
            flash(f'L\'année scolaire "{libelle}" existe déjà', 'warning')
            return redirect(url_for('admin.index'))
        
        # Créer la nouvelle année
        nouvelle_annee = AnneeScolaire(
            libelle=libelle,
            etat=etat,
            date_debut=date_debut,
            date_fin=date_fin
        )
        db.session.add(nouvelle_annee)
        
        # Si l'année est active, désactiver les autres
        if etat == 'actif':
            AnneeScolaire.query.filter(AnneeScolaire.id != nouvelle_annee.id).update({'etat': 'inactif'})
        
        db.session.commit()
        flash(f'Année scolaire "{libelle}" ajoutée avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de l\'ajout de l\'année scolaire: {str(e)}', 'danger')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/annee/<int:id>/edit', methods=['GET', 'POST'])
def edit_annee(id):
    """Éditer une année scolaire"""
    annee = AnneeScolaire.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            annee.libelle = request.form.get('libelle')
            
            # Convertir les chaînes de date en objets Python date
            date_debut_str = request.form.get('date_debut')
            date_fin_str = request.form.get('date_fin')
            
            # Convertir date_debut si elle n'est pas vide
            if date_debut_str and date_debut_str.strip():
                try:
                    annee.date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
                except ValueError:
                    annee.date_debut = None
            else:
                annee.date_debut = None
                
            # Convertir date_fin si elle n'est pas vide
            if date_fin_str and date_fin_str.strip():
                try:
                    annee.date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
                except ValueError:
                    annee.date_fin = None
            else:
                annee.date_fin = None
            
            etat = 'actif' if request.form.get('etat') == 'actif' else 'inactif'
            
            # Si l'année devient active, désactiver les autres
            if etat == 'actif' and annee.etat != 'actif':
                AnneeScolaire.query.filter(AnneeScolaire.id != annee.id).update({'etat': 'inactif'})
            
            annee.etat = etat
            db.session.commit()
            flash(f'Année scolaire "{annee.libelle}" mise à jour avec succès', 'success')
            return redirect(url_for('admin.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour: {str(e)}', 'danger')
    
    return render_template('admin/edit_annee.html',
                          title=f'Éditer {annee.libelle}',
                          app_name=current_app.config['APP_NAME'],
                          app_version=current_app.config['APP_VERSION'],
                          annee=annee)

@admin_bp.route('/annee/<int:id>/active')
def set_active_annee(id):
    """Définir une année scolaire comme active"""
    try:
        # Désactiver toutes les années
        AnneeScolaire.query.update({'etat': 'inactif'})
        
        # Activer l'année sélectionnée
        annee = AnneeScolaire.query.get_or_404(id)
        annee.etat = 'actif'
        
        db.session.commit()
        flash(f'Année scolaire "{annee.libelle}" définie comme active', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la définition de l\'année active: {str(e)}', 'danger')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/annee/<int:id>/delete')
def delete_annee(id):
    """Supprimer une année scolaire"""
    try:
        annee = AnneeScolaire.query.get_or_404(id)
        
        # Si c'est la seule année, ne pas permettre la suppression
        if AnneeScolaire.query.count() <= 1:
            flash('Impossible de supprimer la dernière année scolaire', 'warning')
            return redirect(url_for('admin.index'))
        
        # Si c'est l'année active, ne pas permettre la suppression
        if annee.etat == 'actif':
            flash('Impossible de supprimer l\'année scolaire active', 'warning')
            return redirect(url_for('admin.index'))
        
        # Supprimer l'année
        libelle = annee.libelle
        db.session.delete(annee)
        db.session.commit()
        flash(f'Année scolaire "{libelle}" supprimée avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression: {str(e)}', 'danger')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/niveau/add', methods=['POST'])
def add_niveau():
    """Ajouter un nouveau niveau scolaire"""
    try:
        libelle = request.form.get('libelle')
        etat = 'actif' if request.form.get('etat') == 'actif' else 'inactif'
        
        # Vérifier si le libellé existe déjà
        if Niveau.query.filter_by(libelle=libelle).first():
            flash(f'Le niveau "{libelle}" existe déjà', 'warning')
            return redirect(url_for('admin.index'))
        
        # Créer le nouveau niveau
        nouveau_niveau = Niveau(
            libelle=libelle,
            etat=etat
        )
        db.session.add(nouveau_niveau)
        db.session.commit()
        flash(f'Niveau "{libelle}" ajouté avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de l\'ajout du niveau: {str(e)}', 'danger')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/niveau/<int:id>/edit', methods=['GET', 'POST'])
def edit_niveau(id):
    """Éditer un niveau scolaire"""
    niveau = Niveau.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            niveau.libelle = request.form.get('libelle')
            niveau.etat = 'actif' if request.form.get('etat') == 'actif' else 'inactif'
            db.session.commit()
            flash(f'Niveau "{niveau.libelle}" mis à jour avec succès', 'success')
            return redirect(url_for('admin.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour: {str(e)}', 'danger')
    
    return render_template('admin/edit_niveau.html',
                          title=f'Éditer {niveau.libelle}',
                          app_name=current_app.config['APP_NAME'],
                          app_version=current_app.config['APP_VERSION'],
                          niveau=niveau)

@admin_bp.route('/niveau/<int:id>/toggle')
def toggle_niveau(id):
    """Activer/désactiver un niveau"""
    try:
        niveau = Niveau.query.get_or_404(id)
        niveau.etat = 'inactif' if niveau.etat == 'actif' else 'actif'
        db.session.commit()
        flash(f'Niveau "{niveau.libelle}" {niveau.etat}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors du changement d\'état: {str(e)}', 'danger')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/niveau/<int:id>/delete')
def delete_niveau(id):
    """Supprimer un niveau scolaire"""
    try:
        niveau = Niveau.query.get_or_404(id)
        
        # Vérifier si le niveau a des classes
        if niveau.classes:
            flash(f'Impossible de supprimer le niveau "{niveau.libelle}" car il contient des classes', 'warning')
            return redirect(url_for('admin.index'))
        
        # Supprimer le niveau
        libelle = niveau.libelle
        db.session.delete(niveau)
        db.session.commit()
        flash(f'Niveau "{libelle}" supprimé avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression: {str(e)}', 'danger')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/classe/add', methods=['POST'])
def add_classe():
    """Ajouter une nouvelle classe"""
    try:
        niveau_id = request.form.get('niveau_id')
        libelle = request.form.get('libelle')
        effectif = request.form.get('effectif', 0)
        etat = 'actif' if request.form.get('etat') == 'actif' else 'inactif'
        
        # Vérifier si le niveau existe
        niveau = Niveau.query.get(niveau_id)
        if not niveau:
            flash('Niveau invalide', 'danger')
            return redirect(url_for('admin.index'))
        
        # Vérifier si la classe existe déjà pour ce niveau
        if Classe.query.filter_by(niveau_id=niveau_id, libelle=libelle).first():
            flash(f'La classe "{libelle}" existe déjà pour le niveau {niveau.libelle}', 'warning')
            return redirect(url_for('admin.index'))
        
        # Créer la nouvelle classe
        nouvelle_classe = Classe(
            niveau_id=niveau_id,
            libelle=libelle,
            effectif=effectif,
            etat=etat
        )
        db.session.add(nouvelle_classe)
        db.session.commit()
        flash(f'Classe "{niveau.libelle} {libelle}" ajoutée avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de l\'ajout de la classe: {str(e)}', 'danger')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/classe/<int:id>/edit', methods=['GET', 'POST'])
def edit_classe(id):
    """Éditer une classe"""
    classe = Classe.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # La modification du niveau n'est pas autorisée ici pour éviter les confusions
            classe.libelle = request.form.get('libelle')
            classe.effectif = request.form.get('effectif', 0)
            classe.etat = 'actif' if request.form.get('etat') == 'actif' else 'inactif'
            db.session.commit()
            flash(f'Classe "{classe.niveau.libelle} {classe.libelle}" mise à jour avec succès', 'success')
            return redirect(url_for('admin.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour: {str(e)}', 'danger')
    
    # Récupérer tous les niveaux pour le formulaire
    niveaux = Niveau.query.order_by(Niveau.libelle).all()
    
    return render_template('admin/edit_classe.html',
                          title=f'Éditer {classe.niveau.libelle} {classe.libelle}',
                          app_name=current_app.config['APP_NAME'],
                          app_version=current_app.config['APP_VERSION'],
                          classe=classe,
                          niveaux=niveaux)

@admin_bp.route('/classe/<int:id>/toggle')
def toggle_classe(id):
    """Activer/désactiver une classe"""
    try:
        classe = Classe.query.get_or_404(id)
        classe.etat = 'inactif' if classe.etat == 'actif' else 'actif'
        db.session.commit()
        flash(f'Classe "{classe.niveau.libelle} {classe.libelle}" {classe.etat}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors du changement d\'état: {str(e)}', 'danger')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/classe/<int:id>/delete')
def delete_classe(id):
    """Supprimer une classe"""
    try:
        classe = Classe.query.get_or_404(id)
        
        # Vérifier si la classe a des élèves
        # Cette vérification est optionnelle et dépend de votre modèle de données
        
        # Supprimer la classe
        libelle_complete = f"{classe.niveau.libelle} {classe.libelle}"
        db.session.delete(classe)
        db.session.commit()
        flash(f'Classe "{libelle_complete}" supprimée avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression: {str(e)}', 'danger')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/backup/create', methods=['POST'])
def create_backup():
    """Créer une sauvegarde de la base de données"""
    try:
        # Créer le dossier de sauvegarde s'il n'existe pas
        backup_dir = os.path.join(os.path.dirname(current_app.root_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Nom du fichier de sauvegarde
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'lcams_backup_{timestamp}.db')
        
        # Chemin de la base de données source
        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        
        # Copier la base de données
        shutil.copy2(db_path, backup_file)
        
        flash('Sauvegarde créée avec succès', 'success')
    except Exception as e:
        flash(f'Erreur lors de la création de la sauvegarde: {str(e)}', 'danger')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/backup/restore', methods=['POST'])
def restore_backup():
    """Restaurer une sauvegarde de la base de données"""
    try:
        backup_file = request.form.get('backup_file')
        
        if not backup_file:
            flash('Aucune sauvegarde sélectionnée', 'warning')
            return redirect(url_for('admin.index'))
        
        # Chemin complet du fichier de sauvegarde
        backup_dir = os.path.join(os.path.dirname(current_app.root_path), 'backups')
        backup_path = os.path.join(backup_dir, backup_file)
        
        # Vérifier que le fichier existe
        if not os.path.exists(backup_path):
            flash('Fichier de sauvegarde introuvable', 'danger')
            return redirect(url_for('admin.index'))
        
        # Chemin de la base de données actuelle
        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        
        # Créer une sauvegarde de la base actuelle avant restauration
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        current_backup = os.path.join(backup_dir, f'lcams_pre_restore_{timestamp}.db')
        shutil.copy2(db_path, current_backup)
        
        # Restaurer la sauvegarde
        # Fermer toutes les connexions à la base de données
        db.session.close()
        db.engine.dispose()
        
        # Copier la sauvegarde
        shutil.copy2(backup_path, db_path)
        
        flash('Base de données restaurée avec succès', 'success')
    except Exception as e:
        flash(f'Erreur lors de la restauration: {str(e)}', 'danger')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/database/reset', methods=['POST'])
def reset_database():
    """Réinitialiser la base de données"""
    try:
        # Vérifier la confirmation
        if request.form.get('confirm_reset') != 'on':
            flash('Confirmation requise pour réinitialiser la base de données', 'warning')
            return redirect(url_for('admin.index'))
        
        # Chemin de la base de données
        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        
        # Créer une sauvegarde avant réinitialisation
        backup_dir = os.path.join(os.path.dirname(current_app.root_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'lcams_pre_reset_{timestamp}.db')
        shutil.copy2(db_path, backup_file)
        
        # Fermer toutes les connexions à la base de données
        db.session.close()
        db.engine.dispose()
        
        # Supprimer le fichier de base de données
        if os.path.exists(db_path):
            os.remove(db_path)
        
        # Créer une nouvelle base de données vide
        conn = sqlite3.connect(db_path)
        conn.close()
        
        flash('Base de données réinitialisée avec succès. Veuillez redémarrer l\'application.', 'success')
    except Exception as e:
        flash(f'Erreur lors de la réinitialisation: {str(e)}', 'danger')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/api/configuration')
def get_configuration():
    """API pour récupérer les informations de configuration"""
    config = Configuration.query.first()
    if not config:
        config = Configuration()
        db.session.add(config)
        db.session.commit()
    
    return {
        'nom_etablissement': config.nom_etablissement,
        'adresse': config.adresse,
        'telephone': config.telephone,
        'inspection_academique': config.inspection_academique,
        'inspection_education': config.inspection_education,
    }