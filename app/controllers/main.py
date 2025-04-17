from flask import Blueprint, render_template, current_app, request, flash, redirect, url_for
from app.models.models import AnneeScolaire, MoyenneGeneraleS1, Classe, Niveau, Eleve, NoteS1
from app import db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Statistiques générales
    annee_active = AnneeScolaire.query.filter_by(etat='actif').first().libelle
    total_eleves = MoyenneGeneraleS1.query.filter_by(annee_scolaire=annee_active).count()
    total_classes = Classe.query.filter_by(etat='actif').count()
    eleves_moy = MoyenneGeneraleS1.query.filter(MoyenneGeneraleS1.moyenne>=10, MoyenneGeneraleS1.annee_scolaire==annee_active).count()
    taux = round((eleves_moy/total_eleves*100),2) if total_eleves>0 else 0
    stats = dict(total_eleves=total_eleves, total_classes=total_classes,
                 eleves_moyenne=eleves_moy, taux_reussite=taux)
    niveaux = Niveau.query.filter_by(etat='actif').all()
    classes = Classe.query.filter_by(etat='actif').all()
    return render_template('index.html', title='Accueil', app_name=current_app.config['APP_NAME'],
                           app_version=current_app.config['APP_VERSION'], stats=stats,
                           niveaux=niveaux, classes=classes)

@main_bp.route('/delete/class', methods=['POST'])
def delete_class_data():
    class_id = request.form.get('class_id')
    if class_id:
        # supprimer élèves et notes du semestre 1
        eleves = Eleve.query.filter_by(classe_id=class_id).all()
        iens = [e.ien for e in eleves]
        MoyenneGeneraleS1.query.filter(MoyenneGeneraleS1.eleve_ien.in_(iens)).delete(synchronize_session=False)
        NoteS1.query.filter(NoteS1.eleve_ien.in_(iens)).delete(synchronize_session=False)
        db.session.commit()
        flash(f'Données supprimées pour la classe id={class_id}', 'success')
    return redirect(url_for('main.index'))

@main_bp.route('/delete/level', methods=['POST'])
def delete_level_data():
    niveau_id = request.form.get('niveau_id')
    if niveau_id:
        classes_lv = Classe.query.filter_by(niveau_id=niveau_id).all()
        for cl in classes_lv:
            eleves = Eleve.query.filter_by(classe_id=cl.id).all()
            iens = [e.ien for e in eleves]
            MoyenneGeneraleS1.query.filter(MoyenneGeneraleS1.eleve_ien.in_(iens)).delete(synchronize_session=False)
            NoteS1.query.filter(NoteS1.eleve_ien.in_(iens)).delete(synchronize_session=False)
        db.session.commit()
        flash(f'Données supprimées pour le niveau id={niveau_id}', 'success')
    return redirect(url_for('main.index'))