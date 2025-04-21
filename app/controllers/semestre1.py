from flask import Blueprint, render_template, current_app, jsonify, request, flash, redirect, url_for, send_file
from flask_login import login_required
from app.models.models import Niveau, Classe, Eleve, Discipline, NoteS1, MoyenneGeneraleS1, AnneeScolaire, Configuration, Rapport
from app import db
import pandas as pd
import os
from werkzeug.utils import secure_filename
import re
import datetime
import time
import tempfile

semestre1_bp = Blueprint('semestre1', __name__)

@semestre1_bp.route('/')
def index():
    # Determine active tab from query parameter (overview, moyennes, disciplines, reports, import)
    active_tab = request.args.get('tab', 'moyennes')
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les statistiques de base
    total_eleves = MoyenneGeneraleS1.query.filter_by(annee_scolaire=annee_active).count()
    eleves_moyenne = MoyenneGeneraleS1.query.filter(MoyenneGeneraleS1.moyenne >= 10, 
                                                    MoyenneGeneraleS1.annee_scolaire==annee_active).count()
    
    # Calculer la moyenne générale
    moyennes = MoyenneGeneraleS1.query.filter_by(annee_scolaire=annee_active).with_entities(MoyenneGeneraleS1.moyenne)
    moyenne_generale = 0
    if total_eleves > 0:
        moyenne_generale = sum([m.moyenne for m in moyennes if m.moyenne is not None]) / total_eleves
    
    # Calculer le taux de réussite
    taux_reussite = 0
    if total_eleves > 0:
        taux_reussite = (eleves_moyenne / total_eleves) * 100
    # Calculer extrêmes (min & max) de toutes les moyennes et répartition par sexe
    base_q = db.session.query(MoyenneGeneraleS1).join(Eleve, MoyenneGeneraleS1.eleve_ien==Eleve.ien)
    base_q = base_q.filter(MoyenneGeneraleS1.annee_scolaire == annee_active)
    toutes_moyennes = [m.moyenne for m in base_q.with_entities(MoyenneGeneraleS1.moyenne).all() if m[0] is not None]
    global_min = round(min(toutes_moyennes),2) if toutes_moyennes else 0
    global_max = round(max(toutes_moyennes),2) if toutes_moyennes else 0
    
    # Gestion des sexes avec prise en compte à la fois de "M" et "H" pour masculin
    global_count_m = base_q.filter(Eleve.sexe.in_(['M', 'H'])).count()
    global_count_f = base_q.filter(Eleve.sexe=='F').count()
    global_taux_m = round(global_count_m/total_eleves*100,2) if total_eleves>0 else 0
    global_taux_f = round(global_count_f/total_eleves*100,2) if total_eleves>0 else 0
    base_reussite_q = base_q.filter(MoyenneGeneraleS1.moyenne>=10)
    reussite_count = eleves_moyenne
    global_reussite_m = base_reussite_q.filter(Eleve.sexe.in_(['M', 'H'])).count()
    global_reussite_f = base_reussite_q.filter(Eleve.sexe=='F').count()
    global_taux_reussite_m = round(global_reussite_m/global_count_m*100,2) if global_count_m>0 else 0
    global_taux_reussite_f = round(global_reussite_f/global_count_f*100,2) if global_count_f>0 else 0

    # Récupérer les niveaux
    niveaux = Niveau.query.filter_by(etat='actif').all()
    # Historique des imports (niveau-classe pour semestre 1)
    imports = db.session.query(
        Niveau.id.label('niveau_id'),
        Niveau.libelle.label('niveau'),
        Classe.id.label('classe_id'),
        Classe.libelle.label('classe')
    )
    imports = imports.join(Classe, Classe.niveau_id == Niveau.id)
    imports = imports.join(Eleve, Eleve.classe_id == Classe.id)
    imports = imports.join(MoyenneGeneraleS1, Eleve.ien == MoyenneGeneraleS1.eleve_ien)
    imports = imports.filter(MoyenneGeneraleS1.annee_scolaire == annee_active)
    imports = imports.distinct().all()
    # Classes actives pour suppression
    classes_active = Classe.query.filter_by(etat='actif').all()
    
    # Récupérer les statistiques par niveau
    niveau_stats = []
    for niveau in niveaux:
        # Récupérer les élèves du niveau
        eleves_niveau = db.session.query(MoyenneGeneraleS1).\
            join(Eleve, MoyenneGeneraleS1.eleve_ien == Eleve.ien).\
            join(Classe, Eleve.classe_id == Classe.id).\
            filter(Classe.niveau_id == niveau.id, MoyenneGeneraleS1.annee_scolaire == annee_active).all()
        
        nb_eleves = len(eleves_niveau)
        if nb_eleves > 0:
            # Calculer la moyenne du niveau
            moy_niveau = sum([e.moyenne for e in eleves_niveau if e.moyenne is not None]) / nb_eleves
            
            # Calculer le nombre d'élèves ayant la moyenne
            nb_moyenne = sum(1 for e in eleves_niveau if e.moyenne is not None and e.moyenne >= 10)
            
            # Calculer le taux de réussite
            taux = (nb_moyenne / nb_eleves) * 100 if nb_eleves > 0 else 0
            
            niveau_stats.append({
                'niveau': niveau.libelle,
                'nb_eleves': nb_eleves,
                'moyenne': round(moy_niveau, 2),
                'nb_moyenne': nb_moyenne,
                'taux_reussite': round(taux, 2)
            })
    
    return render_template('semestre1/index.html', 
                          title='Module Semestre 1', 
                          app_name=current_app.config['APP_NAME'], 
                          app_version=current_app.config['APP_VERSION'],
                          active_tab=active_tab,
                          annee_scolaire=annee_active,
                          stats={
                              'total_eleves': total_eleves,
                              'count_hommes': global_count_m,
                              'count_femmes': global_count_f,
                              'taux_hommes': global_taux_m,
                              'taux_femmes': global_taux_f,
                              'eleves_moyenne': eleves_moyenne,
                              'reussite_hommes': global_reussite_m,
                              'reussite_femmes': global_reussite_f,
                              'taux_reussite_hommes': global_taux_reussite_m,
                              'taux_reussite_femmes': global_taux_reussite_f,
                              'moyenne_generale': round(moyenne_generale, 2),
                              'min': global_min,
                              'max': global_max,
                              'taux_reussite': round(taux_reussite, 2)
                          },
                          niveau_stats=niveau_stats,
                          niveaux=niveaux,
                          imports=imports,
                          classes=classes_active)

@semestre1_bp.route('/api/classes/<int:niveau_id>')
def get_classes(niveau_id):
    """Récupérer les classes d'un niveau"""
    classes = Classe.query.filter_by(niveau_id=niveau_id, etat='actif').all()
    return jsonify([{'id': c.id, 'libelle': c.libelle} for c in classes])

@semestre1_bp.route('/api/disciplines/<int:classe_id>')
def get_disciplines(classe_id):
    """Récupérer les disciplines disponibles pour une classe"""
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Rechercher les disciplines pour lesquelles il existe des notes dans cette classe
    disciplines = db.session.query(Discipline).\
        join(NoteS1, NoteS1.discipline_id == Discipline.id).\
        join(Eleve, NoteS1.eleve_ien == Eleve.ien).\
        filter(Eleve.classe_id == classe_id, NoteS1.annee_scolaire == annee_active).\
        distinct().all()
    
    return jsonify([{'id': d.id, 'libelle': d.libelle} for d in disciplines])

@semestre1_bp.route('/api/stats/moyennes')
def stats_moyennes():
    # Récupérer filtres
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    sexe = request.args.get('sexe')
    note_min = float(request.args.get('note_min', 0))
    note_max = float(request.args.get('note_max', 20))
    # Récupérer l'année scolaire active
    annee = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee.libelle if annee else '2024-2025'
    # Construire la requête avec filtres
    q = db.session.query(MoyenneGeneraleS1).join(Eleve, MoyenneGeneraleS1.eleve_ien==Eleve.ien)
    q = q.join(Classe, Eleve.classe_id==Classe.id).join(Niveau, Classe.niveau_id==Niveau.id)
    # Appliquer filtres niveau et classe
    if niveau_id:
        q = q.filter(Niveau.id==niveau_id)
    if classe_id:
        q = q.filter(Classe.id==classe_id)
    # Filtrer par sexe si fourni
    if sexe in ('M','F'):
        q = q.filter(Eleve.sexe==sexe)
    # Filtrer par intervalle de notes
    q = q.filter(MoyenneGeneraleS1.annee_scolaire==annee_active,
                 MoyenneGeneraleS1.moyenne>=note_min,
                 MoyenneGeneraleS1.moyenne<=note_max)
    # Statistiques globales
    total = q.count()
    moys = q.with_entities(MoyenneGeneraleS1.moyenne)
    moyenne = round(sum([m.moyenne or 0 for m in moys]) / total,2) if total>0 else 0
    reussite_count = q.filter(MoyenneGeneraleS1.moyenne>=10).count()
    taux_reussite = round((reussite_count/total*100),2) if total>0 else 0
    # Répartition par sexe (les jointures Eleve sont déjà faites)
    count_m = q.filter(Eleve.sexe=='M').count()
    count_f = q.filter(Eleve.sexe=='F').count()
    taux_m = round((count_m/total*100),2) if total>0 else 0
    taux_f = round((count_f/total*100),2) if total>0 else 0
    # Extrêmes
    all_moy = [m[0] for m in q.with_entities(MoyenneGeneraleS1.moyenne).all() if m[0] is not None]
    minv = round(min(all_moy),2) if all_moy else 0
    maxv = round(max(all_moy),2) if all_moy else 0
    
    return jsonify({
        'total_eleves': total,
        'moyenne_generale': moyenne,
        'eleves_moyenne': reussite_count,
        'taux_reussite': taux_reussite,
        'count_hommes': count_m,
        'count_femmes': count_f,
        'taux_hommes': taux_m,
        'taux_femmes': taux_f,
        'min': minv,
        'max': maxv
    })

@semestre1_bp.route('/moyennes_analysis')
def moyennes_analysis():
    """Page d'analyse des moyennes du semestre 1"""
    # Récupérer les filtres
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    sexe = request.args.get('sexe')
    note_min = request.args.get('note_min', '0')
    note_max = request.args.get('note_max', '20')
    
    # Convertir en float pour les comparaisons
    try:
        note_min = float(note_min)
        note_max = float(note_max)
    except (ValueError, TypeError):
        note_min = 0
        note_max = 20
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les niveaux pour le formulaire de filtrage
    niveaux = Niveau.query.filter_by(etat='actif').all()
    
    # Construire la requête de base
    q = db.session.query(MoyenneGeneraleS1).join(Eleve, MoyenneGeneraleS1.eleve_ien == Eleve.ien)
    q = q.join(Classe, Eleve.classe_id == Classe.id)
    q = q.join(Niveau, Classe.niveau_id == Niveau.id)
    
    # Appliquer les filtres
    q = q.filter(MoyenneGeneraleS1.annee_scolaire == annee_active)
    
    if niveau_id:
        q = q.filter(Niveau.id == niveau_id)
    
    if classe_id:
        q = q.filter(Classe.id == classe_id)
    
    # Correction du filtre sexe : Masculin = M ou H
    if sexe == 'M':
        q = q.filter(Eleve.sexe.in_(['M', 'H']))
    elif sexe == 'F':
        q = q.filter(Eleve.sexe == 'F')
    
    q = q.filter(MoyenneGeneraleS1.moyenne >= note_min, MoyenneGeneraleS1.moyenne <= note_max)
    
    # Récupérer les données
    resultats = q.all()
    
    # Statistiques globales
    total_eleves = len(resultats)
    
    # Prendre en compte à la fois "M" et "H" pour les élèves masculins
    total_filles = q.filter(Eleve.sexe == 'F').count()
    total_garcons = q.filter(Eleve.sexe.in_(['M', 'H'])).count()
    
    # Pourcentages
    pct_filles = round((total_filles / total_eleves * 100) if total_eleves > 0 else 0)
    pct_garcons = round((total_garcons / total_eleves * 100) if total_eleves > 0 else 0)
    
    # Statistiques des moyennes
    moyennes = [r.moyenne for r in resultats if r.moyenne is not None]
    moyenne_generale = round(sum(moyennes) / len(moyennes), 2) if moyennes else 0
    plus_forte_moyenne = round(max(moyennes), 2) if moyennes else 0
    plus_faible_moyenne = round(min(moyennes), 2) if moyennes else 0
    # Ajout médiane et écart-type
    mediane = round(float(pd.Series(moyennes).median()), 2) if moyennes else 0
    ecart_type = round(float(pd.Series(moyennes).std()), 2) if moyennes else 0

    # Calculer les moyennes par catégorie de sexe
    moyennes_garcons = [r.moyenne for r in q.filter(Eleve.sexe.in_(['M', 'H'])).all() if r.moyenne is not None]
    moyennes_filles = [r.moyenne for r in q.filter(Eleve.sexe == 'F').all() if r.moyenne is not None]
    moyenne_garcons = round(sum(moyennes_garcons) / len(moyennes_garcons), 2) if moyennes_garcons else 0
    moyenne_filles = round(sum(moyennes_filles) / len(moyennes_filles), 2) if moyennes_filles else 0

    # Répartition appréciations (selon la moyenne)
    appreciation_counts = {
        'Félicitations': 0,
        'Encouragements': 0,
        "Tableau d'honneur": 0,
        'Passable': 0,
        'Doit redoubler d\'effort': 0,
        'Avertissement': 0,
        'Blâme': 0
    }
    observation_counts = {
        'Travail excellent': 0,
        'Satisfait doit continuer': 0,
        'Peut mieux faire': 0,
        'Insuffisant': 0,
        'Risque de redoubler': 0,
        'Risque d\'exclusion': 0
    }
    for r in resultats:
        m = r.moyenne or 0
        # Appreciation
        if m >= 17:
            appreciation_counts['Félicitations'] += 1
        elif m >= 14:
            appreciation_counts['Encouragements'] += 1
        elif m >= 12:
            appreciation_counts["Tableau d'honneur"] += 1
        elif m >= 10:
            appreciation_counts['Passable'] += 1
        elif m >= 8:
            appreciation_counts["Doit redoubler d'effort"] += 1
        elif m >= 6:
            appreciation_counts['Avertissement'] += 1
        else:
            appreciation_counts['Blâme'] += 1
        
        # Observation (compléter cette partie manquante)
        if m >= 16:
            observation_counts['Travail excellent'] += 1
        elif m >= 12:
            observation_counts['Satisfait doit continuer'] += 1
        elif m >= 10:
            observation_counts['Peut mieux faire'] += 1
        elif m >= 9:
            observation_counts['Insuffisant'] += 1
        elif m >= 7:
            observation_counts['Risque de redoubler'] += 1
        else:
            observation_counts["Risque d'exclusion"] += 1

    # Élèves avec moyenne >= 10
    reussite_count = q.filter(MoyenneGeneraleS1.moyenne >= 10).count()
    reussite_filles = q.filter(Eleve.sexe == 'F', MoyenneGeneraleS1.moyenne >= 10).count()
    reussite_garcons = q.filter(Eleve.sexe.in_(['M', 'H']), MoyenneGeneraleS1.moyenne >= 10).count()
    
    # Taux de réussite
    taux_reussite = round((reussite_count / total_eleves * 100) if total_eleves > 0 else 0)
    taux_reussite_filles = round((reussite_filles / total_filles * 100) if total_filles > 0 else 0)
    taux_reussite_garcons = round((reussite_garcons / total_garcons * 100) if total_garcons > 0 else 0)
    
    # Répartition par mentions
    felicitations_count = q.filter(MoyenneGeneraleS1.moyenne >= 17).count()
    encouragements_count = q.filter(MoyenneGeneraleS1.moyenne >= 15, MoyenneGeneraleS1.moyenne < 17).count()
    tableau_honneur_count = q.filter(MoyenneGeneraleS1.moyenne >= 12, MoyenneGeneraleS1.moyenne < 15).count()
    passable_count = q.filter(MoyenneGeneraleS1.moyenne >= 10, MoyenneGeneraleS1.moyenne < 12).count()
    insuffisant_count = q.filter(MoyenneGeneraleS1.moyenne < 10).count()
    
    # Observations
    mieux_faire_count = q.filter(MoyenneGeneraleS1.moyenne >= 10, MoyenneGeneraleS1.moyenne < 12).count()
    doit_continuer_count = q.filter(MoyenneGeneraleS1.moyenne >= 12).count()
    risque_redoubler_count = q.filter(MoyenneGeneraleS1.moyenne < 10).count()
    
    # Statistiques par niveau
    niveau_stats = []
    for niveau in niveaux:
        eleves_niveau = q.filter(Niveau.id == niveau.id).all()
        nb_eleves = len(eleves_niveau)
        if nb_eleves > 0:
            moyennes_niveau = [e.moyenne for e in eleves_niveau if e.moyenne is not None]
            moy_niveau = sum(moyennes_niveau) / len(moyennes_niveau) if moyennes_niveau else 0
            niveau_stats.append({
                'niveau': niveau.libelle,
                'moyenne': round(moy_niveau, 2)
            })
    
    # Statistiques de retards et absences par classe
    classes = Classe.query.filter_by(etat='actif').all()
    absences_retards = []
    
    for classe in classes:
        eleves_classe = q.filter(Classe.id == classe.id).all()
        nb_retards = sum([e.retard for e in eleves_classe if e.retard is not None])
        nb_absences = sum([e.absence for e in eleves_classe if e.absence is not None])
        absences_retards.append({
            'classe': classe.libelle,
            'retards': nb_retards,
            'absences': nb_absences
        })
    
    # Préparer les données pour les graphiques
    labels_niveaux = [ns['niveau'] for ns in niveau_stats]
    valeurs_moyennes = [ns['moyenne'] for ns in niveau_stats]
    
    # Si un niveau est sélectionné, récupérer ses classes pour le formulaire
    classes_filtre = []
    if niveau_id:
        classes_filtre = Classe.query.filter_by(niveau_id=niveau_id, etat='actif').all()
    
    return render_template('semestre1/moyennes_analysis.html',
                          title='Analyse des moyennes',
                          app_name=current_app.config['APP_NAME'],
                          app_version=current_app.config['APP_VERSION'],
                          active_tab='moyennes',
                          niveaux=niveaux,
                          classes=classes_filtre,
                          stats={
                              'total_eleves': total_eleves,
                              'total_filles': total_filles,
                              'total_garcons': total_garcons,
                              'pct_filles': pct_filles,
                              'pct_garcons': pct_garcons,
                              'moyenne_generale': moyenne_generale,
                              'plus_forte_moyenne': plus_forte_moyenne,
                              'plus_faible_moyenne': plus_faible_moyenne,
                              'reussite_count': reussite_count,
                              'reussite_filles': reussite_filles,
                              'reussite_garcons': reussite_garcons,
                              'taux_reussite': taux_reussite,
                              'taux_reussite_filles': taux_reussite_filles,
                              'taux_reussite_garcons': taux_reussite_garcons,
                              'felicitations': felicitations_count,
                              'encouragements': encouragements_count,
                              'tableau_honneur': tableau_honneur_count,
                              'passable': passable_count,
                              'insuffisant': insuffisant_count,
                              'mieux_faire': mieux_faire_count,
                              'doit_continuer': doit_continuer_count,
                              'risque_redoubler': risque_redoubler_count,
                              'mediane': mediane,
                              'ecart_type': ecart_type,
                              'moyenne_garcons': moyenne_garcons,
                              'moyenne_filles': moyenne_filles
                          },
                          appreciation_counts=appreciation_counts,
                          observation_counts=observation_counts,
                          niveau_stats=niveau_stats,
                          absences_retards=absences_retards,
                          labels_niveaux=labels_niveaux,
                          valeurs_moyennes=valeurs_moyennes,
                          filtres={
                              'niveau_id': niveau_id,
                              'classe_id': classe_id,
                              'sexe': sexe,
                              'note_min': note_min,
                              'note_max': note_max
                          },
                          annee_scolaire=annee_active)

@semestre1_bp.route('/api/stats/discipline')
def stats_discipline():
    classe_id = request.args.get('classe_id')
    discipline_id = request.args.get('discipline_id')
    annee = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee.libelle if annee else '2024-2025'
    # Requête notes
    query = db.session.query(NoteS1).join(Eleve, NoteS1.eleve_ien==Eleve.ien)
    if classe_id:
        query = query.filter(Eleve.classe_id==classe_id)
    if discipline_id:
        query = query.filter(NoteS1.discipline_id==discipline_id)
    query = query.filter(NoteS1.annee_scolaire==annee_active)
    notes = query.with_entities(NoteS1.moy_d)
    total = query.count()
    reussite = query.filter(NoteS1.moy_d>=10).count()
    moy = round(sum([n.moy_d or 0 for n in notes]) / total,2) if total>0 else 0
    minv = round(min([n.moy_d for n in notes if n.moy_d is not None] or [0]),2)
    maxv = round(max([n.moy_d for n in notes if n.moy_d is not None] or [0]),2)
    taux = round((reussite/total*100),2) if total>0 else 0
    return jsonify({
        'nb_eleves': total,
        'moyenne_discipline': moy,
        'nb_moyenne': reussite,
        'taux_reussite': taux,
        'min': minv,
        'max': maxv
    })

@semestre1_bp.route('/classe/<int:classe_id>')
def classe_detail(classe_id):
    """Afficher les détails d'une classe"""
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer la classe
    classe = Classe.query.get_or_404(classe_id)
    niveau = Niveau.query.get(classe.niveau_id)
    
    # Récupérer les moyennes des élèves de la classe
    moyennes = db.session.query(Eleve, MoyenneGeneraleS1).\
        join(MoyenneGeneraleS1, Eleve.ien == MoyenneGeneraleS1.eleve_ien).\
        filter(Eleve.classe_id == classe_id, MoyenneGeneraleS1.annee_scolaire == annee_active).\
        order_by(MoyenneGeneraleS1.rang).all()
    
    # Calculer les statistiques
    nb_eleves = len(moyennes)
    moy_classe = 0
    nb_moyenne = 0
    min_moy = 20
    max_moy = 0
    
    if nb_eleves > 0:
        moy_classe = sum([m.moyenne for _, m in moyennes if m.moyenne is not None]) / nb_eleves
        nb_moyenne = sum(1 for _, m in moyennes if m.moyenne is not None and m.moyenne >= 10)
        min_moy = min([m.moyenne for _, m in moyennes if m.moyenne is not None] or [0])
        max_moy = max([m.moyenne for _, m in moyennes if m.moyenne is not None] or [0])
    
    taux_reussite = (nb_moyenne / nb_eleves) * 100 if nb_eleves > 0 else 0
    
    return render_template('semestre1/classe_detail.html',
                          title=f'Classe {classe.libelle}',
                          app_name=current_app.config['APP_NAME'],
                          app_version=current_app.config['APP_VERSION'],
                          classe=classe,
                          niveau=niveau,
                          moyennes=moyennes,
                          stats={
                              'nb_eleves': nb_eleves,
                              'moyenne_classe': round(moy_classe, 2),
                              'nb_moyenne': nb_moyenne,
                              'taux_reussite': round(taux_reussite, 2),
                              'min': round(min_moy, 2),
                              'max': round(max_moy, 2)
                          })

@semestre1_bp.route('/discipline/<int:classe_id>/<int:discipline_id>')
def discipline_detail(classe_id, discipline_id):
    """Afficher les détails d'une discipline pour une classe"""
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer la classe et la discipline
    classe = Classe.query.get_or_404(classe_id)
    discipline = Discipline.query.get_or_404(discipline_id)
    niveau = Niveau.query.get(classe.niveau_id)
    
    # Récupérer les notes des élèves
    notes = db.session.query(Eleve, NoteS1).\
        join(NoteS1, Eleve.ien == NoteS1.eleve_ien).\
        filter(Eleve.classe_id == classe_id, 
               NoteS1.discipline_id == discipline_id,
               NoteS1.annee_scolaire == annee_active).\
        order_by(NoteS1.rang_d).all()
    
    # Calculer les statistiques
    nb_eleves = len(notes)
    moy_discipline = 0
    nb_moyenne = 0
    min_note = 20
    max_note = 0
    
    if nb_eleves > 0:
        moy_discipline = sum([n.moy_d for _, n in notes if n.moy_d is not None]) / nb_eleves
        nb_moyenne = sum(1 for _, n in notes if n.moy_d is not None and n.moy_d >= 10)
        min_note = min([n.moy_d for _, n in notes if n.moy_d is not None] or [0])
        max_note = max([n.moy_d for _, n in notes if n.moy_d is not None] or [0])
    
    taux_reussite = (nb_moyenne / nb_eleves) * 100 if nb_eleves > 0 else 0
    
    return render_template('semestre1/discipline_detail.html',
                          title=f'Discipline {discipline.libelle}',
                          app_name=current_app.config['APP_NAME'],
                          app_version=current_app.config['APP_VERSION'],
                          classe=classe,
                          niveau=niveau,
                          discipline=discipline,
                          notes=notes,
                          stats={
                              'nb_eleves': nb_eleves,
                              'moyenne_discipline': round(moy_discipline, 2),
                              'nb_moyenne': nb_moyenne,
                              'taux_reussite': round(taux_reussite, 2),
                              'min': round(min_note, 2),
                              'max': round(max_note, 2)
                          })

@semestre1_bp.route('/import', methods=['GET', 'POST'])
def import_data():
    """Page d'importation des données"""
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les niveaux pour le formulaire
    niveaux = Niveau.query.filter_by(etat='actif').all()
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        niveau_id = request.form.get('niveau_id')
        classe_id = request.form.get('classe_id')
        
        # Vérifier si un fichier a été soumis
        if 'file' not in request.files:
            flash('Aucun fichier sélectionné', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # Vérifier si le fichier a un nom
        if file.filename == '':
            flash('Aucun fichier sélectionné', 'danger')
            return redirect(request.url)
        
        # Vérifier si le fichier est un fichier Excel
        if file and file.filename.endswith('.xlsx'):
            # Sécuriser le nom de fichier
            filename = secure_filename(file.filename)
            
            # Chemin temporaire pour sauvegarder le fichier
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                # Traiter le fichier Excel
                result = importer_donnees_excel(filepath, niveau_id, classe_id, annee_active)
                
                if result['success']:
                    flash(f"Importation réussie: {result['message']}", 'success')
                else:
                    flash(f"Erreur lors de l'importation: {result['message']}", 'danger')
                
                try:
                    os.remove(filepath)
                except Exception:
                    pass
                
                return redirect(url_for('semestre1.index', tab='import'))
            except Exception as e:
                flash(f"Erreur lors du traitement du fichier: {str(e)}", 'danger')
                return redirect(request.url)
        else:
            flash('Le fichier doit être au format Excel (.xlsx)', 'danger')
            return redirect(request.url)
    
    # Redirect GET to main index (import tab available there)
    return redirect(url_for('semestre1.index', tab='import'))

def importer_donnees_excel(filepath, niveau_id, classe_id, annee_scolaire):
    """Importe les données d'un fichier Excel"""
    try:
        # Vérifier que le niveau et la classe existent
        niveau = Niveau.query.get(niveau_id)
        classe = Classe.query.get(classe_id)
        
        if not niveau or not classe:
            return {'success': False, 'message': 'Niveau ou classe invalide'}
        
        # Ouvrir le fichier pour vérifier les feuilles disponibles
        try:
            xls = pd.ExcelFile(filepath)
        except Exception as e:
            return {'success': False, 'message': f"Impossible d'ouvrir le fichier Excel: {str(e)}"}

        # Vérifier la présence des feuilles nécessaires
        required_sheets = ['Moyennes eleves', 'Données détaillées']
        missing_sheets = [s for s in required_sheets if s not in xls.sheet_names]
        if missing_sheets:
            xls.close()
            return {'success': False, 'message': f"Feuilles manquantes dans le fichier: {', '.join(missing_sheets)}"}

        # Lire les données
        try:
            df_moyennes = pd.read_excel(xls, sheet_name='Moyennes eleves', skiprows=range(11), header=0)
            # Accepter le header sans accent
            if 'Prenom' in df_moyennes.columns and 'Prénom' not in df_moyennes.columns:
                df_moyennes.rename(columns={'Prenom': 'Prénom'}, inplace=True)
            df_detail = pd.read_excel(xls, sheet_name='Données détaillées', skiprows=range(8), header=[0, 1])
        except Exception as e:
            xls.close()
            return {'success': False, 'message': f"Erreur lors de la lecture des feuilles Excel: {str(e)}"}
        finally:
            xls.close()

        # Nettoyer et traiter les données détaillées
        # Extraire les niveaux de colonnes et sous-colonnes
        disciplines = df_detail.columns.get_level_values(0).tolist()
        sous_colonnes = df_detail.columns.get_level_values(1).tolist()
            
        # Remplir les colonnes "Unnamed"
        for i in range(len(disciplines)):
            if "Unnamed" in disciplines[i]:
                disciplines[i] = disciplines[i - 1]
            
        # Extraction des colonnes infos (les 3 premières)
        info_colonnes = df_detail.iloc[:, :3]
        info_colonnes.columns = [col[0] for col in info_colonnes.columns]
        
        # Extraction des colonnes Moy D avec les noms exacts des disciplines
        colonnes_moy_d = []
        noms_moy_d = []
        
        # Parcourir toutes les colonnes pour identifier celles avec "Moy D" et récupérer le nom correct de la discipline
        for i, sous_col in enumerate(sous_colonnes):
            if sous_col == "Moy D":
                colonnes_moy_d.append(i)
                discipline_nom = disciplines[i].strip()
                noms_moy_d.append(discipline_nom)
        
        # Créer un DataFrame avec uniquement les colonnes Moy D
        df_detail_moy_d = df_detail.iloc[:, colonnes_moy_d]
        df_detail_moy_d.columns = noms_moy_d
            
        # Fusion info + moyennes
        df_final = pd.concat([info_colonnes, df_detail_moy_d], axis=1)
            
        # Vérifier que les colonnes obligatoires sont présentes dans df_moyennes
        required_columns_moyennes = ["IEN", "Prénom", "Nom", "Moy", "Rang"]
        missing_columns = [col for col in required_columns_moyennes if col not in df_moyennes.columns]
            
        if missing_columns:
            return {'success': False, 'message': f"Colonnes manquantes dans les moyennes: {', '.join(missing_columns)}"}
            
        # Normaliser les colonnes de df_moyennes
        # Parser les dates de naissance en date Python
        if 'Date naissance' in df_moyennes.columns:
            df_moyennes['Date naissance'] = pd.to_datetime(df_moyennes['Date naissance'], errors='coerce').dt.date
        df_moyennes["IEN"] = df_moyennes["IEN"].astype(str)
        df_moyennes["Prénom"] = df_moyennes["Prénom"].fillna("Non défini")
        df_moyennes["Nom"] = df_moyennes["Nom"].fillna("Non défini")
        # Helper to parse duration strings like '2h 15mn'
        def parse_duration(val):
            if pd.isna(val):
                return 0
            if isinstance(val, (int, float)):
                return int(val)
            m = re.match(r"(\d+)h\s*(\d+)mn", str(val))
            if m:
                return int(m.group(1)) * 60 + int(m.group(2))
            # Try to convert directly
            try:
                return int(val)
            except Exception:
                return 0
        # Helper to parse numeric strings robustly
        def parse_number(val):
            if pd.isna(val):
                return 0.0
            try:
                return float(val)
            except Exception:
                s = str(val)
                m = re.match(r"[-+]?[0-9]*\.?[0-9]+", s)
                if m:
                    return float(m.group())
                return 0.0
            
        # Supprimer les données existantes pour cette classe et ce semestre
        eleves_classe = Eleve.query.filter_by(classe_id=classe.id).all()
        eleves_ien = [e.ien for e in eleves_classe]
            
        MoyenneGeneraleS1.query.filter(MoyenneGeneraleS1.eleve_ien.in_(eleves_ien),
                                          MoyenneGeneraleS1.annee_scolaire == annee_scolaire).delete(synchronize_session=False)
            
        NoteS1.query.filter(NoteS1.eleve_ien.in_(eleves_ien),
                               NoteS1.annee_scolaire == annee_scolaire).delete(synchronize_session=False)
            
        # Importer les données
        eleves_ajoutes = 0
        disciplines_ajoutees = set()
            
        # Pour chaque élève
        for _, row in df_moyennes.iterrows():
            ien = str(row["IEN"])
            if pd.isna(ien) or ien == "":
                continue

            # Préparer la date de naissance
            # Parse 'Date naissance' into Python date
            raw_date = row.get("Date naissance", None)
            date_naissance = None
            if pd.notna(raw_date):
                if isinstance(raw_date, datetime.date):
                    date_naissance = raw_date
                else:
                    try:
                        if isinstance(raw_date, str):
                            date_naissance = datetime.datetime.strptime(raw_date, "%Y-%m-%d").date()
                        else:
                            date_naissance = pd.to_datetime(raw_date, errors='coerce').date()
                    except Exception:
                        date_naissance = None

            eleve = Eleve.query.filter_by(ien=ien).first()
            
            if not eleve:
                # Créer l'élève
                eleve = Eleve(
                    ien=ien,
                    prenom=row["Prénom"],
                    nom=row["Nom"],
                    sexe=row.get("Sexe", ""),
                    date_naissance=date_naissance,
                    lieu_naissance=row.get("Lieu naissance", ""),
                    classe_id=classe.id,
                    annee_scolaire=annee_scolaire
                )
                db.session.add(eleve)
            else:
                # Mettre à jour la classe
                eleve.classe_id = classe.id
                
            # Calculate metrics
            val_moy = row.get("Moy", 0)
            val_rang = row.get("Rang", 0)
            val_retard = row.get("Retard", 0)
            val_absence = row.get("Absence", 0)
            moy_generale = MoyenneGeneraleS1(
                eleve_ien=ien,
                moyenne=parse_number(val_moy),
                rang=int(parse_number(val_rang)),
                retard=parse_duration(val_retard),
                absence=parse_duration(val_absence),
                conseil_discipline=row.get("C.D.", ""),
                appreciation=row.get("Appréciation", ""),
                observation=row.get("Observation conseil", ""),
                annee_scolaire=annee_scolaire
            )
            db.session.add(moy_generale)
                
            eleves_ajoutes += 1
            
        # Pour chaque discipline dans df_detail_moy_d
        for discipline_nom in noms_moy_d:
            # Le nom est déjà normalisé (strip a été appliqué lors de l'extraction)
            # Si le nom normalisé est vide, ignorer cette colonne
            if not discipline_nom:
                continue

            # Rechercher la discipline par son nom normalisé
            discipline = Discipline.query.filter_by(libelle=discipline_nom).first()
            
            if not discipline:
                # Créer la discipline si elle n'existe pas
                discipline = Discipline(
                    libelle=discipline_nom,
                    coefficient=1.0, # Coefficient par défaut
                    type='principale' # Type par défaut
                )
                db.session.add(discipline)
                # Flush pour obtenir l'ID si c'est une nouvelle discipline, nécessaire pour la clé étrangère NoteS1
                db.session.flush() 
            
            disciplines_ajoutees.add(discipline_nom) # Garder une trace des disciplines traitées

            # Pour chaque élève, créer une note pour cette discipline
            for idx, row in df_final.iterrows(): 
                ien = str(row["IEN"])
                
                # Récupérer la valeur Moy D pour cette discipline
                val = row.get(discipline_nom)
                
                # Vérification de type et conversion si nécessaire
                if hasattr(val, 'values'):
                    # Si val est une Series, prendre le premier élément
                    val = val.values[0] if len(val.values) > 0 else None
                
                if pd.isna(ien) or ien == "" or pd.isna(val):
                    continue # Ignorer si IEN ou Moy D est manquant

                # Vérifier si l'élève existe (devrait avoir été créé/mis à jour plus tôt)
                eleve = Eleve.query.filter_by(ien=ien).first()
                if not eleve:
                    print(f"Avertissement: Eleve avec IEN {ien} non trouvé lors de l'enregistrement des notes pour {discipline_nom}.") 
                    continue

                # Créer ou mettre à jour la note (ici on crée, car on supprime les anciennes avant)
                note = NoteS1(
                    eleve_ien=ien,
                    discipline_id=discipline.id, # Utiliser l'ID de la discipline trouvée/créée
                    moy_dd=0, # Non disponible dans Moy D
                    comp_d=0, # Non disponible dans Moy D
                    moy_d=parse_number(val), # Utiliser la fonction parse_number pour la robustesse
                    rang_d=0,  # Rang non disponible dans les détails Moy D
                    annee_scolaire=annee_scolaire
                )
                db.session.add(note)
            
        db.session.commit() # Valider toutes les modifications (élèves, moyennes, disciplines, notes)
            
        return {
            'success': True, 
            'message': f"Importation réussie: {eleves_ajoutes} élèves et {len(disciplines_ajoutees)} disciplines."
        }
            
    except Exception as e:
        db.session.rollback() # Annuler les changements en cas d'erreur
        # Log l'erreur pour le débogage
        current_app.logger.error(f"Erreur détaillée lors de l'importation: {str(e)}", exc_info=True) 
        return {'success': False, 'message': f"Erreur lors de l'importation: {str(e)}"}

@semestre1_bp.route('/rapport/classe/<int:classe_id>')
def rapport_classe(classe_id):
    """Générer un rapport pour une classe"""
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer la classe
    classe = Classe.query.get_or_404(classe_id)
    niveau = Niveau.query.get(classe.niveau_id)
    
    # Récupérer tous les élèves et leurs moyennes
    eleves_moyennes = db.session.query(Eleve, MoyenneGeneraleS1).\
        join(MoyenneGeneraleS1, Eleve.ien == MoyenneGeneraleS1.eleve_ien).\
        filter(Eleve.classe_id == classe_id, MoyenneGeneraleS1.annee_scolaire == annee_active).\
        order_by(MoyenneGeneraleS1.rang).all()
    
    # Récupérer toutes les disciplines pour lesquelles il y a des notes
    disciplines = db.session.query(Discipline).\
        join(NoteS1, NoteS1.discipline_id == Discipline.id).\
        join(Eleve, NoteS1.eleve_ien == Eleve.ien).\
        filter(Eleve.classe_id == classe_id, NoteS1.annee_scolaire == annee_active).\
        distinct().all()
    
    # Pour chaque discipline, récupérer les notes de tous les élèves
    disciplines_notes = {}
    for discipline in disciplines:
        notes = db.session.query(Eleve, NoteS1).\
            join(NoteS1, Eleve.ien == NoteS1.eleve_ien).\
            filter(Eleve.classe_id == classe_id, 
                  NoteS1.discipline_id == discipline.id,
                  NoteS1.annee_scolaire == annee_active).\
            order_by(NoteS1.rang_d).all()
        
        disciplines_notes[discipline.id] = {
            'discipline': discipline,
            'notes': notes
        }
    
    # Calculer les statistiques de classe
    nb_eleves = len(eleves_moyennes)
    moy_classe = 0
    nb_moyenne = 0
    
    if nb_eleves > 0:
        moy_classe = sum([m.moyenne for _, m in eleves_moyennes if m.moyenne is not None]) / nb_eleves
        nb_moyenne = sum(1 for _, m in eleves_moyennes if m.moyenne is not None and m.moyenne >= 10)
    
    taux_reussite = (nb_moyenne / nb_eleves) * 100 if nb_eleves > 0 else 0
    
    return render_template('semestre1/rapport_classe.html',
                          title=f'Rapport Classe {classe.libelle}',
                          app_name=current_app.config['APP_NAME'],
                          app_version=current_app.config['APP_VERSION'],
                          classe=classe,
                          niveau=niveau,
                          eleves_moyennes=eleves_moyennes,
                          disciplines=disciplines,
                          disciplines_notes=disciplines_notes,
                          stats={
                              'nb_eleves': nb_eleves,
                              'moyenne_classe': round(moy_classe, 2),
                              'nb_moyenne': nb_moyenne,
                              'taux_reussite': round(taux_reussite, 2)
                          })

@semestre1_bp.route('/tableau-honneur')
def tableau_honneur():
    """Générer un tableau d'honneur"""
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les paramètres
    niveau_id = request.args.get('niveau_id', 'all')
    classe_id = request.args.get('classe_id', 'all')
    limit = int(request.args.get('limit', 10))
    
    # Construire la requête de base
    query = db.session.query(Eleve, MoyenneGeneraleS1, Classe, Niveau).\
        join(MoyenneGeneraleS1, Eleve.ien == MoyenneGeneraleS1.eleve_ien).\
        join(Classe, Eleve.classe_id == Classe.id).\
        join(Niveau, Classe.niveau_id == Niveau.id).\
        filter(MoyenneGeneraleS1.annee_scolaire == annee_active)
    
    # Filtrer par niveau si spécifié
    if niveau_id != 'all':
        query = query.filter(Niveau.id == niveau_id)
    
    # Filtrer par classe si spécifié
    if classe_id != 'all':
        query = query.filter(Classe.id == classe_id)
    
    # Trier par moyenne et limiter le nombre de résultats
    meilleurs_eleves = query.order_by(MoyenneGeneraleS1.moyenne.desc()).limit(limit).all()
    
    # Récupérer tous les niveaux et classes pour le formulaire
    niveaux = Niveau.query.filter_by(etat='actif').all()
    classes = Classe.query.filter_by(etat='actif').all()
    
    return render_template('semestre1/tableau_honneur.html',
                          title='Tableau d\'honneur',
                          app_name=current_app.config['APP_NAME'],
                          app_version=current_app.config['APP_VERSION'],
                          meilleurs_eleves=meilleurs_eleves,
                          niveaux=niveaux,
                          classes=classes,
                          niveau_id=niveau_id,
                          classe_id=classe_id,
                          limit=limit)

@semestre1_bp.route('/import/delete', methods=['POST'])
def delete_import():
    """Supprime les données importées pour un niveau et une classe donnés"""
    niveau_id = request.form.get('niveau_id')
    classe_id = request.form.get('classe_id')
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first().libelle
    if niveau_id and classe_id:
        # supprimer les élèves de la classe
        eleves = Eleve.query.filter_by(classe_id=classe_id).all()
        iens = [e.ien for e in eleves]
        MoyenneGeneraleS1.query.filter(
            MoyenneGeneraleS1.eleve_ien.in_(iens),
            MoyenneGeneraleS1.annee_scolaire==annee_scolaire
        ).delete(synchronize_session=False)
        NoteS1.query.filter(
            NoteS1.eleve_ien.in_(iens),
            NoteS1.annee_scolaire==annee_scolaire
        ).delete(synchronize_session=False)
        db.session.commit()
        flash(f"Import supprimé pour Niveau id={niveau_id}, Classe id={classe_id}", 'success')
    # Redirect back to the Import tab history section
    return redirect(url_for('semestre1.index', tab='import') + '#import-history')

@semestre1_bp.route('/import/delete-class', methods=['POST'])
def delete_import_class():
    """Supprime toutes les données (Moyennes & Notes) pour une classe donnée"""
    classe_id = request.form.get('class_id')
    annee_active = AnneeScolaire.query.filter_by(etat='actif').first().libelle
    if classe_id:
        eleves = Eleve.query.filter_by(classe_id=classe_id).all()
        iens = [e.ien for e in eleves]
        MoyenneGeneraleS1.query.filter(
            MoyenneGeneraleS1.eleve_ien.in_(iens),
            MoyenneGeneraleS1.annee_scolaire==annee_active
        ).delete(synchronize_session=False)
        NoteS1.query.filter(
            NoteS1.eleve_ien.in_(iens),
            NoteS1.annee_scolaire==annee_active
        ).delete(synchronize_session=False)
        db.session.commit()
        flash(f'Données dusemestre supprimées pour la classe id={classe_id}', 'success')
    return redirect(url_for('semestre1.index', tab='import') + '#import-history')

@semestre1_bp.route('/import/delete-level', methods=['POST'])
def delete_import_level():
    """Supprime toutes les données pour toutes les classes d'un niveau donné"""
    niveau_id = request.form.get('niveau_id')
    annee_active = AnneeScolaire.query.filter_by(etat='actif').first().libelle
    if niveau_id:
        classes_lv = Classe.query.filter_by(niveau_id=niveau_id).all()
        for cl in classes_lv:
            eleves = Eleve.query.filter_by(classe_id=cl.id).all()
            iens = [e.ien for e in eleves]
            MoyenneGeneraleS1.query.filter(
                MoyenneGeneraleS1.eleve_ien.in_(iens),
                MoyenneGeneraleS1.annee_scolaire==annee_active
            ).delete(synchronize_session=False)
            NoteS1.query.filter(
                NoteS1.eleve_ien.in_(iens),
                NoteS1.annee_scolaire==annee_active
            ).delete(synchronize_session=False)
        db.session.commit()
        flash(f'Données du semestre supprimées pour le niveau id={niveau_id}', 'success')
    return redirect(url_for('semestre1.index', tab='import') + '#import-history')

@semestre1_bp.route('/api/classe-eleves/<int:classe_id>')
def get_classe_eleves(classe_id):
    """Récupérer la liste des élèves d'une classe avec leurs moyennes au format JSON"""
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les données de configuration
    config = Configuration.query.first()
    
    # Récupérer la classe
    classe = Classe.query.get_or_404(classe_id)
    niveau = Niveau.query.get(classe.niveau_id)
    
    # Récupérer les élèves avec leurs moyennes
    eleves_moyennes = db.session.query(Eleve, MoyenneGeneraleS1).\
        join(MoyenneGeneraleS1, Eleve.ien == MoyenneGeneraleS1.eleve_ien).\
        filter(Eleve.classe_id == classe_id, MoyenneGeneraleS1.annee_scolaire == annee_active).\
        order_by(MoyenneGeneraleS1.rang).all()
    
    # Formater les données pour la réponse JSON
    eleves_liste = []
    for eleve, moyenne in eleves_moyennes:
        eleves_liste.append({
            'ien': eleve.ien,
            'nom': eleve.nom,
            'prenom': eleve.prenom,
            'sexe': eleve.sexe,
            'moyenne': round(moyenne.moyenne, 2) if moyenne.moyenne else 0,
            'rang': moyenne.rang,
            'retard': moyenne.retard,
            'absence': moyenne.absence,
            'appreciation': moyenne.appreciation,
            'observation': moyenne.observation,
            'conseil_discipline': moyenne.conseil_discipline
        })
    
    # Statistiques de la classe
    nb_eleves = len(eleves_moyennes)
    moy_classe = 0
    nb_moyenne = 0
    
    if nb_eleves > 0:
        moy_classe = sum([m.moyenne for _, m in eleves_moyennes if m.moyenne is not None]) / nb_eleves
        nb_moyenne = sum(1 for _, m in eleves_moyennes if m.moyenne is not None and m.moyenne >= 10)
    
    taux_reussite = (nb_moyenne / nb_eleves) * 100 if nb_eleves > 0 else 0
    
    return jsonify({
        'configuration': {
            'nom_etablissement': config.nom_etablissement if config else 'LYCÉE',
            'inspection_academique': config.inspection_academique if config else "INSPECTION D'ACADÉMIE",
            'inspection_education': config.inspection_education if config else "INSPECTION DE L'ÉDUCATION ET DE LA FORMATION"
        },
        'classe': {
            'id': classe.id,
            'libelle': classe.libelle,
            'niveau': niveau.libelle,
            'niveau_id': niveau.id
        },
        'statistiques': {
            'nb_eleves': nb_eleves,
            'moyenne_classe': round(moy_classe, 2),
            'nb_moyenne': nb_moyenne,
            'taux_reussite': round(taux_reussite, 2)
        },
        'eleves': eleves_liste,
        'annee_scolaire': annee_active
    })

@semestre1_bp.route('/discipline-analysis')
def discipline_analysis():
    """Page d'analyse par discipline (dashboard complet)"""
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    discipline_id = request.args.get('discipline_id')
    sexe = request.args.get('sexe')
    note_min = request.args.get('note_min', '0')
    note_max = request.args.get('note_max', '20')
    try:
        note_min = float(note_min)
        note_max = float(note_max)
    except (ValueError, TypeError):
        note_min = 0
        note_max = 20
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    niveaux = Niveau.query.filter_by(etat='actif').all()
    classes = Classe.query.filter_by(niveau_id=niveau_id, etat='actif').all() if niveau_id else []
    disciplines = db.session.query(Discipline).join(NoteS1, NoteS1.discipline_id == Discipline.id)
    if classe_id:
        disciplines = disciplines.join(Eleve, NoteS1.eleve_ien == Eleve.ien).filter(Eleve.classe_id == classe_id, NoteS1.annee_scolaire == annee_active)
    else:
        disciplines = []
    disciplines = disciplines.distinct().all() if classe_id else []
    stats = None
    notes_list = []
    mentions = {
        'Félicitations': 0,
        'Encouragements': 0,
        "Tableau d'honneur": 0,
        'Passable': 0,
        'Doit redoubler d\'effort': 0,
        'Avertissement': 0,
        'Blâme': 0
    }
    if discipline_id:
        # Construction de la requête filtrée
        query = db.session.query(NoteS1, Eleve, Classe, Niveau).join(Eleve, NoteS1.eleve_ien==Eleve.ien)
        query = query.join(Classe, Eleve.classe_id==Classe.id).join(Niveau, Classe.niveau_id==Niveau.id)
        query = query.filter(NoteS1.discipline_id==discipline_id, NoteS1.annee_scolaire==annee_active)
        if niveau_id:
            query = query.filter(Niveau.id==niveau_id)
        if classe_id:
            query = query.filter(Classe.id==classe_id)
        # Construire les requêtes sans filtres de notes ou sexe pour obtenir les totaux
        query_sans_filtres = query
        
        # Appliquer filtres de sexe si demandé
        if sexe == 'M':
            query = query.filter(Eleve.sexe.in_(['M', 'H']))
        elif sexe == 'F':
            query = query.filter(Eleve.sexe=='F')
            
        # Appliquer filtres de notes
        query = query.filter(NoteS1.moy_d >= note_min, NoteS1.moy_d <= note_max)
        
        # Récupérer les notes avec sexe de l'élève
        notes = query.with_entities(NoteS1.moy_d, Eleve.sexe).all()
        
        # Compter les élèves correspondant aux critères de filtrage
        total_eleves_filtres = query.count()
        
        # Liste des notes non nulles pour calculs statistiques
        notes_list = [n[0] for n in notes if n[0] is not None]
        
        # Calculs généraux
        total = total_eleves_filtres
        reussite = len([n for n in notes_list if n >= 10])
        moy = round(sum(notes_list) / len(notes_list), 2) if notes_list else 0
        minv = round(min(notes_list), 2) if notes_list else 0
        maxv = round(max(notes_list), 2) if notes_list else 0
        taux = round((reussite / total) * 100, 2) if total > 0 else 0
        
        # CORRECTION: Calculs par sexe en prenant en compte les filtres de notes
        # Compter le nombre total de filles et garçons DANS L'INTERVALLE DE NOTES spécifié
        # Si un sexe est spécifié, on utilise les totaux filtrés par sexe
        if sexe == 'F':
            total_filles = total_eleves_filtres
            total_garcons = 0
        elif sexe == 'M':
            total_filles = 0
            total_garcons = total_eleves_filtres
        else:
            # Si aucun filtre de sexe n'est appliqué, on compte par sexe dans l'intervalle
            total_filles = query.filter(Eleve.sexe == 'F').count()
            total_garcons = query.filter(Eleve.sexe.in_(['M', 'H'])).count()
        
        # Pourcentages du total général
        pct_filles = round((total_filles / total) * 100) if total > 0 else 0
        pct_garcons = round((total_garcons / total) * 100) if total > 0 else 0
        
        # Nombre d'élèves ayant la moyenne (>=10) par sexe, dans l'intervalle spécifié
        reussite_filles = query.filter(Eleve.sexe == 'F', NoteS1.moy_d >= 10).count()
        reussite_garcons = query.filter(Eleve.sexe.in_(['M', 'H']), NoteS1.moy_d >= 10).count()
        
        # Taux de réussite par sexe (en pourcentage du total par sexe)
        taux_reussite_filles = round((reussite_filles / total_filles) * 100) if total_filles > 0 else 0
        taux_reussite_garcons = round((reussite_garcons / total_garcons) * 100) if total_garcons > 0 else 0
        
        # Médiane et écart-type
        import pandas as pd
        mediane = round(float(pd.Series(notes_list).median()), 2) if notes_list else 0
        ecart_type = round(float(pd.Series(notes_list).std()), 2) if notes_list else 0
        
        # Répartition des mentions
        for n in notes_list:
            if n >= 17:
                mentions['Félicitations'] += 1
            elif n >= 14:
                mentions['Encouragements'] += 1
            elif n >= 12:
                mentions["Tableau d'honneur"] += 1
            elif n >= 10:
                mentions['Passable'] += 1
            elif n >= 8:
                mentions["Doit redoubler d'effort"] += 1
            elif n >= 6:
                mentions['Avertissement'] += 1
            else:
                mentions['Blâme'] += 1

        stats = {
            'nb_eleves': total,
            'total_filles': total_filles,
            'total_garcons': total_garcons,
            'pct_filles': pct_filles,
            'pct_garcons': pct_garcons,
            'moyenne_discipline': moy,
            'nb_moyenne': reussite,
            'reussite_filles': reussite_filles,
            'reussite_garcons': reussite_garcons,
            'taux_reussite': taux,
            'taux_reussite_filles': taux_reussite_filles,
            'taux_reussite_garcons': taux_reussite_garcons,
            'min': minv,
            'max': maxv,
            'mediane': mediane,
            'ecart_type': ecart_type,
            'mentions': mentions
        }
    # Préparer les données pour les graphiques (Chart.js)
    notes_hist = [0]*5  # [0-5, 5-8, 8-10, 10-15, 15-20]
    if notes_list:
        for n in notes_list:
            if n < 5:
                notes_hist[0] += 1
            elif n < 8:
                notes_hist[1] += 1
            elif n < 10:
                notes_hist[2] += 1
            elif n < 15:
                notes_hist[3] += 1
            else:
                notes_hist[4] += 1
    chart_data = {
        'labels': ['0-5', '5-8', '8-10', '10-15', '15-20'],
        'data': notes_hist
    }
    mentions_labels = list(mentions.keys())
    mentions_data = list(mentions.values())
    return render_template('semestre1/discipline_analysis.html',
        title='Analyse par discipline',
        app_name=current_app.config['APP_NAME'],
        app_version=current_app.config['APP_VERSION'],
        niveaux=niveaux,
        classes=classes,
        disciplines=disciplines,
        stats=stats,
        filtres={
            'niveau_id': niveau_id,
            'classe_id': classe_id,
            'discipline_id': discipline_id,
            'sexe': sexe,
            'note_min': note_min,
            'note_max': note_max
        },
        annee_scolaire=annee_active,
        chart_data=chart_data,
        mentions_labels=mentions_labels,
        mentions_data=mentions_data
    )

@semestre1_bp.route('/api/disciplines')
def api_get_disciplines_all():
    """API pour récupérer toutes les disciplines"""
    disciplines = Discipline.query.order_by(Discipline.libelle).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/<int:classe_id>')
def api_get_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines d'une classe spécifique"""
    # Récupérer la classe pour déterminer le niveau
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à cette classe via l'année en cours
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).filter(
        Eleve.classe_id == classe_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>')
def api_get_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines d'un niveau spécifique"""
    # Récupérer l'année active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes pour ce niveau
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).filter(
        Classe.niveau_id == niveau_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])

@semestre1_bp.route('/api/discipline_report/details')
def api_discipline_report_detailed():
    """API pour générer un rapport d'analyse par discipline (version détaillée)"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id', type=int)
    classe_id = request.args.get('classe_id', type=int)
    niveau_id = request.args.get('niveau_id', type=int)
    
    if not discipline_id:
        return jsonify({'error': 'Discipline non spécifiée'}), 400
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Construire la requête de base
    query = db.session.query(
        NoteS1.valeur.label('note'),
        Eleve.sexe,
        Classe.id.label('classe_id'),
        Classe.libelle.label('classe_libelle'),
        Niveau.id.label('niveau_id'),
        Niveau.libelle.label('niveau_libelle')
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).join(
        Niveau, Classe.niveau_id == Niveau.id
    ).filter(
        NoteS1.discipline_id == discipline_id,
        NoteS1.annee_scolaire == annee_active
    )
    
    # Filtrer par classe si spécifié
    if classe_id:
        query = query.filter(Classe.id == classe_id)
    
    # Filtrer par niveau si spécifié
    if niveau_id:
        query = query.filter(Niveau.id == niveau_id)
    
    # Exécuter la requête
    results = query.all()
    
    if not results:
        return jsonify({'error': 'Aucune donnée pour cette discipline'}), 404
    
    # Calculer les statistiques générales
    all_notes = [r.note for r in results]
    average = sum(all_notes) / len(all_notes)
    highest = max(all_notes)
    lowest = min(all_notes)
    total_students = len(all_notes)
    
    # Calculer la distribution des notes
    distribution = [0] * 7  # [0-5, 5-10, 10-12, 12-14, 14-16, 16-18, 18-20]
    for note in all_notes:
        if note < 5:
            distribution[0] += 1
        elif note < 10:
            distribution[1] += 1
        elif note < 12:
            distribution[2] += 1
        elif note < 14:
            distribution[3] += 1
        elif note < 16:
            distribution[4] += 1
        elif note < 18:
            distribution[5] += 1
        else:
            distribution[6] += 1
    
    # Regrouper les résultats par classe
    class_results = {}
    for r in results:
        if r.classe_id not in class_results:
            class_results[r.classe_id] = {
                'classe_id': r.classe_id,
                'classe_libelle': r.classe_libelle,
                'niveau_id': r.niveau_id,
                'niveau_libelle': r.niveau_libelle,
                'notes': []
            }
        class_results[r.classe_id]['notes'].append(r.note)
    
    # Calculer les statistiques par classe
    class_stats = []
    for class_id, data in class_results.items():
        notes = data['notes']
        class_stats.append({
            'classe_id': data['classe_id'],
            'classe_libelle': data['classe_libelle'],
            'niveau_id': data['niveau_id'],
            'niveau_libelle': data['niveau_libelle'],
            'average': sum(notes) / len(notes),
            'highest': max(notes),
            'lowest': min(notes),
            'total_students': len(notes)
        })
    
    # Trier les résultats par moyenne décroissante
    class_stats.sort(key=lambda x: x['average'], reverse=True)
    
    # Construire la réponse
    response = {
        'discipline_id': discipline_id,
        'discipline_name': discipline.libelle,
        'niveau_id': niveau_id,
        'classe_id': classe_id,
        'results': class_stats,
        'general_stats': {
            'average': average,
            'highest': highest,
            'lowest': lowest,
            'total_students': total_students
        },
        'distribution': distribution
    }
    
    return jsonify(response)
    """API pour générer un rapport d'analyse par discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id', type=int)
    classe_id = request.args.get('classe_id', type=int)
    niveau_id = request.args.get('niveau_id', type=int)
    
    if not discipline_id:
        return jsonify({'error': 'Discipline non spécifiée'}), 400
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Construire la requête de base
    query = db.session.query(
        NoteS1.valeur.label('note'),
        Eleve.sexe,
        Classe.id.label('classe_id'),
        Classe.libelle.label('classe_libelle'),
        Niveau.id.label('niveau_id'),
        Niveau.libelle.label('niveau_libelle')
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).join(
        Niveau, Classe.niveau_id == Niveau.id
    ).filter(
        NoteS1.discipline_id == discipline_id,
        NoteS1.annee_scolaire == annee_active
    )
    
    # Filtrer par classe si spécifié
    if classe_id:
        query = query.filter(Classe.id == classe_id)
    
    # Filtrer par niveau si spécifié
    if niveau_id:
        query = query.filter(Niveau.id == niveau_id)
    
    # Exécuter la requête
    results = query.all()
    
    if not results:
        return jsonify({'error': 'Aucune donnée pour cette discipline'}), 404
    
    # Calculer les statistiques générales
    all_notes = [r.note for r in results]
    average = sum(all_notes) / len(all_notes)
    highest = max(all_notes)
    lowest = min(all_notes)
    total_students = len(all_notes)
    
    # Calculer la distribution des notes
    distribution = [0] * 7  # [0-5, 5-10, 10-12, 12-14, 14-16, 16-18, 18-20]
    for note in all_notes:
        if note < 5:
            distribution[0] += 1
        elif note < 10:
            distribution[1] += 1
        elif note < 12:
            distribution[2] += 1
        elif note < 14:
            distribution[3] += 1
        elif note < 16:
            distribution[4] += 1
        elif note < 18:
            distribution[5] += 1
        else:
            distribution[6] += 1
    
    # Regrouper les résultats par classe
    class_results = {}
    for r in results:
        if r.classe_id not in class_results:
            class_results[r.classe_id] = {
                'classe_id': r.classe_id,
                'classe_libelle': r.classe_libelle,
                'niveau_id': r.niveau_id,
                'niveau_libelle': r.niveau_libelle,
                'notes': []
            }
        class_results[r.classe_id]['notes'].append(r.note)
    
    # Calculer les statistiques par classe
    class_stats = []
    for class_id, data in class_results.items():
        notes = data['notes']
        class_stats.append({
            'classe_id': data['classe_id'],
            'classe_libelle': data['classe_libelle'],
            'niveau_id': data['niveau_id'],
            'niveau_libelle': data['niveau_libelle'],
            'average': sum(notes) / len(notes),
            'highest': max(notes),
            'lowest': min(notes),
            'total_students': len(notes)
        })
    
    # Trier les résultats par moyenne décroissante
    class_stats.sort(key=lambda x: x['average'], reverse=True)
    
    # Construire la réponse
    response = {
        'discipline_id': discipline_id,
        'discipline_name': discipline.libelle,
        'niveau_id': niveau_id,
        'classe_id': classe_id,
        'results': class_stats,
        'general_stats': {
            'average': average,
            'highest': highest,
            'lowest': lowest,
            'total_students': total_students
        },
        'distribution': distribution
    }
    
    return jsonify(response)
    """API pour générer un rapport d'analyse par discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id', type=int)
    classe_id = request.args.get('classe_id', type=int)
    niveau_id = request.args.get('niveau_id', type=int)
    
    if not discipline_id:
        return jsonify({'error': 'Discipline non spécifiée'}), 400
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Construire la requête de base
    query = db.session.query(
        NoteS1.valeur.label('note'),
        Eleve.sexe,
        Classe.id.label('classe_id'),
        Classe.libelle.label('classe_libelle'),
        Niveau.id.label('niveau_id'),
        Niveau.libelle.label('niveau_libelle')
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).join(
        Niveau, Classe.niveau_id == Niveau.id
    ).filter(
        NoteS1.discipline_id == discipline_id,
        NoteS1.annee_scolaire == annee_active
    )
    
    # Filtrer par classe si spécifié
    if classe_id:
        query = query.filter(Classe.id == classe_id)
    
    # Filtrer par niveau si spécifié
    if niveau_id:
        query = query.filter(Niveau.id == niveau_id)
    
    # Exécuter la requête
    results = query.all()
    
    if not results:
        return jsonify({
            'discipline_id': discipline_id,
            'discipline_name': discipline.libelle,
            'niveau_id': niveau_id,
            'classe_id': classe_id,
            'results': [],
            'general_stats': {
                'average': 0,
                'highest': 0,
                'lowest': 0,
                'total_students': 0
            },
            'distribution': [0, 0, 0, 0, 0, 0, 0]  # Distribution vide
        })
    
    # Calculer les statistiques générales
    all_notes = [r.note for r in results]
    average = sum(all_notes) / len(all_notes)
    highest = max(all_notes)
    lowest = min(all_notes)
    total_students = len(all_notes)
    
    # Calculer la distribution des notes
    distribution = [0] * 7  # [0-5, 5-10, 10-12, 12-14, 14-16, 16-18, 18-20]
    for note in all_notes:
        if note < 5:
            distribution[0] += 1
        elif note < 10:
            distribution[1] += 1
        elif note < 12:
            distribution[2] += 1
        elif note < 14:
            distribution[3] += 1
        elif note < 16:
            distribution[4] += 1
        elif note < 18:
            distribution[5] += 1
        else:
            distribution[6] += 1
    
    # Regrouper les résultats par classe
    class_results = {}
    for r in results:
        class_id = r.classe_id
        if class_id not in class_results:
            class_results[class_id] = {
                'classe_id': class_id,
                'classe_name': r.classe_libelle,
                'notes': []
            }
        class_results[class_id]['notes'].append(r.note)
    
    # Calculer les statistiques par classe
    class_stats = []
    for class_id, data in class_results.items():
        notes = data['notes']
        class_stats.append({
            'classe_id': data['classe_id'],
            'classe_name': data['classe_name'],
            'average': sum(notes) / len(notes),
            'highest': max(notes),
            'lowest': min(notes),
            'student_count': len(notes)
        })
    
    # Trier les résultats par moyenne décroissante
    class_stats.sort(key=lambda x: x['average'], reverse=True)
    
    # Construire la réponse
    response = {
        'discipline_id': discipline_id,
        'discipline_name': discipline.libelle,
        'niveau_id': niveau_id,
        'classe_id': classe_id,
        'results': class_stats,
        'general_stats': {
            'average': average,
            'highest': highest,
            'lowest': lowest,
            'total_students': total_students
        },
        'distribution': distribution
    }
    
    return jsonify(response)

@semestre1_bp.route('/api/disciplines_by_niveau/<int:niveau_id>')
def api_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines par niveau"""
    disciplines = Discipline.query.filter_by(niveau_id=niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/api/disciplines_by_classe/<int:classe_id>')
def api_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines par classe"""
    # Récupérer le niveau associé à la classe
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à ce niveau
    disciplines = Discipline.query.filter_by(niveau_id=classe.niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/discipline_analysis')
@login_required
def discipline_analysis_admin():
    """Page for analyzing discipline statistics"""
    # Get all niveaux for filtering
    niveaux = Niveau.query.all()
    
    # Get all disciplines initially (will be filtered by JS)
    disciplines = Discipline.query.all()
    
    # Get current date for reporting
    current_date = datetime.datetime.now().strftime("%d/%m/%Y")
    
    return render_template(
        'semestre1/discipline_analysis.html',
        title='Analyse par Discipline',
        niveaux=niveaux,
        disciplines=disciplines,
        current_date=current_date
    )

@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>', methods=['GET'])
def get_disciplines_by_niveau_v2(niveau_id):
    """API route to get disciplines by niveau"""
    try:
        # Get all disciplines for classes in this niveau
        classes = Classe.query.filter_by(niveau_id=niveau_id).all()
        classe_ids = [c.id for c in classes]
        # Find disciplines associated with these classes
        disciplines = Discipline.query.filter(Discipline.classe_id.in_(classe_ids)).all()
        disciplines_data = [{'id': d.id, 'libelle': d.libelle} for d in disciplines]
        return jsonify(disciplines_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        return jsonify(disciplines_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        return jsonify(disciplines_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        return jsonify({'status': 'success', 'disciplines': disciplines_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@semestre1_bp.route('/api/stats/discipline')
def discipline_stats():
    """API pour récupérer les statistiques d'une discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    sexe = request.args.get('sexe')
    note_min = request.args.get('note_min', '0')
    note_max = request.args.get('note_max', '20')
    
    # Convertir en float pour les comparaisons
    try:
        note_min = float(note_min)
        note_max = float(note_max)
    except (ValueError, TypeError):
        note_min = 0
        note_max = 20
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Vérifier si la discipline est spécifiée
    if not discipline_id:
        return jsonify({'error': 'Une discipline doit être spécifiée'}), 400
    
    # Construire la requête de base
    q = db.session.query(NoteS1).join(Eleve, NoteS1.eleve_ien == Eleve.ien)
    q = q.join(Classe, Eleve.classe_id == Classe.id)
    q = q.join(Niveau, Classe.niveau_id == Niveau.id)
    
    # Appliquer les filtres
    q = q.filter(NoteS1.annee_scolaire == annee_active)
    q = q.filter(NoteS1.discipline_id == discipline_id)
    
    if niveau_id:
        q = q.filter(Niveau.id == niveau_id)
    
    if classe_id:
        q = q.filter(Classe.id == classe_id)
    
    if sexe:
        if sexe == 'M':
            q = q.filter(Eleve.sexe.in_(['M', 'H']))
        else:
            q = q.filter(Eleve.sexe == 'F')
    
    q = q.filter(NoteS1.moy_d >= note_min, NoteS1.moy_d <= note_max)
    
    # Récupérer les données
    resultats = q.all()
    
    # Statistiques globales
    total_eleves = len(resultats)
    
    # Initialiser les statistiques
    stats = {
        'nb_eleves': 0,
        'moyenne_discipline': 0,
        'nb_moyenne': 0,
        'taux_reussite': 0,
        'min': 0,
        'max': 0
    }
    
    if total_eleves > 0:
        # Extraire les moyennes valides
        moyennes = [r.moy_d for r in resultats if r.moy_d is not None]
        
        # Calculer les statistiques
        stats = {
            'nb_eleves': total_eleves,
            'moyenne_discipline': round(sum(moyennes) / len(moyennes), 2) if moyennes else 0,
            'nb_moyenne': q.filter(NoteS1.moy_d >= 10).count(),
            'taux_reussite': round((q.filter(NoteS1.moy_d >= 10).count() / total_eleves * 100) if total_eleves > 0 else 0),
            'min': round(min(moyennes), 2) if moyennes else 0,
            'max': round(max(moyennes), 2) if moyennes else 0
        }
    
    return jsonify(stats)


 

@semestre1_bp.route('/api/report/discipline', methods=['POST'])
def api_generate_discipline_report():
    """
    API pour générer un rapport de discipline.
    Paramètres:
    - discipline_id: ID de la discipline
    - niveau_id: (optionnel) ID du niveau
    - classe_id: (optionnel) ID de la classe
    """
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    
    if not discipline_id:
        return jsonify({'error': 'discipline_id est obligatoire'}), 400
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Construire la requête de base pour les notes
    query = db.session.query(NoteS1, Eleve).\
        join(Eleve, NoteS1.eleve_ien == Eleve.ien).\
        join(Classe, Eleve.classe_id == Classe.id).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active)
    
    # Appliquer les filtres
    if niveau_id:
        query = query.join(Classe, Eleve.classe_id == Classe.id).\
                filter(Classe.niveau_id == niveau_id)
    if classe_id:
        query = query.filter(Eleve.classe_id == classe_id)
    
    # Récupérer les données
    notes_eleves = query.all()
    
    if not notes_eleves:
        return jsonify({'error': 'Aucune donnée trouvée pour ces critères'}), 404
    
    # Calculer les statistiques globales
    notes = [n.moy_d for n, _ in notes_eleves if n.moy_d is not None]
    total_eleves = len(notes)
    
    if total_eleves == 0:
        return jsonify({'error': 'Aucune note valide trouvée pour ces critères'}), 404
    
    # Statistiques générales
    moyenne = sum(notes) / total_eleves
    min_note = min(notes)
    max_note = max(notes)
    
    # Utiliser pandas pour calculer la médiane et l'écart-type
    notes_series = pd.Series(notes)
    mediane = float(notes_series.median())
    ecart_type = float(notes_series.std())
    
    # Statistiques par sexe
    notes_garcons = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe in ('M', 'H')]
    notes_filles = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe == 'F']
    
    total_garcons = len(notes_garcons)
    total_filles = len(notes_filles)
    
    moyenne_garcons = sum(notes_garcons) / total_garcons if total_garcons > 0 else 0
    moyenne_filles = sum(notes_filles) / total_filles if total_filles > 0 else 0
    
    reussite_garcons = sum(1 for n in notes_garcons if n >= 10)
    reussite_filles = sum(1 for n in notes_filles if n >= 10)
    
    taux_reussite_global = sum(1 for n in notes if n >= 10) / total_eleves * 100
    taux_reussite_garcons = reussite_garcons / total_garcons * 100 if total_garcons > 0 else 0
    taux_reussite_filles = reussite_filles / total_filles * 100 if total_filles > 0 else 0
    
    pct_garcons = (total_garcons / total_eleves * 100) if total_eleves > 0 else 0
    pct_filles = (total_filles / total_eleves * 100) if total_eleves > 0 else 0
    
    # Répartition par tranches de notes
    tranches = {
        'tres_bien': sum(1 for n in notes if n >= 16),
        'bien': sum(1 for n in notes if 14 <= n < 16),
        'assez_bien': sum(1 for n in notes if 12 <= n < 14),
        'passable': sum(1 for n in notes if 10 <= n < 12),
        'insuffisant': sum(1 for n in notes if n < 10)
    }
    
    # Récupérer la configuration de l'application
    config = Configuration.query.first()
    
    # Récupérer le niveau et la classe si spécifiés
    niveau = Niveau.query.get(niveau_id) if niveau_id else None
    classe = Classe.query.get(classe_id) if classe_id else None
    
    # Calculer la moyenne générale de l'établissement pour comparaison
    all_moyennes = db.session.query(NoteS1.moy_d).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active,
               NoteS1.moy_d.isnot(None)).all()
    
    all_moyenne = sum([m.moy_d for m in all_moyennes]) / len(all_moyennes) if all_moyennes else 0
    difference_moyenne = moyenne - all_moyenne
    
    # Préparer les données de retour
    report_data = {
        'stats': {
            'total_eleves': total_eleves,
            'moyenne_generale': round(moyenne, 2),
            'eleves_moyenne': sum(1 for n in notes if n >= 10),
            'taux_reussite': round(taux_reussite_global, 2),
            'min': round(min_note, 2),
            'max': round(max_note, 2),
            'mediane': round(mediane, 2),
            'ecart_type': round(ecart_type, 2),
            'total_garcons': total_garcons,
            'total_filles': total_filles,
            'pct_garcons': round(pct_garcons, 2),
            'pct_filles': round(pct_filles, 2),
            'moyenne_garcons': round(moyenne_garcons, 2),
            'moyenne_filles': round(moyenne_filles, 2),
            'reussite_garcons': reussite_garcons,
            'reussite_filles': reussite_filles,
            'taux_reussite_garcons': round(taux_reussite_garcons, 2),
            'taux_reussite_filles': round(taux_reussite_filles, 2),
            'tranches': tranches,
            'moyenne_generale_etablissement': round(all_moyenne, 2),
            'difference_moyenne': round(difference_moyenne, 2)
        },
        'config': {
            'nom_etablissement': config.nom_etablissement if config else 'Établissement'
        },
        'filter': {
            'discipline': discipline.libelle,
            'niveau': niveau.libelle if niveau else None,
            'classe': classe.libelle if classe else None
        },
        'annee_scolaire': annee_active
    }
    
    # Enregistrer le rapport pour référence ultérieure
    import json
    import datetime
    
    now = datetime.datetime.now()
    rapport = Rapport(
        type='discipline',
        date_creation=now,
        contenu=json.dumps(report_data),
        discipline_id=discipline_id,
        niveau_id=niveau_id,
        classe_id=classe_id,
        annee_scolaire=annee_active
    )
    db.session.add(rapport)
    db.session.commit()
    
    # Ajouter l'ID du rapport aux données de retour
    report_data['rapport_id'] = rapport.id
    
    return jsonify(report_data)

@semestre1_bp.route('/api/disciplines')
def api_get_all_disciplines():
    """API pour récupérer toutes les disciplines existantes pour l'année scolaire active (pour filtre global)"""
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    disciplines = db.session.query(Discipline).join(NoteS1, NoteS1.discipline_id == Discipline.id)
    disciplines = disciplines.filter(NoteS1.annee_scolaire == annee_active).distinct().all()
    return jsonify([{'id': d.id, 'libelle': d.libelle} for d in disciplines])


@semestre1_bp.route('/api/disciplines/<int:classe_id>')
def api_get_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines d'une classe spécifique"""
    # Récupérer la classe pour déterminer le niveau
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à cette classe via l'année en cours
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).filter(
        Eleve.classe_id == classe_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>')
def api_get_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines d'un niveau spécifique"""
    # Récupérer l'année active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes pour ce niveau
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).filter(
        Classe.niveau_id == niveau_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])

@semestre1_bp.route('/api/discipline_report')
def api_discipline_report_data():
    """API pour générer un rapport d'analyse par discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id', type=int)
    classe_id = request.args.get('classe_id', type=int)
    niveau_id = request.args.get('niveau_id', type=int)
    
    if not discipline_id:
        return jsonify({'error': 'Discipline non spécifiée'}), 400
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Construire la requête de base
    query = db.session.query(
        NoteS1.valeur.label('note'),
        Eleve.sexe,
        Classe.id.label('classe_id'),
        Classe.libelle.label('classe_libelle'),
        Niveau.id.label('niveau_id'),
        Niveau.libelle.label('niveau_libelle')
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).join(
        Niveau, Classe.niveau_id == Niveau.id
    ).filter(
        NoteS1.discipline_id == discipline_id,
        NoteS1.annee_scolaire == annee_active
    )
    
    # Filtrer par classe si spécifié
    if classe_id:
        query = query.filter(Classe.id == classe_id)
    
    # Filtrer par niveau si spécifié
    if niveau_id:
        query = query.filter(Niveau.id == niveau_id)
    
    # Exécuter la requête
    results = query.all()
    
    if not results:
        return jsonify({
            'discipline_id': discipline_id,
            'discipline_name': discipline.libelle,
            'niveau_id': niveau_id,
            'classe_id': classe_id,
            'results': [],
            'general_stats': {
                'average': 0,
                'highest': 0,
                'lowest': 0,
                'total_students': 0
            },
            'distribution': [0, 0, 0, 0, 0, 0, 0]  # Distribution vide
        })
    
    # Calculer les statistiques générales
    all_notes = [r.note for r in results]
    average = sum(all_notes) / len(all_notes)
    highest = max(all_notes)
    lowest = min(all_notes)
    total_students = len(all_notes)
    
    # Calculer la distribution des notes
    distribution = [0] * 7  # [0-5, 5-10, 10-12, 12-14, 14-16, 16-18, 18-20]
    for note in all_notes:
        if note < 5:
            distribution[0] += 1
        elif note < 10:
            distribution[1] += 1
        elif note < 12:
            distribution[2] += 1
        elif note < 14:
            distribution[3] += 1
        elif note < 16:
            distribution[4] += 1
        elif note < 18:
            distribution[5] += 1
        else:
            distribution[6] += 1
    
    # Regrouper les résultats par classe
    class_results = {}
    for r in results:
        class_id = r.classe_id
        if class_id not in class_results:
            class_results[class_id] = {
                'classe_id': class_id,
                'classe_name': r.classe_libelle,
                'notes': []
            }
        class_results[class_id]['notes'].append(r.note)
    
    # Calculer les statistiques par classe
    class_stats = []
    for class_id, data in class_results.items():
        notes = data['notes']
        class_stats.append({
            'classe_id': data['classe_id'],
            'classe_name': data['classe_name'],
            'average': sum(notes) / len(notes),
            'highest': max(notes),
            'lowest': min(notes),
            'student_count': len(notes)
        })
    
    # Trier les résultats par moyenne décroissante
    class_stats.sort(key=lambda x: x['average'], reverse=True)
    
    # Construire la réponse
    response = {
        'discipline_id': discipline_id,
        'discipline_name': discipline.libelle,
        'niveau_id': niveau_id,
        'classe_id': classe_id,
        'results': class_stats,
        'general_stats': {
            'average': average,
            'highest': highest,
            'lowest': lowest,
            'total_students': total_students
        },
        'distribution': distribution
    }
    
    return jsonify(response)

@semestre1_bp.route('/api/disciplines_by_niveau/<int:niveau_id>')
def api_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines par niveau"""
    disciplines = Discipline.query.filter_by(niveau_id=niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/api/disciplines_by_classe/<int:classe_id>')
def api_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines par classe"""
    # Récupérer le niveau associé à la classe
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à ce niveau
    disciplines = Discipline.query.filter_by(niveau_id=classe.niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/discipline_analysis')
@login_required
def discipline_analysis_admin():
    """Page for analyzing discipline statistics"""
    # Get all niveaux for filtering
    niveaux = Niveau.query.all()
    
    # Get all disciplines initially (will be filtered by JS)
    disciplines = Discipline.query.all()
    
    # Get current date for reporting
    current_date = datetime.datetime.now().strftime("%d/%m/%Y")
    
    return render_template(
        'semestre1/discipline_analysis.html',
        title='Analyse par Discipline',
        niveaux=niveaux,
        disciplines=disciplines,
        current_date=current_date
    )

@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>', methods=['GET'])
def get_disciplines_by_niveau_v2(niveau_id):
    """API route to get disciplines by niveau"""
    try:
        # Get all disciplines for classes in this niveau
        classes = Classe.query.filter_by(niveau_id=niveau_id).all()
        classe_ids = [c.id for c in classes]
        
        # Find disciplines associated with these classes
        disciplines = Discipline.query.filter(Discipline.classe_id.in_(classe_ids)).all()
        
        disciplines_data = [{'id': d.id, 'libelle': d.libelle} for d in disciplines]
        return jsonify({'status': 'success', 'disciplines': disciplines_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@semestre1_bp.route('/api/stats/discipline')
def discipline_stats():
    """API pour récupérer les statistiques d'une discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    sexe = request.args.get('sexe')
    note_min = request.args.get('note_min', '0')
    note_max = request.args.get('note_max', '20')
    
    # Convertir en float pour les comparaisons
    try:
        note_min = float(note_min)
        note_max = float(note_max)
    except (ValueError, TypeError):
        note_min = 0
        note_max = 20
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Vérifier si la discipline est spécifiée
    if not discipline_id:
        return jsonify({'error': 'Une discipline doit être spécifiée'}), 400
    
    # Construire la requête de base
    q = db.session.query(NoteS1).join(Eleve, NoteS1.eleve_ien == Eleve.ien)
    q = q.join(Classe, Eleve.classe_id == Classe.id)
    q = q.join(Niveau, Classe.niveau_id == Niveau.id)
    
    # Appliquer les filtres
    q = q.filter(NoteS1.annee_scolaire == annee_active)
    q = q.filter(NoteS1.discipline_id == discipline_id)
    
    if niveau_id:
        q = q.filter(Niveau.id == niveau_id)
    
    if classe_id:
        q = q.filter(Classe.id == classe_id)
    
    if sexe:
        if sexe == 'M':
            q = q.filter(Eleve.sexe.in_(['M', 'H']))
        else:
            q = q.filter(Eleve.sexe == 'F')
    
    q = q.filter(NoteS1.moy_d >= note_min, NoteS1.moy_d <= note_max)
    
    # Récupérer les données
    resultats = q.all()
    
    # Statistiques globales
    total_eleves = len(resultats)
    
    # Initialiser les statistiques
    stats = {
        'nb_eleves': 0,
        'moyenne_discipline': 0,
        'nb_moyenne': 0,
        'taux_reussite': 0,
        'min': 0,
        'max': 0
    }
    
    if total_eleves > 0:
        # Extraire les moyennes valides
        moyennes = [r.moy_d for r in resultats if r.moy_d is not None]
        
        # Calculer les statistiques
        stats = {
            'nb_eleves': total_eleves,
            'moyenne_discipline': round(sum(moyennes) / len(moyennes), 2) if moyennes else 0,
            'nb_moyenne': q.filter(NoteS1.moy_d >= 10).count(),
            'taux_reussite': round((q.filter(NoteS1.moy_d >= 10).count() / total_eleves * 100) if total_eleves > 0 else 0),
            'min': round(min(moyennes), 2) if moyennes else 0,
            'max': round(max(moyennes), 2) if moyennes else 0
        }
    
    return jsonify(stats)

@semestre1_bp.route('/api/report/discipline', methods=['POST'])
def api_generate_discipline_report():
    """
    API pour générer un rapport de discipline.
    Paramètres:
    - discipline_id: ID de la discipline
    - niveau_id: (optionnel) ID du niveau
    - classe_id: (optionnel) ID de la classe
    """
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    
    if not discipline_id:
        return jsonify({'error': 'discipline_id est obligatoire'}), 400
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Construire la requête de base pour les notes
    query = db.session.query(NoteS1, Eleve).\
        join(Eleve, NoteS1.eleve_ien == Eleve.ien).\
        join(Classe, Eleve.classe_id == Classe.id).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active)
    
    # Appliquer les filtres
    if niveau_id:
        query = query.join(Classe, Eleve.classe_id == Classe.id).\
                filter(Classe.niveau_id == niveau_id)
    if classe_id:
        query = query.filter(Eleve.classe_id == classe_id)
    
    # Récupérer les données
    notes_eleves = query.all()
    
    if not notes_eleves:
        return jsonify({'error': 'Aucune donnée trouvée pour ces critères'}), 404
    
    # Calculer les statistiques globales
    notes = [n.moy_d for n, _ in notes_eleves if n.moy_d is not None]
    total_eleves = len(notes)
    
    if total_eleves == 0:
        return jsonify({'error': 'Aucune note valide trouvée pour ces critères'}), 404
    
    # Statistiques générales
    moyenne = sum(notes) / total_eleves
    min_note = min(notes)
    max_note = max(notes)
    
    # Utiliser pandas pour calculer la médiane et l'écart-type
    notes_series = pd.Series(notes)
    mediane = float(notes_series.median())
    ecart_type = float(notes_series.std())
    
    # Statistiques par sexe
    notes_garcons = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe in ('M', 'H')]
    notes_filles = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe == 'F']
    
    total_garcons = len(notes_garcons)
    total_filles = len(notes_filles)
    
    moyenne_garcons = sum(notes_garcons) / total_garcons if total_garcons > 0 else 0
    moyenne_filles = sum(notes_filles) / total_filles if total_filles > 0 else 0
    
    reussite_garcons = sum(1 for n in notes_garcons if n >= 10)
    reussite_filles = sum(1 for n in notes_filles if n >= 10)
    
    taux_reussite_global = sum(1 for n in notes if n >= 10) / total_eleves * 100
    taux_reussite_garcons = reussite_garcons / total_garcons * 100 if total_garcons > 0 else 0
    taux_reussite_filles = reussite_filles / total_filles * 100 if total_filles > 0 else 0
    
    pct_garcons = (total_garcons / total_eleves * 100) if total_eleves > 0 else 0
    pct_filles = (total_filles / total_eleves * 100) if total_eleves > 0 else 0
    
    # Répartition par tranches de notes
    tranches = {
        'tres_bien': sum(1 for n in notes if n >= 16),
        'bien': sum(1 for n in notes if 14 <= n < 16),
        'assez_bien': sum(1 for n in notes if 12 <= n < 14),
        'passable': sum(1 for n in notes if 10 <= n < 12),
        'insuffisant': sum(1 for n in notes if n < 10)
    }
    
    # Récupérer la configuration de l'application
    config = Configuration.query.first()
    
    # Récupérer le niveau et la classe si spécifiés
    niveau = Niveau.query.get(niveau_id) if niveau_id else None
    classe = Classe.query.get(classe_id) if classe_id else None
    
    # Calculer la moyenne générale de l'établissement pour comparaison
    all_moyennes = db.session.query(NoteS1.moy_d).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active,
               NoteS1.moy_d.isnot(None)).all()
    
    all_moyenne = sum([m.moy_d for m in all_moyennes]) / len(all_moyennes) if all_moyennes else 0
    difference_moyenne = moyenne - all_moyenne
    
    # Préparer les données de retour
    report_data = {
        'stats': {
            'total_eleves': total_eleves,
            'moyenne_generale': round(moyenne, 2),
            'eleves_moyenne': sum(1 for n in notes if n >= 10),
            'taux_reussite': round(taux_reussite_global, 2),
            'min': round(min_note, 2),
            'max': round(max_note, 2),
            'mediane': round(mediane, 2),
            'ecart_type': round(ecart_type, 2),
            'total_garcons': total_garcons,
            'total_filles': total_filles,
            'pct_garcons': round(pct_garcons, 2),
            'pct_filles': round(pct_filles, 2),
            'moyenne_garcons': round(moyenne_garcons, 2),
            'moyenne_filles': round(moyenne_filles, 2),
            'reussite_garcons': reussite_garcons,
            'reussite_filles': reussite_filles,
            'taux_reussite_garcons': round(taux_reussite_garcons, 2),
            'taux_reussite_filles': round(taux_reussite_filles, 2),
            'tranches': tranches,
            'moyenne_generale_etablissement': round(all_moyenne, 2),
            'difference_moyenne': round(difference_moyenne, 2)
        },
        'config': {
            'nom_etablissement': config.nom_etablissement if config else 'Établissement'
        },
        'filter': {
            'discipline': discipline.libelle,
            'niveau': niveau.libelle if niveau else None,
            'classe': classe.libelle if classe else None
        },
        'annee_scolaire': annee_active
    }
    
    # Enregistrer le rapport pour référence ultérieure
    import json
    import datetime
    
    now = datetime.datetime.now()
    rapport = Rapport(
        type='discipline',
        date_creation=now,
        contenu=json.dumps(report_data),
        discipline_id=discipline_id,
        niveau_id=niveau_id,
        classe_id=classe_id,
        annee_scolaire=annee_active
    )
    db.session.add(rapport)
    db.session.commit()
    
    # Ajouter l'ID du rapport aux données de retour
    report_data['rapport_id'] = rapport.id
    
    return jsonify(report_data)

@semestre1_bp.route('/api/disciplines')
def api_get_disciplines():
    """API pour récupérer toutes les disciplines"""
    disciplines = Discipline.query.order_by(Discipline.libelle).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/<int:classe_id>')
def api_get_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines d'une classe spécifique"""
    # Récupérer la classe pour déterminer le niveau
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à cette classe via l'année en cours
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).filter(
        Eleve.classe_id == classe_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>')
def api_get_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines d'un niveau spécifique"""
    # Récupérer l'année active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes pour ce niveau
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).filter(
        Classe.niveau_id == niveau_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])

@semestre1_bp.route('/api/discipline_report')
def api_discipline_report_analysis():
    """API pour générer un rapport d'analyse par discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id', type=int)
    classe_id = request.args.get('classe_id', type=int)
    niveau_id = request.args.get('niveau_id', type=int)
    
    if not discipline_id:
        return jsonify({'error': 'Discipline non spécifiée'}), 400
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Construire la requête de base
    query = db.session.query(
        NoteS1.valeur.label('note'),
        Eleve.sexe,
        Classe.id.label('classe_id'),
        Classe.libelle.label('classe_libelle'),
        Niveau.id.label('niveau_id'),
        Niveau.libelle.label('niveau_libelle')
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).join(
        Niveau, Classe.niveau_id == Niveau.id
    ).filter(
        NoteS1.discipline_id == discipline_id,
        NoteS1.annee_scolaire == annee_active
    )
    
    # Filtrer par classe si spécifié
    if classe_id:
        query = query.filter(Classe.id == classe_id)
    
    # Filtrer par niveau si spécifié
    if niveau_id:
        query = query.filter(Niveau.id == niveau_id)
    
    # Exécuter la requête
    results = query.all()
    
    if not results:
        return jsonify({
            'discipline_id': discipline_id,
            'discipline_name': discipline.libelle,
            'niveau_id': niveau_id,
            'classe_id': classe_id,
            'results': [],
            'general_stats': {
                'average': 0,
                'highest': 0,
                'lowest': 0,
                'total_students': 0
            },
            'distribution': [0, 0, 0, 0, 0, 0, 0]  # Distribution vide
        })
    
    # Calculer les statistiques générales
    all_notes = [r.note for r in results]
    average = sum(all_notes) / len(all_notes)
    highest = max(all_notes)
    lowest = min(all_notes)
    total_students = len(all_notes)
    
    # Calculer la distribution des notes
    distribution = [0] * 7  # [0-5, 5-10, 10-12, 12-14, 14-16, 16-18, 18-20]
    for note in all_notes:
        if note < 5:
            distribution[0] += 1
        elif note < 10:
            distribution[1] += 1
        elif note < 12:
            distribution[2] += 1
        elif note < 14:
            distribution[3] += 1
        elif note < 16:
            distribution[4] += 1
        elif note < 18:
            distribution[5] += 1
        else:
            distribution[6] += 1
    
    # Regrouper les résultats par classe
    class_results = {}
    for r in results:
        class_id = r.classe_id
        if class_id not in class_results:
            class_results[class_id] = {
                'classe_id': class_id,
                'classe_name': r.classe_libelle,
                'notes': []
            }
        class_results[class_id]['notes'].append(r.note)
    
    # Calculer les statistiques par classe
    class_stats = []
    for class_id, data in class_results.items():
        notes = data['notes']
        class_stats.append({
            'classe_id': data['classe_id'],
            'classe_name': data['classe_name'],
            'average': sum(notes) / len(notes),
            'highest': max(notes),
            'lowest': min(notes),
            'student_count': len(notes)
        })
    
    # Trier les résultats par moyenne décroissante
    class_stats.sort(key=lambda x: x['average'], reverse=True)
    
    # Construire la réponse
    response = {
        'discipline_id': discipline_id,
        'discipline_name': discipline.libelle,
        'niveau_id': niveau_id,
        'classe_id': classe_id,
        'results': class_stats,
        'general_stats': {
            'average': average,
            'highest': highest,
            'lowest': lowest,
            'total_students': total_students
        },
        'distribution': distribution
    }
    
    return jsonify(response)

@semestre1_bp.route('/api/disciplines_by_niveau/<int:niveau_id>')
def api_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines par niveau"""
    disciplines = Discipline.query.filter_by(niveau_id=niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/api/disciplines_by_classe/<int:classe_id>')
def api_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines par classe"""
    # Récupérer le niveau associé à la classe
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à ce niveau
    disciplines = Discipline.query.filter_by(niveau_id=classe.niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/discipline_analysis')
@login_required
def discipline_analysis_admin():
    """Page for analyzing discipline statistics"""
    # Get all niveaux for filtering
    niveaux = Niveau.query.all()
    
    # Get all disciplines initially (will be filtered by JS)
    disciplines = Discipline.query.all()
    
    # Get current date for reporting
    current_date = datetime.datetime.now().strftime("%d/%m/%Y")
    
    return render_template(
        'semestre1/discipline_analysis.html',
        title='Analyse par Discipline',
        niveaux=niveaux,
        disciplines=disciplines,
        current_date=current_date
    )

@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>', methods=['GET'])
def get_disciplines_by_niveau_v2(niveau_id):
    """API route to get disciplines by niveau"""
    try:
        # Get all disciplines for classes in this niveau
        classes = Classe.query.filter_by(niveau_id=niveau_id).all()
        classe_ids = [c.id for c in classes]
        
        # Find disciplines associated with these classes
        disciplines = Discipline.query.filter(Discipline.classe_id.in_(classe_ids)).all()
        
        disciplines_data = [{'id': d.id, 'libelle': d.libelle} for d in disciplines]
        return jsonify({'status': 'success', 'disciplines': disciplines_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@semestre1_bp.route('/api/stats/discipline')
def discipline_stats():
    """API pour récupérer les statistiques d'une discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    sexe = request.args.get('sexe')
    note_min = request.args.get('note_min', '0')
    note_max = request.args.get('note_max', '20')
    
    # Convertir en float pour les comparaisons
    try:
        note_min = float(note_min)
        note_max = float(note_max)
    except (ValueError, TypeError):
        note_min = 0
        note_max = 20
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Vérifier si la discipline est spécifiée
    if not discipline_id:
        return jsonify({'error': 'Une discipline doit être spécifiée'}), 400
    
    # Construire la requête de base
    q = db.session.query(NoteS1).join(Eleve, NoteS1.eleve_ien == Eleve.ien)
    q = q.join(Classe, Eleve.classe_id == Classe.id)
    q = q.join(Niveau, Classe.niveau_id == Niveau.id)
    
    # Appliquer les filtres
    q = q.filter(NoteS1.annee_scolaire == annee_active)
    q = q.filter(NoteS1.discipline_id == discipline_id)
    
    if niveau_id:
        q = q.filter(Niveau.id == niveau_id)
    
    if classe_id:
        q = q.filter(Classe.id == classe_id)
    
    if sexe:
        if sexe == 'M':
            q = q.filter(Eleve.sexe.in_(['M', 'H']))
        else:
            q = q.filter(Eleve.sexe == 'F')
    
    q = q.filter(NoteS1.moy_d >= note_min, NoteS1.moy_d <= note_max)
    
    # Récupérer les données
    resultats = q.all()
    
    # Statistiques globales
    total_eleves = len(resultats)
    
    # Initialiser les statistiques
    stats = {
        'nb_eleves': 0,
        'moyenne_discipline': 0,
        'nb_moyenne': 0,
        'taux_reussite': 0,
        'min': 0,
        'max': 0
    }
    
    if total_eleves > 0:
        # Extraire les moyennes valides
        moyennes = [r.moy_d for r in resultats if r.moy_d is not None]
        
        # Calculer les statistiques
        stats = {
            'nb_eleves': total_eleves,
            'moyenne_discipline': round(sum(moyennes) / len(moyennes), 2) if moyennes else 0,
            'nb_moyenne': q.filter(NoteS1.moy_d >= 10).count(),
            'taux_reussite': round((q.filter(NoteS1.moy_d >= 10).count() / total_eleves * 100) if total_eleves > 0 else 0),
            'min': round(min(moyennes), 2) if moyennes else 0,
            'max': round(max(moyennes), 2) if moyennes else 0
        }
    
    return jsonify(stats)

@semestre1_bp.route('/api/report/discipline', methods=['POST'])
def api_generate_discipline_report():
    """
    API pour générer un rapport de discipline.
    Paramètres:
    - discipline_id: ID de la discipline
    - niveau_id: (optionnel) ID du niveau
    - classe_id: (optionnel) ID de la classe
    """
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    
    if not discipline_id:
        return jsonify({'error': 'discipline_id est obligatoire'}), 400
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Construire la requête de base pour les notes
    query = db.session.query(NoteS1, Eleve).\
        join(Eleve, NoteS1.eleve_ien == Eleve.ien).\
        join(Classe, Eleve.classe_id == Classe.id).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active)
    
    # Appliquer les filtres
    if niveau_id:
        query = query.join(Classe, Eleve.classe_id == Classe.id).\
                filter(Classe.niveau_id == niveau_id)
    if classe_id:
        query = query.filter(Eleve.classe_id == classe_id)
    
    # Récupérer les données
    notes_eleves = query.all()
    
    if not notes_eleves:
        return jsonify({'error': 'Aucune donnée trouvée pour ces critères'}), 404
    
    # Calculer les statistiques globales
    notes = [n.moy_d for n, _ in notes_eleves if n.moy_d is not None]
    total_eleves = len(notes)
    
    if total_eleves == 0:
        return jsonify({'error': 'Aucune note valide trouvée pour ces critères'}), 404
    
    # Statistiques générales
    moyenne = sum(notes) / total_eleves
    min_note = min(notes)
    max_note = max(notes)
    
    # Utiliser pandas pour calculer la médiane et l'écart-type
    notes_series = pd.Series(notes)
    mediane = float(notes_series.median())
    ecart_type = float(notes_series.std())
    
    # Statistiques par sexe
    notes_garcons = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe in ('M', 'H')]
    notes_filles = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe == 'F']
    
    total_garcons = len(notes_garcons)
    total_filles = len(notes_filles)
    
    moyenne_garcons = sum(notes_garcons) / total_garcons if total_garcons > 0 else 0
    moyenne_filles = sum(notes_filles) / total_filles if total_filles > 0 else 0
    
    reussite_garcons = sum(1 for n in notes_garcons if n >= 10)
    reussite_filles = sum(1 for n in notes_filles if n >= 10)
    
    taux_reussite_global = sum(1 for n in notes if n >= 10) / total_eleves * 100
    taux_reussite_garcons = reussite_garcons / total_garcons * 100 if total_garcons > 0 else 0
    taux_reussite_filles = reussite_filles / total_filles * 100 if total_filles > 0 else 0
    
    pct_garcons = (total_garcons / total_eleves * 100) if total_eleves > 0 else 0
    pct_filles = (total_filles / total_eleves * 100) if total_eleves > 0 else 0
    
    # Répartition par tranches de notes
    tranches = {
        'tres_bien': sum(1 for n in notes if n >= 16),
        'bien': sum(1 for n in notes if 14 <= n < 16),
        'assez_bien': sum(1 for n in notes if 12 <= n < 14),
        'passable': sum(1 for n in notes if 10 <= n < 12),
        'insuffisant': sum(1 for n in notes if n < 10)
    }
    
    # Récupérer la configuration de l'application
    config = Configuration.query.first()
    
    # Récupérer le niveau et la classe si spécifiés
    niveau = Niveau.query.get(niveau_id) if niveau_id else None
    classe = Classe.query.get(classe_id) if classe_id else None
    
    # Calculer la moyenne générale de l'établissement pour comparaison
    all_moyennes = db.session.query(NoteS1.moy_d).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active,
               NoteS1.moy_d.isnot(None)).all()
    
    all_moyenne = sum([m.moy_d for m in all_moyennes]) / len(all_moyennes) if all_moyennes else 0
    difference_moyenne = moyenne - all_moyenne
    
    # Préparer les données de retour
    report_data = {
        'stats': {
            'total_eleves': total_eleves,
            'moyenne_generale': round(moyenne, 2),
            'eleves_moyenne': sum(1 for n in notes if n >= 10),
            'taux_reussite': round(taux_reussite_global, 2),
            'min': round(min_note, 2),
            'max': round(max_note, 2),
            'mediane': round(mediane, 2),
            'ecart_type': round(ecart_type, 2),
            'total_garcons': total_garcons,
            'total_filles': total_filles,
            'pct_garcons': round(pct_garcons, 2),
            'pct_filles': round(pct_filles, 2),
            'moyenne_garcons': round(moyenne_garcons, 2),
            'moyenne_filles': round(moyenne_filles, 2),
            'reussite_garcons': reussite_garcons,
            'reussite_filles': reussite_filles,
            'taux_reussite_garcons': round(taux_reussite_garcons, 2),
            'taux_reussite_filles': round(taux_reussite_filles, 2),
            'tranches': tranches,
            'moyenne_generale_etablissement': round(all_moyenne, 2),
            'difference_moyenne': round(difference_moyenne, 2)
        },
        'config': {
            'nom_etablissement': config.nom_etablissement if config else 'Établissement'
        },
        'filter': {
            'discipline': discipline.libelle,
            'niveau': niveau.libelle if niveau else None,
            'classe': classe.libelle if classe else None
        },
        'annee_scolaire': annee_active
    }
    
    # Enregistrer le rapport pour référence ultérieure
    import json
    import datetime
    
    now = datetime.datetime.now()
    rapport = Rapport(
        type='discipline',
        date_creation=now,
        contenu=json.dumps(report_data),
        discipline_id=discipline_id,
        niveau_id=niveau_id,
        classe_id=classe_id,
        annee_scolaire=annee_active
    )
    db.session.add(rapport)
    db.session.commit()
    
    # Ajouter l'ID du rapport aux données de retour
    report_data['rapport_id'] = rapport.id
    
    return jsonify(report_data)

@semestre1_bp.route('/api/disciplines')
def api_get_disciplines():
    """API pour récupérer toutes les disciplines"""
    disciplines = Discipline.query.order_by(Discipline.libelle).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/<int:classe_id>')
def api_get_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines d'une classe spécifique"""
    # Récupérer la classe pour déterminer le niveau
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à cette classe via l'année en cours
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).filter(
        Eleve.classe_id == classe_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>')
def api_get_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines d'un niveau spécifique"""
    # Récupérer l'année active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes pour ce niveau
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).filter(
        Classe.niveau_id == niveau_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])

@semestre1_bp.route('/api/discipline_report')
def api_discipline_report_analysis():
    """API pour générer un rapport d'analyse par discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id', type=int)
    classe_id = request.args.get('classe_id', type=int)
    niveau_id = request.args.get('niveau_id', type=int)
    
    if not discipline_id:
        return jsonify({'error': 'Discipline non spécifiée'}), 400
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Construire la requête de base
    query = db.session.query(
        NoteS1.valeur.label('note'),
        Eleve.sexe,
        Classe.id.label('classe_id'),
        Classe.libelle.label('classe_libelle'),
        Niveau.id.label('niveau_id'),
        Niveau.libelle.label('niveau_libelle')
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).join(
        Niveau, Classe.niveau_id == Niveau.id
    ).filter(
        NoteS1.discipline_id == discipline_id,
        NoteS1.annee_scolaire == annee_active
    )
    
    # Filtrer par classe si spécifié
    if classe_id:
        query = query.filter(Classe.id == classe_id)
    
    # Filtrer par niveau si spécifié
    if niveau_id:
        query = query.filter(Niveau.id == niveau_id)
    
    # Exécuter la requête
    results = query.all()
    
    if not results:
        return jsonify({
            'discipline_id': discipline_id,
            'discipline_name': discipline.libelle,
            'niveau_id': niveau_id,
            'classe_id': classe_id,
            'results': [],
            'general_stats': {
                'average': 0,
                'highest': 0,
                'lowest': 0,
                'total_students': 0
            },
            'distribution': [0, 0, 0, 0, 0, 0, 0]  # Distribution vide
        })
    
    # Calculer les statistiques générales
    all_notes = [r.note for r in results]
    average = sum(all_notes) / len(all_notes)
    highest = max(all_notes)
    lowest = min(all_notes)
    total_students = len(all_notes)
    
    # Calculer la distribution des notes
    distribution = [0] * 7  # [0-5, 5-10, 10-12, 12-14, 14-16, 16-18, 18-20]
    for note in all_notes:
        if note < 5:
            distribution[0] += 1
        elif note < 10:
            distribution[1] += 1
        elif note < 12:
            distribution[2] += 1
        elif note < 14:
            distribution[3] += 1
        elif note < 16:
            distribution[4] += 1
        elif note < 18:
            distribution[5] += 1
        else:
            distribution[6] += 1
    
    # Regrouper les résultats par classe
    class_results = {}
    for r in results:
        class_id = r.classe_id
        if class_id not in class_results:
            class_results[class_id] = {
                'classe_id': class_id,
                'classe_name': r.classe_libelle,
                'notes': []
            }
        class_results[class_id]['notes'].append(r.note)
    
    # Calculer les statistiques par classe
    class_stats = []
    for class_id, data in class_results.items():
        notes = data['notes']
        class_stats.append({
            'classe_id': data['classe_id'],
            'classe_name': data['classe_name'],
            'average': sum(notes) / len(notes),
            'highest': max(notes),
            'lowest': min(notes),
            'student_count': len(notes)
        })
    
    # Trier les résultats par moyenne décroissante
    class_stats.sort(key=lambda x: x['average'], reverse=True)
    
    # Construire la réponse
    response = {
        'discipline_id': discipline_id,
        'discipline_name': discipline.libelle,
        'niveau_id': niveau_id,
        'classe_id': classe_id,
        'results': class_stats,
        'general_stats': {
            'average': average,
            'highest': highest,
            'lowest': lowest,
            'total_students': total_students
        },
        'distribution': distribution
    }
    
    return jsonify(response)

@semestre1_bp.route('/api/disciplines_by_niveau/<int:niveau_id>')
def api_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines par niveau"""
    disciplines = Discipline.query.filter_by(niveau_id=niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/api/disciplines_by_classe/<int:classe_id>')
def api_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines par classe"""
    # Récupérer le niveau associé à la classe
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à ce niveau
    disciplines = Discipline.query.filter_by(niveau_id=classe.niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/discipline_analysis')
@login_required
def discipline_analysis_admin():
    """Page for analyzing discipline statistics"""
    # Get all niveaux for filtering
    niveaux = Niveau.query.all()
    
    # Get all disciplines initially (will be filtered by JS)
    disciplines = Discipline.query.all()
    
    # Get current date for reporting
    current_date = datetime.datetime.now().strftime("%d/%m/%Y")
    
    return render_template(
        'semestre1/discipline_analysis.html',
        title='Analyse par Discipline',
        niveaux=niveaux,
        disciplines=disciplines,
        current_date=current_date
    )

@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>', methods=['GET'])
def get_disciplines_by_niveau_v2(niveau_id):
    """API route to get disciplines by niveau"""
    try:
        # Get all disciplines for classes in this niveau
        classes = Classe.query.filter_by(niveau_id=niveau_id).all()
        classe_ids = [c.id for c in classes]
        
        # Find disciplines associated with these classes
        disciplines = Discipline.query.filter(Discipline.classe_id.in_(classe_ids)).all()
        
        disciplines_data = [{'id': d.id, 'libelle': d.libelle} for d in disciplines]
        return jsonify({'status': 'success', 'disciplines': disciplines_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@semestre1_bp.route('/api/stats/discipline')
def discipline_stats():
    """API pour récupérer les statistiques d'une discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    sexe = request.args.get('sexe')
    note_min = request.args.get('note_min', '0')
    note_max = request.args.get('note_max', '20')
    
    # Convertir en float pour les comparaisons
    try:
        note_min = float(note_min)
        note_max = float(note_max)
    except (ValueError, TypeError):
        note_min = 0
        note_max = 20
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Vérifier si la discipline est spécifiée
    if not discipline_id:
        return jsonify({'error': 'Une discipline doit être spécifiée'}), 400
    
    # Construire la requête de base
    q = db.session.query(NoteS1).join(Eleve, NoteS1.eleve_ien == Eleve.ien)
    q = q.join(Classe, Eleve.classe_id == Classe.id)
    q = q.join(Niveau, Classe.niveau_id == Niveau.id)
    
    # Appliquer les filtres
    q = q.filter(NoteS1.annee_scolaire == annee_active)
    q = q.filter(NoteS1.discipline_id == discipline_id)
    
    if niveau_id:
        q = q.filter(Niveau.id == niveau_id)
    
    if classe_id:
        q = q.filter(Classe.id == classe_id)
    
    if sexe:
        if sexe == 'M':
            q = q.filter(Eleve.sexe.in_(['M', 'H']))
        else:
            q = q.filter(Eleve.sexe == 'F')
    
    q = q.filter(NoteS1.moy_d >= note_min, NoteS1.moy_d <= note_max)
    
    # Récupérer les données
    resultats = q.all()
    
    # Statistiques globales
    total_eleves = len(resultats)
    
    # Initialiser les statistiques
    stats = {
        'nb_eleves': 0,
        'moyenne_discipline': 0,
        'nb_moyenne': 0,
        'taux_reussite': 0,
        'min': 0,
        'max': 0
    }
    
    if total_eleves > 0:
        # Extraire les moyennes valides
        moyennes = [r.moy_d for r in resultats if r.moy_d is not None]
        
        # Calculer les statistiques
        stats = {
            'nb_eleves': total_eleves,
            'moyenne_discipline': round(sum(moyennes) / len(moyennes), 2) if moyennes else 0,
            'nb_moyenne': q.filter(NoteS1.moy_d >= 10).count(),
            'taux_reussite': round((q.filter(NoteS1.moy_d >= 10).count() / total_eleves * 100) if total_eleves > 0 else 0),
            'min': round(min(moyennes), 2) if moyennes else 0,
            'max': round(max(moyennes), 2) if moyennes else 0
        }
    
    return jsonify(stats)
@semestre1_bp.route('/api/report/discipline', methods=['POST'])
def api_generate_discipline_report():
    """
    API pour générer un rapport de discipline.
    Paramètres:
    - discipline_id: ID de la discipline
    - niveau_id: (optionnel) ID du niveau
    - classe_id: (optionnel) ID de la classe
    """
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    
    if not discipline_id:
        return jsonify({'error': 'discipline_id est obligatoire'}), 400
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Construire la requête de base pour les notes
    query = db.session.query(NoteS1, Eleve).\
        join(Eleve, NoteS1.eleve_ien == Eleve.ien).\
        join(Classe, Eleve.classe_id == Classe.id).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active)
    
    # Appliquer les filtres
    if niveau_id:
        query = query.join(Classe, Eleve.classe_id == Classe.id).\
                filter(Classe.niveau_id == niveau_id)
    if classe_id:
        query = query.filter(Eleve.classe_id == classe_id)
    
    # Récupérer les données
    notes_eleves = query.all()
    
    if not notes_eleves:
        return jsonify({'error': 'Aucune donnée trouvée pour ces critères'}), 404
    
    # Calculer les statistiques globales
    notes = [n.moy_d for n, _ in notes_eleves if n.moy_d is not None]
    total_eleves = len(notes)
    
    if total_eleves == 0:
        return jsonify({'error': 'Aucune note valide trouvée pour ces critères'}), 404
    
    # Statistiques générales
    moyenne = sum(notes) / total_eleves
    min_note = min(notes)
    max_note = max(notes)
    
    # Utiliser pandas pour calculer la médiane et l'écart-type
    notes_series = pd.Series(notes)
    mediane = float(notes_series.median())
    ecart_type = float(notes_series.std())
    
    # Statistiques par sexe
    notes_garcons = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe in ('M', 'H')]
    notes_filles = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe == 'F']
    
    total_garcons = len(notes_garcons)
    total_filles = len(notes_filles)
    
    moyenne_garcons = sum(notes_garcons) / total_garcons if total_garcons > 0 else 0
    moyenne_filles = sum(notes_filles) / total_filles if total_filles > 0 else 0
    
    reussite_garcons = sum(1 for n in notes_garcons if n >= 10)
    reussite_filles = sum(1 for n in notes_filles if n >= 10)
    
    taux_reussite_global = sum(1 for n in notes if n >= 10) / total_eleves * 100
    taux_reussite_garcons = reussite_garcons / total_garcons * 100 if total_garcons > 0 else 0
    taux_reussite_filles = reussite_filles / total_filles * 100 if total_filles > 0 else 0
    
    pct_garcons = (total_garcons / total_eleves * 100) if total_eleves > 0 else 0
    pct_filles = (total_filles / total_eleves * 100) if total_eleves > 0 else 0
    
    # Répartition par tranches de notes
    tranches = {
        'tres_bien': sum(1 for n in notes if n >= 16),
        'bien': sum(1 for n in notes if 14 <= n < 16),
        'assez_bien': sum(1 for n in notes if 12 <= n < 14),
        'passable': sum(1 for n in notes if 10 <= n < 12),
        'insuffisant': sum(1 for n in notes if n < 10)
    }
    
    # Récupérer la configuration de l'application
    config = Configuration.query.first()
    
    # Récupérer le niveau et la classe si spécifiés
    niveau = Niveau.query.get(niveau_id) if niveau_id else None
    classe = Classe.query.get(classe_id) if classe_id else None
    
    # Calculer la moyenne générale de l'établissement pour comparaison
    all_moyennes = db.session.query(NoteS1.moy_d).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active,
               NoteS1.moy_d.isnot(None)).all()
    
    all_moyenne = sum([m.moy_d for m in all_moyennes]) / len(all_moyennes) if all_moyennes else 0
    difference_moyenne = moyenne - all_moyenne
    
    # Préparer les données de retour
    report_data = {
        'stats': {
            'total_eleves': total_eleves,
            'moyenne_generale': round(moyenne, 2),
            'eleves_moyenne': sum(1 for n in notes if n >= 10),
            'taux_reussite': round(taux_reussite_global, 2),
            'min': round(min_note, 2),
            'max': round(max_note, 2),
            'mediane': round(mediane, 2),
            'ecart_type': round(ecart_type, 2),
            'total_garcons': total_garcons,
            'total_filles': total_filles,
            'pct_garcons': round(pct_garcons, 2),
            'pct_filles': round(pct_filles, 2),
            'moyenne_garcons': round(moyenne_garcons, 2),
            'moyenne_filles': round(moyenne_filles, 2),
            'reussite_garcons': reussite_garcons,
            'reussite_filles': reussite_filles,
            'taux_reussite_garcons': round(taux_reussite_garcons, 2),
            'taux_reussite_filles': round(taux_reussite_filles, 2),
            'tranches': tranches,
            'moyenne_generale_etablissement': round(all_moyenne, 2),
            'difference_moyenne': round(difference_moyenne, 2)
        },
        'config': {
            'nom_etablissement': config.nom_etablissement if config else 'Établissement'
        },
        'filter': {
            'discipline': discipline.libelle,
            'niveau': niveau.libelle if niveau else None,
            'classe': classe.libelle if classe else None
        },
        'annee_scolaire': annee_active
    }
    
    # Enregistrer le rapport pour référence ultérieure
    import json
    import datetime
    
    now = datetime.datetime.now()
    rapport = Rapport(
        type='discipline',
        date_creation=now,
        contenu=json.dumps(report_data),
        discipline_id=discipline_id,
        niveau_id=niveau_id,
        classe_id=classe_id,
        annee_scolaire=annee_active
    )
    db.session.add(rapport)
    db.session.commit()
    
    # Ajouter l'ID du rapport aux données de retour
    report_data['rapport_id'] = rapport.id
    
    return jsonify(report_data)

@semestre1_bp.route('/api/disciplines')
def api_get_disciplines():
    """API pour récupérer toutes les disciplines"""
    disciplines = Discipline.query.order_by(Discipline.libelle).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/<int:classe_id>')
def api_get_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines d'une classe spécifique"""
    # Récupérer la classe pour déterminer le niveau
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à cette classe via l'année en cours
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).filter(
        Eleve.classe_id == classe_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>')
def api_get_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines d'un niveau spécifique"""
    # Récupérer l'année active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes pour ce niveau
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).filter(
        Classe.niveau_id == niveau_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])

@semestre1_bp.route('/api/discipline_report')
def api_discipline_report_analysis():
    """API pour générer un rapport d'analyse par discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id', type=int)
    classe_id = request.args.get('classe_id', type=int)
    niveau_id = request.args.get('niveau_id', type=int)
    
    if not discipline_id:
        return jsonify({'error': 'Discipline non spécifiée'}), 400
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Construire la requête de base
    query = db.session.query(
        NoteS1.valeur.label('note'),
        Eleve.sexe,
        Classe.id.label('classe_id'),
        Classe.libelle.label('classe_libelle'),
        Niveau.id.label('niveau_id'),
        Niveau.libelle.label('niveau_libelle')
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).join(
        Niveau, Classe.niveau_id == Niveau.id
    ).filter(
        NoteS1.discipline_id == discipline_id,
        NoteS1.annee_scolaire == annee_active
    )
    
    # Filtrer par classe si spécifié
    if classe_id:
        query = query.filter(Classe.id == classe_id)
    
    # Filtrer par niveau si spécifié
    if niveau_id:
        query = query.filter(Niveau.id == niveau_id)
    
    # Exécuter la requête
    results = query.all()
    
    if not results:
        return jsonify({
            'discipline_id': discipline_id,
            'discipline_name': discipline.libelle,
            'niveau_id': niveau_id,
            'classe_id': classe_id,
            'results': [],
            'general_stats': {
                'average': 0,
                'highest': 0,
                'lowest': 0,
                'total_students': 0
            },
            'distribution': [0, 0, 0, 0, 0, 0, 0]  # Distribution vide
        })
    
    # Calculer les statistiques générales
    all_notes = [r.note for r in results]
    average = sum(all_notes) / len(all_notes)
    highest = max(all_notes)
    lowest = min(all_notes)
    total_students = len(all_notes)
    
    # Calculer la distribution des notes
    distribution = [0] * 7  # [0-5, 5-10, 10-12, 12-14, 14-16, 16-18, 18-20]
    for note in all_notes:
        if note < 5:
            distribution[0] += 1
        elif note < 10:
            distribution[1] += 1
        elif note < 12:
            distribution[2] += 1
        elif note < 14:
            distribution[3] += 1
        elif note < 16:
            distribution[4] += 1
        elif note < 18:
            distribution[5] += 1
        else:
            distribution[6] += 1
    
    # Regrouper les résultats par classe
    class_results = {}
    for r in results:
        class_id = r.classe_id
        if class_id not in class_results:
            class_results[class_id] = {
                'classe_id': class_id,
                'classe_name': r.classe_libelle,
                'notes': []
            }
        class_results[class_id]['notes'].append(r.note)
    
    # Calculer les statistiques par classe
    class_stats = []
    for class_id, data in class_results.items():
        notes = data['notes']
        class_stats.append({
            'classe_id': data['classe_id'],
            'classe_name': data['classe_name'],
            'average': sum(notes) / len(notes),
            'highest': max(notes),
            'lowest': min(notes),
            'student_count': len(notes)
        })
    
    # Trier les résultats par moyenne décroissante
    class_stats.sort(key=lambda x: x['average'], reverse=True)
    
    # Construire la réponse
    response = {
        'discipline_id': discipline_id,
        'discipline_name': discipline.libelle,
        'niveau_id': niveau_id,
        'classe_id': classe_id,
        'results': class_stats,
        'general_stats': {
            'average': average,
            'highest': highest,
            'lowest': lowest,
            'total_students': total_students
        },
        'distribution': distribution
    }
    
    return jsonify(response)

@semestre1_bp.route('/api/disciplines_by_niveau/<int:niveau_id>')
def api_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines par niveau"""
    disciplines = Discipline.query.filter_by(niveau_id=niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/api/disciplines_by_classe/<int:classe_id>')
def api_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines par classe"""
    # Récupérer le niveau associé à la classe
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à ce niveau
    disciplines = Discipline.query.filter_by(niveau_id=classe.niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/discipline_analysis')
@login_required
def discipline_analysis_admin():
    """Page for analyzing discipline statistics"""
    # Get all niveaux for filtering
    niveaux = Niveau.query.all()
    
    # Get all disciplines initially (will be filtered by JS)
    disciplines = Discipline.query.all()
    
    # Get current date for reporting
    current_date = datetime.datetime.now().strftime("%d/%m/%Y")
    
    return render_template(
        'semestre1/discipline_analysis.html',
        title='Analyse par Discipline',
        niveaux=niveaux,
        disciplines=disciplines,
        current_date=current_date
    )

@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>', methods=['GET'])
def get_disciplines_by_niveau_v2(niveau_id):
    """API route to get disciplines by niveau"""
    try:
        # Get all disciplines for classes in this niveau
        classes = Classe.query.filter_by(niveau_id=niveau_id).all()
        classe_ids = [c.id for c in classes]
        
        # Find disciplines associated with these classes
        disciplines = Discipline.query.filter(Discipline.classe_id.in_(classe_ids)).all()
        
        disciplines_data = [{'id': d.id, 'libelle': d.libelle} for d in disciplines]
        return jsonify({'status': 'success', 'disciplines': disciplines_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@semestre1_bp.route('/api/stats/discipline')
def discipline_stats():
    """API pour récupérer les statistiques d'une discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    sexe = request.args.get('sexe')
    note_min = request.args.get('note_min', '0')
    note_max = request.args.get('note_max', '20')
    
    # Convertir en float pour les comparaisons
    try:
        note_min = float(note_min)
        note_max = float(note_max)
    except (ValueError, TypeError):
        note_min = 0
        note_max = 20
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Vérifier si la discipline est spécifiée
    if not discipline_id:
        return jsonify({'error': 'Une discipline doit être spécifiée'}), 400
    
    # Construire la requête de base
    q = db.session.query(NoteS1).join(Eleve, NoteS1.eleve_ien == Eleve.ien)
    q = q.join(Classe, Eleve.classe_id == Classe.id)
    q = q.join(Niveau, Classe.niveau_id == Niveau.id)
    
    # Appliquer les filtres
    q = q.filter(NoteS1.annee_scolaire == annee_active)
    q = q.filter(NoteS1.discipline_id == discipline_id)
    
    if niveau_id:
        q = q.filter(Niveau.id == niveau_id)
    
    if classe_id:
        q = q.filter(Classe.id == classe_id)
    
    if sexe:
        if sexe == 'M':
            q = q.filter(Eleve.sexe.in_(['M', 'H']))
        else:
            q = q.filter(Eleve.sexe == 'F')
    
    q = q.filter(NoteS1.moy_d >= note_min, NoteS1.moy_d <= note_max)
    
    # Récupérer les données
    resultats = q.all()
    
    # Statistiques globales
    total_eleves = len(resultats)
    
    # Initialiser les statistiques
    stats = {
        'nb_eleves': 0,
        'moyenne_discipline': 0,
        'nb_moyenne': 0,
        'taux_reussite': 0,
        'min': 0,
        'max': 0
    }
    
    if total_eleves > 0:
        # Extraire les moyennes valides
        moyennes = [r.moy_d for r in resultats if r.moy_d is not None]
        
        # Calculer les statistiques
        stats = {
            'nb_eleves': total_eleves,
            'moyenne_discipline': round(sum(moyennes) / len(moyennes), 2) if moyennes else 0,
            'nb_moyenne': q.filter(NoteS1.moy_d >= 10).count(),
            'taux_reussite': round((q.filter(NoteS1.moy_d >= 10).count() / total_eleves * 100) if total_eleves > 0 else 0),
            'min': round(min(moyennes), 2) if moyennes else 0,
            'max': round(max(moyennes), 2) if moyennes else 0
        }
    
    return jsonify(stats)

@semestre1_bp.route('/api/report/discipline', methods=['POST'])
def api_generate_discipline_report():
    """
    API pour générer un rapport de discipline.
    Paramètres:
    - discipline_id: ID de la discipline
    - niveau_id: (optionnel) ID du niveau
    - classe_id: (optionnel) ID de la classe
    """
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    
    if not discipline_id:
        return jsonify({'error': 'discipline_id est obligatoire'}), 400
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Construire la requête de base pour les notes
    query = db.session.query(NoteS1, Eleve).\
        join(Eleve, NoteS1.eleve_ien == Eleve.ien).\
        join(Classe, Eleve.classe_id == Classe.id).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active)
    
    # Appliquer les filtres
    if niveau_id:
        query = query.join(Classe, Eleve.classe_id == Classe.id).\
                filter(Classe.niveau_id == niveau_id)
    if classe_id:
        query = query.filter(Eleve.classe_id == classe_id)
    
    # Récupérer les données
    notes_eleves = query.all()
    
    if not notes_eleves:
        return jsonify({'error': 'Aucune donnée trouvée pour ces critères'}), 404
    
    # Calculer les statistiques globales
    notes = [n.moy_d for n, _ in notes_eleves if n.moy_d is not None]
    total_eleves = len(notes)
    
    if total_eleves == 0:
        return jsonify({'error': 'Aucune note valide trouvée pour ces critères'}), 404
    
    # Statistiques générales
    moyenne = sum(notes) / total_eleves
    min_note = min(notes)
    max_note = max(notes)
    
    # Utiliser pandas pour calculer la médiane et l'écart-type
    notes_series = pd.Series(notes)
    mediane = float(notes_series.median())
    ecart_type = float(notes_series.std())
    
    # Statistiques par sexe
    notes_garcons = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe in ('M', 'H')]
    notes_filles = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe == 'F']
    
    total_garcons = len(notes_garcons)
    total_filles = len(notes_filles)
    
    moyenne_garcons = sum(notes_garcons) / total_garcons if total_garcons > 0 else 0
    moyenne_filles = sum(notes_filles) / total_filles if total_filles > 0 else 0
    
    reussite_garcons = sum(1 for n in notes_garcons if n >= 10)
    reussite_filles = sum(1 for n in notes_filles if n >= 10)
    
    taux_reussite_global = sum(1 for n in notes if n >= 10) / total_eleves * 100
    taux_reussite_garcons = reussite_garcons / total_garcons * 100 if total_garcons > 0 else 0
    taux_reussite_filles = reussite_filles / total_filles * 100 if total_filles > 0 else 0
    
    pct_garcons = (total_garcons / total_eleves * 100) if total_eleves > 0 else 0
    pct_filles = (total_filles / total_eleves * 100) if total_eleves > 0 else 0
    
    # Répartition par tranches de notes
    tranches = {
        'tres_bien': sum(1 for n in notes if n >= 16),
        'bien': sum(1 for n in notes if 14 <= n < 16),
        'assez_bien': sum(1 for n in notes if 12 <= n < 14),
        'passable': sum(1 for n in notes if 10 <= n < 12),
        'insuffisant': sum(1 for n in notes if n < 10)
    }
    
    # Récupérer la configuration de l'application
    config = Configuration.query.first()
    
    # Récupérer le niveau et la classe si spécifiés
    niveau = Niveau.query.get(niveau_id) if niveau_id else None
    classe = Classe.query.get(classe_id) if classe_id else None
    
    # Calculer la moyenne générale de l'établissement pour comparaison
    all_moyennes = db.session.query(NoteS1.moy_d).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active,
               NoteS1.moy_d.isnot(None)).all()
    
    all_moyenne = sum([m.moy_d for m in all_moyennes]) / len(all_moyennes) if all_moyennes else 0
    difference_moyenne = moyenne - all_moyenne
    
    # Préparer les données de retour
    report_data = {
        'stats': {
            'total_eleves': total_eleves,
            'moyenne_generale': round(moyenne, 2),
            'eleves_moyenne': sum(1 for n in notes if n >= 10),
            'taux_reussite': round(taux_reussite_global, 2),
            'min': round(min_note, 2),
            'max': round(max_note, 2),
            'mediane': round(mediane, 2),
            'ecart_type': round(ecart_type, 2),
            'total_garcons': total_garcons,
            'total_filles': total_filles,
            'pct_garcons': round(pct_garcons, 2),
            'pct_filles': round(pct_filles, 2),
            'moyenne_garcons': round(moyenne_garcons, 2),
            'moyenne_filles': round(moyenne_filles, 2),
            'reussite_garcons': reussite_garcons,
            'reussite_filles': reussite_filles,
            'taux_reussite_garcons': round(taux_reussite_garcons, 2),
            'taux_reussite_filles': round(taux_reussite_filles, 2),
            'tranches': tranches,
            'moyenne_generale_etablissement': round(all_moyenne, 2),
            'difference_moyenne': round(difference_moyenne, 2)
        },
        'config': {
            'nom_etablissement': config.nom_etablissement if config else 'Établissement'
        },
        'filter': {
            'discipline': discipline.libelle,
            'niveau': niveau.libelle if niveau else None,
            'classe': classe.libelle if classe else None
        },
        'annee_scolaire': annee_active
    }
    
    # Enregistrer le rapport pour référence ultérieure
    import json
    import datetime
    
    now = datetime.datetime.now()
    rapport = Rapport(
        type='discipline',
        date_creation=now,
        contenu=json.dumps(report_data),
        discipline_id=discipline_id,
        niveau_id=niveau_id,
        classe_id=classe_id,
        annee_scolaire=annee_active
    )
    db.session.add(rapport)
    db.session.commit()
    
    # Ajouter l'ID du rapport aux données de retour
    report_data['rapport_id'] = rapport.id
    
    return jsonify(report_data)

@semestre1_bp.route('/api/disciplines')
def api_get_disciplines():
    """API pour récupérer toutes les disciplines"""
    disciplines = Discipline.query.order_by(Discipline.libelle).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/<int:classe_id>')
def api_get_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines d'une classe spécifique"""
    # Récupérer la classe pour déterminer le niveau
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à cette classe via l'année en cours
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).filter(
        Eleve.classe_id == classe_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>')
def api_get_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines d'un niveau spécifique"""
    # Récupérer l'année active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes pour ce niveau
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).filter(
        Classe.niveau_id == niveau_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])

@semestre1_bp.route('/api/discipline_report')
def api_discipline_report_analysis():
    """API pour générer un rapport d'analyse par discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id', type=int)
    classe_id = request.args.get('classe_id', type=int)
    niveau_id = request.args.get('niveau_id', type=int)
    
    if not discipline_id:
        return jsonify({'error': 'Discipline non spécifiée'}), 400
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Construire la requête de base
    query = db.session.query(
        NoteS1.valeur.label('note'),
        Eleve.sexe,
        Classe.id.label('classe_id'),
        Classe.libelle.label('classe_libelle'),
        Niveau.id.label('niveau_id'),
        Niveau.libelle.label('niveau_libelle')
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).join(
        Niveau, Classe.niveau_id == Niveau.id
    ).filter(
        NoteS1.discipline_id == discipline_id,
        NoteS1.annee_scolaire == annee_active
    )
    
    # Filtrer par classe si spécifié
    if classe_id:
        query = query.filter(Classe.id == classe_id)
    
    # Filtrer par niveau si spécifié
    if niveau_id:
        query = query.filter(Niveau.id == niveau_id)
    
    # Exécuter la requête
    results = query.all()
    
    if not results:
        return jsonify({
            'discipline_id': discipline_id,
            'discipline_name': discipline.libelle,
            'niveau_id': niveau_id,
            'classe_id': classe_id,
            'results': [],
            'general_stats': {
                'average': 0,
                'highest': 0,
                'lowest': 0,
                'total_students': 0
            },
            'distribution': [0, 0, 0, 0, 0, 0, 0]  # Distribution vide
        })
    
    # Calculer les statistiques générales
    all_notes = [r.note for r in results]
    average = sum(all_notes) / len(all_notes)
    highest = max(all_notes)
    lowest = min(all_notes)
    total_students = len(all_notes)
    
    # Calculer la distribution des notes
    distribution = [0] * 7  # [0-5, 5-10, 10-12, 12-14, 14-16, 16-18, 18-20]
    for note in all_notes:
        if note < 5:
            distribution[0] += 1
        elif note < 10:
            distribution[1] += 1
        elif note < 12:
            distribution[2] += 1
        elif note < 14:
            distribution[3] += 1
        elif note < 16:
            distribution[4] += 1
        elif note < 18:
            distribution[5] += 1
        else:
            distribution[6] += 1
    
    # Regrouper les résultats par classe
    class_results = {}
    for r in results:
        class_id = r.classe_id
        if class_id not in class_results:
            class_results[class_id] = {
                'classe_id': class_id,
                'classe_name': r.classe_libelle,
                'notes': []
            }
        class_results[class_id]['notes'].append(r.note)
    
    # Calculer les statistiques par classe
    class_stats = []
    for class_id, data in class_results.items():
        notes = data['notes']
        class_stats.append({
            'classe_id': data['classe_id'],
            'classe_name': data['classe_name'],
            'average': sum(notes) / len(notes),
            'highest': max(notes),
            'lowest': min(notes),
            'student_count': len(notes)
        })
    
    # Trier les résultats par moyenne décroissante
    class_stats.sort(key=lambda x: x['average'], reverse=True)
    
    # Construire la réponse
    response = {
        'discipline_id': discipline_id,
        'discipline_name': discipline.libelle,
        'niveau_id': niveau_id,
        'classe_id': classe_id,
        'results': class_stats,
        'general_stats': {
            'average': average,
            'highest': highest,
            'lowest': lowest,
            'total_students': total_students
        },
        'distribution': distribution
    }
    
    return jsonify(response)

@semestre1_bp.route('/api/disciplines_by_niveau/<int:niveau_id>')
def api_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines par niveau"""
    disciplines = Discipline.query.filter_by(niveau_id=niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/api/disciplines_by_classe/<int:classe_id>')
def api_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines par classe"""
    # Récupérer le niveau associé à la classe
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à ce niveau
    disciplines = Discipline.query.filter_by(niveau_id=classe.niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/discipline_analysis')
@login_required
def discipline_analysis_admin():
    """Page for analyzing discipline statistics"""
    # Get all niveaux for filtering
    niveaux = Niveau.query.all()
    
    # Get all disciplines initially (will be filtered by JS)
    disciplines = Discipline.query.all()
    
    # Get current date for reporting
    current_date = datetime.datetime.now().strftime("%d/%m/%Y")
    
    return render_template(
        'semestre1/discipline_analysis.html',
        title='Analyse par Discipline',
        niveaux=niveaux,
        disciplines=disciplines,
        current_date=current_date
    )

@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>', methods=['GET'])
def get_disciplines_by_niveau_v2(niveau_id):
    """API route to get disciplines by niveau"""
    try:
        # Get all disciplines for classes in this niveau
        classes = Classe.query.filter_by(niveau_id=niveau_id).all()
        classe_ids = [c.id for c in classes]
        
        # Find disciplines associated with these classes
        disciplines = Discipline.query.filter(Discipline.classe_id.in_(classe_ids)).all()
        
        disciplines_data = [{'id': d.id, 'libelle': d.libelle} for d in disciplines]
        return jsonify({'status': 'success', 'disciplines': disciplines_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@semestre1_bp.route('/api/stats/discipline')
def discipline_stats():
    """API pour récupérer les statistiques d'une discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    sexe = request.args.get('sexe')
    note_min = request.args.get('note_min', '0')
    note_max = request.args.get('note_max', '20')
    
    # Convertir en float pour les comparaisons
    try:
        note_min = float(note_min)
        note_max = float(note_max)
    except (ValueError, TypeError):
        note_min = 0
        note_max = 20
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Vérifier si la discipline est spécifiée
    if not discipline_id:
        return jsonify({'error': 'Une discipline doit être spécifiée'}), 400
    
    # Construire la requête de base
    q = db.session.query(NoteS1).join(Eleve, NoteS1.eleve_ien == Eleve.ien)
    q = q.join(Classe, Eleve.classe_id == Classe.id)
    q = q.join(Niveau, Classe.niveau_id == Niveau.id)
    
    # Appliquer les filtres
    q = q.filter(NoteS1.annee_scolaire == annee_active)
    q = q.filter(NoteS1.discipline_id == discipline_id)
    
    if niveau_id:
        q = q.filter(Niveau.id == niveau_id)
    
    if classe_id:
        q = q.filter(Classe.id == classe_id)
    
    if sexe:
        if sexe == 'M':
            q = q.filter(Eleve.sexe.in_(['M', 'H']))
        else:
            q = q.filter(Eleve.sexe == 'F')
    
    q = q.filter(NoteS1.moy_d >= note_min, NoteS1.moy_d <= note_max)
    
    # Récupérer les données
    resultats = q.all()
    
    # Statistiques globales
    total_eleves = len(resultats)
    
    # Initialiser les statistiques
    stats = {
        'nb_eleves': 0,
        'moyenne_discipline': 0,
        'nb_moyenne': 0,
        'taux_reussite': 0,
        'min': 0,
        'max': 0
    }
    
    if total_eleves > 0:
        # Extraire les moyennes valides
        moyennes = [r.moy_d for r in resultats if r.moy_d is not None]
        
        # Calculer les statistiques
        stats = {
            'nb_eleves': total_eleves,
            'moyenne_discipline': round(sum(moyennes) / len(moyennes), 2) if moyennes else 0,
            'nb_moyenne': q.filter(NoteS1.moy_d >= 10).count(),
            'taux_reussite': round((q.filter(NoteS1.moy_d >= 10).count() / total_eleves * 100) if total_eleves > 0 else 0),
            'min': round(min(moyennes), 2) if moyennes else 0,
            'max': round(max(moyennes), 2) if moyennes else 0
        }
    
    return jsonify(stats)

@semestre1_bp.route('/api/report/discipline', methods=['POST'])
def api_generate_discipline_report():
    """
    API pour générer un rapport de discipline.
    Paramètres:
    - discipline_id: ID de la discipline
    - niveau_id: (optionnel) ID du niveau
    - classe_id: (optionnel) ID de la classe
    """
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    
    if not discipline_id:
        return jsonify({'error': 'discipline_id est obligatoire'}), 400
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Construire la requête de base pour les notes
    query = db.session.query(NoteS1, Eleve).\
        join(Eleve, NoteS1.eleve_ien == Eleve.ien).\
        join(Classe, Eleve.classe_id == Classe.id).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active)
    
    # Appliquer les filtres
    if niveau_id:
        query = query.join(Classe, Eleve.classe_id == Classe.id).\
                filter(Classe.niveau_id == niveau_id)
    if classe_id:
        query = query.filter(Eleve.classe_id == classe_id)
    
    # Récupérer les données
    notes_eleves = query.all()
    
    if not notes_eleves:
        return jsonify({'error': 'Aucune donnée trouvée pour ces critères'}), 404
    
    # Calculer les statistiques globales
    notes = [n.moy_d for n, _ in notes_eleves if n.moy_d is not None]
    total_eleves = len(notes)
    
    if total_eleves == 0:
        return jsonify({'error': 'Aucune note valide trouvée pour ces critères'}), 404
    
    # Statistiques générales
    moyenne = sum(notes) / total_eleves
    min_note = min(notes)
    max_note = max(notes)
    
    # Utiliser pandas pour calculer la médiane et l'écart-type
    notes_series = pd.Series(notes)
    mediane = float(notes_series.median())
    ecart_type = float(notes_series.std())
    
    # Statistiques par sexe
    notes_garcons = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe in ('M', 'H')]
    notes_filles = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe == 'F']
    
    total_garcons = len(notes_garcons)
    total_filles = len(notes_filles)
    
    moyenne_garcons = sum(notes_garcons) / total_garcons if total_garcons > 0 else 0
    moyenne_filles = sum(notes_filles) / total_filles if total_filles > 0 else 0
    
    reussite_garcons = sum(1 for n in notes_garcons if n >= 10)
    reussite_filles = sum(1 for n in notes_filles if n >= 10)
    
    taux_reussite_global = sum(1 for n in notes if n >= 10) / total_eleves * 100
    taux_reussite_garcons = reussite_garcons / total_garcons * 100 if total_garcons > 0 else 0
    taux_reussite_filles = reussite_filles / total_filles * 100 if total_filles > 0 else 0
    
    pct_garcons = (total_garcons / total_eleves * 100) if total_eleves > 0 else 0
    pct_filles = (total_filles / total_eleves * 100) if total_eleves > 0 else 0
    
    # Répartition par tranches de notes
    tranches = {
        'tres_bien': sum(1 for n in notes if n >= 16),
        'bien': sum(1 for n in notes if 14 <= n < 16),
        'assez_bien': sum(1 for n in notes if 12 <= n < 14),
        'passable': sum(1 for n in notes if 10 <= n < 12),
        'insuffisant': sum(1 for n in notes if n < 10)
    }
    
    # Récupérer la configuration de l'application
    config = Configuration.query.first()
    
    # Récupérer le niveau et la classe si spécifiés
    niveau = Niveau.query.get(niveau_id) if niveau_id else None
    classe = Classe.query.get(classe_id) if classe_id else None
    
    # Calculer la moyenne générale de l'établissement pour comparaison
    all_moyennes = db.session.query(NoteS1.moy_d).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active,
               NoteS1.moy_d.isnot(None)).all()
    
    all_moyenne = sum([m.moy_d for m in all_moyennes]) / len(all_moyennes) if all_moyennes else 0
    difference_moyenne = moyenne - all_moyenne
    
    # Préparer les données de retour
    report_data = {
        'stats': {
            'total_eleves': total_eleves,
            'moyenne_generale': round(moyenne, 2),
            'eleves_moyenne': sum(1 for n in notes if n >= 10),
            'taux_reussite': round(taux_reussite_global, 2),
            'min': round(min_note, 2),
            'max': round(max_note, 2),
            'mediane': round(mediane, 2),
            'ecart_type': round(ecart_type, 2),
            'total_garcons': total_garcons,
            'total_filles': total_filles,
            'pct_garcons': round(pct_garcons, 2),
            'pct_filles': round(pct_filles, 2),
            'moyenne_garcons': round(moyenne_garcons, 2),
            'moyenne_filles': round(moyenne_filles, 2),
            'reussite_garcons': reussite_garcons,
            'reussite_filles': reussite_filles,
            'taux_reussite_garcons': round(taux_reussite_garcons, 2),
            'taux_reussite_filles': round(taux_reussite_filles, 2),
            'tranches': tranches,
            'moyenne_generale_etablissement': round(all_moyenne, 2),
            'difference_moyenne': round(difference_moyenne, 2)
        },
        'config': {
            'nom_etablissement': config.nom_etablissement if config else 'Établissement'
        },
        'filter': {
            'discipline': discipline.libelle,
            'niveau': niveau.libelle if niveau else None,
            'classe': classe.libelle if classe else None
        },
        'annee_scolaire': annee_active
    }
    
    # Enregistrer le rapport pour référence ultérieure
    import json
    import datetime
    
    now = datetime.datetime.now()
    rapport = Rapport(
        type='discipline',
        date_creation=now,
        contenu=json.dumps(report_data),
        discipline_id=discipline_id,
        niveau_id=niveau_id,
        classe_id=classe_id,
        annee_scolaire=annee_active
    )
    db.session.add(rapport)
    db.session.commit()
    
    # Ajouter l'ID du rapport aux données de retour
    report_data['rapport_id'] = rapport.id
    
    return jsonify(report_data)

@semestre1_bp.route('/api/disciplines')
def api_get_disciplines():
    """API pour récupérer toutes les disciplines"""
    disciplines = Discipline.query.order_by(Discipline.libelle).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/<int:classe_id>')
def api_get_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines d'une classe spécifique"""
    # Récupérer la classe pour déterminer le niveau
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à cette classe via l'année en cours
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).filter(
        Eleve.classe_id == classe_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>')
def api_get_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines d'un niveau spécifique"""
    # Récupérer l'année active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes pour ce niveau
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).filter(
        Classe.niveau_id == niveau_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])

@semestre1_bp.route('/api/discipline_report')
def api_discipline_report_analysis():
    """API pour générer un rapport d'analyse par discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id', type=int)
    classe_id = request.args.get('classe_id', type=int)
    niveau_id = request.args.get('niveau_id', type=int)
    
    if not discipline_id:
        return jsonify({'error': 'Discipline non spécifiée'}), 400
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Construire la requête de base
    query = db.session.query(
        NoteS1.valeur.label('note'),
        Eleve.sexe,
        Classe.id.label('classe_id'),
        Classe.libelle.label('classe_libelle'),
        Niveau.id.label('niveau_id'),
        Niveau.libelle.label('niveau_libelle')
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).join(
        Niveau, Classe.niveau_id == Niveau.id
    ).filter(
        NoteS1.discipline_id == discipline_id,
        NoteS1.annee_scolaire == annee_active
    )
    
    # Filtrer par classe si spécifié
    if classe_id:
        query = query.filter(Classe.id == classe_id)
    
    # Filtrer par niveau si spécifié
    if niveau_id:
        query = query.filter(Niveau.id == niveau_id)
    
    # Exécuter la requête
    results = query.all()
    
    if not results:
        return jsonify({
            'discipline_id': discipline_id,
            'discipline_name': discipline.libelle,
            'niveau_id': niveau_id,
            'classe_id': classe_id,
            'results': [],
            'general_stats': {
                'average': 0,
                'highest': 0,
                'lowest': 0,
                'total_students': 0
            },
            'distribution': [0, 0, 0, 0, 0, 0, 0]  # Distribution vide
        })
    
    # Calculer les statistiques générales
    all_notes = [r.note for r in results]
    average = sum(all_notes) / len(all_notes)
    highest = max(all_notes)
    lowest = min(all_notes)
    total_students = len(all_notes)
    
    # Calculer la distribution des notes
    distribution = [0] * 7  # [0-5, 5-10, 10-12, 12-14, 14-16, 16-18, 18-20]
    for note in all_notes:
        if note < 5:
            distribution[0] += 1
        elif note < 10:
            distribution[1] += 1
        elif note < 12:
            distribution[2] += 1
        elif note < 14:
            distribution[3] += 1
        elif note < 16:
            distribution[4] += 1
        elif note < 18:
            distribution[5] += 1
        else:
            distribution[6] += 1
    
    # Regrouper les résultats par classe
    class_results = {}
    for r in results:
        class_id = r.classe_id
        if class_id not in class_results:
            class_results[class_id] = {
                'classe_id': class_id,
                'classe_name': r.classe_libelle,
                'notes': []
            }
        class_results[class_id]['notes'].append(r.note)
    
    # Calculer les statistiques par classe
    class_stats = []
    for class_id, data in class_results.items():
        notes = data['notes']
        class_stats.append({
            'classe_id': data['classe_id'],
            'classe_name': data['classe_name'],
            'average': sum(notes) / len(notes),
            'highest': max(notes),
            'lowest': min(notes),
            'student_count': len(notes)
        })
    
    # Trier les résultats par moyenne décroissante
    class_stats.sort(key=lambda x: x['average'], reverse=True)
    
    # Construire la réponse
    response = {
        'discipline_id': discipline_id,
        'discipline_name': discipline.libelle,
        'niveau_id': niveau_id,
        'classe_id': classe_id,
        'results': class_stats,
        'general_stats': {
            'average': average,
            'highest': highest,
            'lowest': lowest,
            'total_students': total_students
        },
        'distribution': distribution
    }
    
    return jsonify(response)

@semestre1_bp.route('/api/disciplines_by_niveau/<int:niveau_id>')
def api_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines par niveau"""
    disciplines = Discipline.query.filter_by(niveau_id=niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/api/disciplines_by_classe/<int:classe_id>')
def api_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines par classe"""
    # Récupérer le niveau associé à la classe
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à ce niveau
    disciplines = Discipline.query.filter_by(niveau_id=classe.niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/discipline_analysis')
@login_required
def discipline_analysis_admin():
    """Page for analyzing discipline statistics"""
    # Get all niveaux for filtering
    niveaux = Niveau.query.all()
    
    # Get all disciplines initially (will be filtered by JS)
    disciplines = Discipline.query.all()
    
    # Get current date for reporting
    current_date = datetime.datetime.now().strftime("%d/%m/%Y")
    
    return render_template(
        'semestre1/discipline_analysis.html',
        title='Analyse par Discipline',
        niveaux=niveaux,
        disciplines=disciplines,
        current_date=current_date
    )

@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>', methods=['GET'])
def get_disciplines_by_niveau_v2(niveau_id):
    """API route to get disciplines by niveau"""
    try:
        # Get all disciplines for classes in this niveau
        classes = Classe.query.filter_by(niveau_id=niveau_id).all()
        classe_ids = [c.id for c in classes]
        
        # Find disciplines associated with these classes
        disciplines = Discipline.query.filter(Discipline.classe_id.in_(classe_ids)).all()
        
        disciplines_data = [{'id': d.id, 'libelle': d.libelle} for d in disciplines]
        return jsonify({'status': 'success', 'disciplines': disciplines_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@semestre1_bp.route('/api/stats/discipline')
def discipline_stats():
    """API pour récupérer les statistiques d'une discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    sexe = request.args.get('sexe')
    note_min = request.args.get('note_min', '0')
    note_max = request.args.get('note_max', '20')
    
    # Convertir en float pour les comparaisons
    try:
        note_min = float(note_min)
        note_max = float(note_max)
    except (ValueError, TypeError):
        note_min = 0
        note_max = 20
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Vérifier si la discipline est spécifiée
    if not discipline_id:
        return jsonify({'error': 'Une discipline doit être spécifiée'}), 400
    
    # Construire la requête de base
    q = db.session.query(NoteS1).join(Eleve, NoteS1.eleve_ien == Eleve.ien)
    q = q.join(Classe, Eleve.classe_id == Classe.id)
    q = q.join(Niveau, Classe.niveau_id == Niveau.id)
    
    # Appliquer les filtres
    q = q.filter(NoteS1.annee_scolaire == annee_active)
    q = q.filter(NoteS1.discipline_id == discipline_id)
    
    if niveau_id:
        q = q.filter(Niveau.id == niveau_id)
    
    if classe_id:
        q = q.filter(Classe.id == classe_id)
    
    if sexe:
        if sexe == 'M':
            q = q.filter(Eleve.sexe.in_(['M', 'H']))
        else:
            q = q.filter(Eleve.sexe == 'F')
    
    q = q.filter(NoteS1.moy_d >= note_min, NoteS1.moy_d <= note_max)
    
    # Récupérer les données
    resultats = q.all()
    
    # Statistiques globales
    total_eleves = len(resultats)
    
    # Initialiser les statistiques
    stats = {
        'nb_eleves': 0,
        'moyenne_discipline': 0,
        'nb_moyenne': 0,
        'taux_reussite': 0,
        'min': 0,
        'max': 0
    }
    
    if total_eleves > 0:
        # Extraire les moyennes valides
        moyennes = [r.moy_d for r in resultats if r.moy_d is not None]
        
        # Calculer les statistiques
        stats = {
            'nb_eleves': total_eleves,
            'moyenne_discipline': round(sum(moyennes) / len(moyennes), 2) if moyennes else 0,
            'nb_moyenne': q.filter(NoteS1.moy_d >= 10).count(),
            'taux_reussite': round((q.filter(NoteS1.moy_d >= 10).count() / total_eleves * 100) if total_eleves > 0 else 0),
            'min': round(min(moyennes), 2) if moyennes else 0,
            'max': round(max(moyennes), 2) if moyennes else 0
        }
    
    return jsonify(stats)

@semestre1_bp.route('/api/report/discipline', methods=['POST'])
def api_generate_discipline_report():
    """
    API pour générer un rapport de discipline.
    Paramètres:
    - discipline_id: ID de la discipline
    - niveau_id: (optionnel) ID du niveau
    - classe_id: (optionnel) ID de la classe
    """
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    
    if not discipline_id:
        return jsonify({'error': 'discipline_id est obligatoire'}), 400
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Construire la requête de base pour les notes
    query = db.session.query(NoteS1, Eleve).\
        join(Eleve, NoteS1.eleve_ien == Eleve.ien).\
        join(Classe, Eleve.classe_id == Classe.id).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active)
    
    # Appliquer les filtres
    if niveau_id:
        query = query.join(Classe, Eleve.classe_id == Classe.id).\
                filter(Classe.niveau_id == niveau_id)
    if classe_id:
        query = query.filter(Eleve.classe_id == classe_id)
    
    # Récupérer les données
    notes_eleves = query.all()
    
    if not notes_eleves:
        return jsonify({'error': 'Aucune donnée trouvée pour ces critères'}), 404
    
    # Calculer les statistiques globales
    notes = [n.moy_d for n, _ in notes_eleves if n.moy_d is not None]
    total_eleves = len(notes)
    
    if total_eleves == 0:
        return jsonify({'error': 'Aucune note valide trouvée pour ces critères'}), 404
    
    # Statistiques générales
    moyenne = sum(notes) / total_eleves
    min_note = min(notes)
    max_note = max(notes)
    
    # Utiliser pandas pour calculer la médiane et l'écart-type
    notes_series = pd.Series(notes)
    mediane = float(notes_series.median())
    ecart_type = float(notes_series.std())
    
    # Statistiques par sexe
    notes_garcons = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe in ('M', 'H')]
    notes_filles = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe == 'F']
    
    total_garcons = len(notes_garcons)
    total_filles = len(notes_filles)
    
    moyenne_garcons = sum(notes_garcons) / total_garcons if total_garcons > 0 else 0
    moyenne_filles = sum(notes_filles) / total_filles if total_filles > 0 else 0
    
    reussite_garcons = sum(1 for n in notes_garcons if n >= 10)
    reussite_filles = sum(1 for n in notes_filles if n >= 10)
    
    taux_reussite_global = sum(1 for n in notes if n >= 10) / total_eleves * 100
    taux_reussite_garcons = reussite_garcons / total_garcons * 100 if total_garcons > 0 else 0
    taux_reussite_filles = reussite_filles / total_filles * 100 if total_filles > 0 else 0
    
    pct_garcons = (total_garcons / total_eleves * 100) if total_eleves > 0 else 0
    pct_filles = (total_filles / total_eleves * 100) if total_eleves > 0 else 0
    
    # Répartition par tranches de notes
    tranches = {
        'tres_bien': sum(1 for n in notes if n >= 16),
        'bien': sum(1 for n in notes if 14 <= n < 16),
        'assez_bien': sum(1 for n in notes if 12 <= n < 14),
        'passable': sum(1 for n in notes if 10 <= n < 12),
        'insuffisant': sum(1 for n in notes if n < 10)
    }
    
    # Récupérer la configuration de l'application
    config = Configuration.query.first()
    
    # Récupérer le niveau et la classe si spécifiés
    niveau = Niveau.query.get(niveau_id) if niveau_id else None
    classe = Classe.query.get(classe_id) if classe_id else None
    
    # Calculer la moyenne générale de l'établissement pour comparaison
    all_moyennes = db.session.query(NoteS1.moy_d).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active,
               NoteS1.moy_d.isnot(None)).all()
    
    all_moyenne = sum([m.moy_d for m in all_moyennes]) / len(all_moyennes) if all_moyennes else 0
    difference_moyenne = moyenne - all_moyenne
    
    # Préparer les données de retour
    report_data = {
        'stats': {
            'total_eleves': total_eleves,
            'moyenne_generale': round(moyenne, 2),
            'eleves_moyenne': sum(1 for n in notes if n >= 10),
            'taux_reussite': round(taux_reussite_global, 2),
            'min': round(min_note, 2),
            'max': round(max_note, 2),
            'mediane': round(mediane, 2),
            'ecart_type': round(ecart_type, 2),
            'total_garcons': total_garcons,
            'total_filles': total_filles,
            'pct_garcons': round(pct_garcons, 2),
            'pct_filles': round(pct_filles, 2),
            'moyenne_garcons': round(moyenne_garcons, 2),
            'moyenne_filles': round(moyenne_filles, 2),
            'reussite_garcons': reussite_garcons,
            'reussite_filles': reussite_filles,
            'taux_reussite_garcons': round(taux_reussite_garcons, 2),
            'taux_reussite_filles': round(taux_reussite_filles, 2),
            'tranches': tranches,
            'moyenne_generale_etablissement': round(all_moyenne, 2),
            'difference_moyenne': round(difference_moyenne, 2)
        },
        'config': {
            'nom_etablissement': config.nom_etablissement if config else 'Établissement'
        },
        'filter': {
            'discipline': discipline.libelle,
            'niveau': niveau.libelle if niveau else None,
            'classe': classe.libelle if classe else None
        },
        'annee_scolaire': annee_active
    }
    
    # Enregistrer le rapport pour référence ultérieure
    import json
    import datetime
    
    now = datetime.datetime.now()
    rapport = Rapport(
        type='discipline',
        date_creation=now,
        contenu=json.dumps(report_data),
        discipline_id=discipline_id,
        niveau_id=niveau_id,
        classe_id=classe_id,
        annee_scolaire=annee_active
    )
    db.session.add(rapport)
    db.session.commit()
    
    # Ajouter l'ID du rapport aux données de retour
    report_data['rapport_id'] = rapport.id
    
    return jsonify(report_data)

@semestre1_bp.route('/api/disciplines')
def api_get_disciplines():
    """API pour récupérer toutes les disciplines"""
    disciplines = Discipline.query.order_by(Discipline.libelle).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/<int:classe_id>')
def api_get_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines d'une classe spécifique"""
    # Récupérer la classe pour déterminer le niveau
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à cette classe via l'année en cours
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).filter(
        Eleve.classe_id == classe_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>')
def api_get_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines d'un niveau spécifique"""
    # Récupérer l'année active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes pour ce niveau
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).filter(
        Classe.niveau_id == niveau_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])

@semestre1_bp.route('/api/discipline_report')
def api_discipline_report_analysis():
    """API pour générer un rapport d'analyse par discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id', type=int)
    classe_id = request.args.get('classe_id', type=int)
    niveau_id = request.args.get('niveau_id', type=int)
    
    if not discipline_id:
        return jsonify({'error': 'Discipline non spécifiée'}), 400
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Construire la requête de base
    query = db.session.query(
        NoteS1.valeur.label('note'),
        Eleve.sexe,
        Classe.id.label('classe_id'),
        Classe.libelle.label('classe_libelle'),
        Niveau.id.label('niveau_id'),
        Niveau.libelle.label('niveau_libelle')
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).join(
        Niveau, Classe.niveau_id == Niveau.id
    ).filter(
        NoteS1.discipline_id == discipline_id,
        NoteS1.annee_scolaire == annee_active
    )
    
    # Filtrer par classe si spécifié
    if classe_id:
        query = query.filter(Classe.id == classe_id)
    
    # Filtrer par niveau si spécifié
    if niveau_id:
        query = query.filter(Niveau.id == niveau_id)
    
    # Exécuter la requête
    results = query.all()
    
    if not results:
        return jsonify({
            'discipline_id': discipline_id,
            'discipline_name': discipline.libelle,
            'niveau_id': niveau_id,
            'classe_id': classe_id,
            'results': [],
            'general_stats': {
                'average': 0,
                'highest': 0,
                'lowest': 0,
                'total_students': 0
            },
            'distribution': [0, 0, 0, 0, 0, 0, 0]  # Distribution vide
        })
    
    # Calculer les statistiques générales
    all_notes = [r.note for r in results]
    average = sum(all_notes) / len(all_notes)
    highest = max(all_notes)
    lowest = min(all_notes)
    total_students = len(all_notes)
    
    # Calculer la distribution des notes
    distribution = [0] * 7  # [0-5, 5-10, 10-12, 12-14, 14-16, 16-18, 18-20]
    for note in all_notes:
        if note < 5:
            distribution[0] += 1
        elif note < 10:
            distribution[1] += 1
        elif note < 12:
            distribution[2] += 1
        elif note < 14:
            distribution[3] += 1
        elif note < 16:
            distribution[4] += 1
        elif note < 18:
            distribution[5] += 1
        else:
            distribution[6] += 1
    
    # Regrouper les résultats par classe
    class_results = {}
    for r in results:
        class_id = r.classe_id
        if class_id not in class_results:
            class_results[class_id] = {
                'classe_id': class_id,
                'classe_name': r.classe_libelle,
                'notes': []
            }
        class_results[class_id]['notes'].append(r.note)
    
    # Calculer les statistiques par classe
    class_stats = []
    for class_id, data in class_results.items():
        notes = data['notes']
        class_stats.append({
            'classe_id': data['classe_id'],
            'classe_name': data['classe_name'],
            'average': sum(notes) / len(notes),
            'highest': max(notes),
            'lowest': min(notes),
            'student_count': len(notes)
        })
    
    # Trier les résultats par moyenne décroissante
    class_stats.sort(key=lambda x: x['average'], reverse=True)
    
    # Construire la réponse
    response = {
        'discipline_id': discipline_id,
        'discipline_name': discipline.libelle,
        'niveau_id': niveau_id,
        'classe_id': classe_id,
        'results': class_stats,
        'general_stats': {
            'average': average,
            'highest': highest,
            'lowest': lowest,
            'total_students': total_students
        },
        'distribution': distribution
    }
    
    return jsonify(response)

@semestre1_bp.route('/api/disciplines_by_niveau/<int:niveau_id>')
def api_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines par niveau"""
    disciplines = Discipline.query.filter_by(niveau_id=niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/api/disciplines_by_classe/<int:classe_id>')
def api_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines par classe"""
    # Récupérer le niveau associé à la classe
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à ce niveau
    disciplines = Discipline.query.filter_by(niveau_id=classe.niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/discipline_analysis')
@login_required
def discipline_analysis_admin():
    """Page for analyzing discipline statistics"""
    # Get all niveaux for filtering
    niveaux = Niveau.query.all()
    
    # Get all disciplines initially (will be filtered by JS)
    disciplines = Discipline.query.all()
    
    # Get current date for reporting
    current_date = datetime.datetime.now().strftime("%d/%m/%Y")
    
    return render_template(
        'semestre1/discipline_analysis.html',
        title='Analyse par Discipline',
        niveaux=niveaux,
        disciplines=disciplines,
        current_date=current_date
    )

@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>', methods=['GET'])
def get_disciplines_by_niveau_v2(niveau_id):
    """API route to get disciplines by niveau"""
    try:
        # Get all disciplines for classes in this niveau
        classes = Classe.query.filter_by(niveau_id=niveau_id).all()
        classe_ids = [c.id for c in classes]
        
        # Find disciplines associated with these classes
        disciplines = Discipline.query.filter(Discipline.classe_id.in_(classe_ids)).all()
        
        disciplines_data = [{'id': d.id, 'libelle': d.libelle} for d in disciplines]
        return jsonify({'status': 'success', 'disciplines': disciplines_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@semestre1_bp.route('/api/stats/discipline')
def discipline_stats():
    """API pour récupérer les statistiques d'une discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    sexe = request.args.get('sexe')
    note_min = request.args.get('note_min', '0')
    note_max = request.args.get('note_max', '20')
    
    # Convertir en float pour les comparaisons
    try:
        note_min = float(note_min)
        note_max = float(note_max)
    except (ValueError, TypeError):
        note_min = 0
        note_max = 20
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Vérifier si la discipline est spécifiée
    if not discipline_id:
        return jsonify({'error': 'Une discipline doit être spécifiée'}), 400
    
    # Construire la requête de base
    q = db.session.query(NoteS1).join(Eleve, NoteS1.eleve_ien == Eleve.ien)
    q = q.join(Classe, Eleve.classe_id == Classe.id)
    q = q.join(Niveau, Classe.niveau_id == Niveau.id)
    
    # Appliquer les filtres
    q = q.filter(NoteS1.annee_scolaire == annee_active)
    q = q.filter(NoteS1.discipline_id == discipline_id)
    
    if niveau_id:
        q = q.filter(Niveau.id == niveau_id)
    
    if classe_id:
        q = q.filter(Classe.id == classe_id)
    
    if sexe:
        if sexe == 'M':
            q = q.filter(Eleve.sexe.in_(['M', 'H']))
        else:
            q = q.filter(Eleve.sexe == 'F')
    
    q = q.filter(NoteS1.moy_d >= note_min, NoteS1.moy_d <= note_max)
    
    # Récupérer les données
    resultats = q.all()
    
    # Statistiques globales
    total_eleves = len(resultats)
    
    # Initialiser les statistiques
    stats = {
        'nb_eleves': 0,
        'moyenne_discipline': 0,
        'nb_moyenne': 0,
        'taux_reussite': 0,
        'min': 0,
        'max': 0
    }
    
    if total_eleves > 0:
        # Extraire les moyennes valides
        moyennes = [r.moy_d for r in resultats if r.moy_d is not None]
        
        # Calculer les statistiques
        stats = {
            'nb_eleves': total_eleves,
            'moyenne_discipline': round(sum(moyennes) / len(moyennes), 2) if moyennes else 0,
            'nb_moyenne': q.filter(NoteS1.moy_d >= 10).count(),
            'taux_reussite': round((q.filter(NoteS1.moy_d >= 10).count() / total_eleves * 100) if total_eleves > 0 else 0),
            'min': round(min(moyennes), 2) if moyennes else 0,
            'max': round(max(moyennes), 2) if moyennes else 0
        }
    
    return jsonify(stats)

@semestre1_bp.route('/api/report/discipline', methods=['POST'])
def api_generate_discipline_report():
    """
    API pour générer un rapport de discipline.
    Paramètres:
    - discipline_id: ID de la discipline
    - niveau_id: (optionnel) ID du niveau
    - classe_id: (optionnel) ID de la classe
    """
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    
    if not discipline_id:
        return jsonify({'error': 'discipline_id est obligatoire'}), 400
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Construire la requête de base pour les notes
    query = db.session.query(NoteS1, Eleve).\
        join(Eleve, NoteS1.eleve_ien == Eleve.ien).\
        join(Classe, Eleve.classe_id == Classe.id).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active)
    
    # Appliquer les filtres
    if niveau_id:
        query = query.join(Classe, Eleve.classe_id == Classe.id).\
                filter(Classe.niveau_id == niveau_id)
    if classe_id:
        query = query.filter(Eleve.classe_id == classe_id)
    
    # Récupérer les données
    notes_eleves = query.all()
    
    if not notes_eleves:
        return jsonify({'error': 'Aucune donnée trouvée pour ces critères'}), 404
    
    # Calculer les statistiques globales
    notes = [n.moy_d for n, _ in notes_eleves if n.moy_d is not None]
    total_eleves = len(notes)
    
    if total_eleves == 0:
        return jsonify({'error': 'Aucune note valide trouvée pour ces critères'}), 404
    
    # Statistiques générales
    moyenne = sum(notes) / total_eleves
    min_note = min(notes)
    max_note = max(notes)
    
    # Utiliser pandas pour calculer la médiane et l'écart-type
    notes_series = pd.Series(notes)
    mediane = float(notes_series.median())
    ecart_type = float(notes_series.std())
    
    # Statistiques par sexe
    notes_garcons = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe in ('M', 'H')]
    notes_filles = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe == 'F']
    
    total_garcons = len(notes_garcons)
    total_filles = len(notes_filles)
    
    moyenne_garcons = sum(notes_garcons) / total_garcons if total_garcons > 0 else 0
    moyenne_filles = sum(notes_filles) / total_filles if total_filles > 0 else 0
    
    reussite_garcons = sum(1 for n in notes_garcons if n >= 10)
    reussite_filles = sum(1 for n in notes_filles if n >= 10)
    
    taux_reussite_global = sum(1 for n in notes if n >= 10) / total_eleves * 100
    taux_reussite_garcons = reussite_garcons / total_garcons * 100 if total_garcons > 0 else 0
    taux_reussite_filles = reussite_filles / total_filles * 100 if total_filles > 0 else 0
    
    pct_garcons = (total_garcons / total_eleves * 100) if total_eleves > 0 else 0
    pct_filles = (total_filles / total_eleves * 100) if total_eleves > 0 else 0
    
    # Répartition par tranches de notes
    tranches = {
        'tres_bien': sum(1 for n in notes if n >= 16),
        'bien': sum(1 for n in notes if 14 <= n < 16),
        'assez_bien': sum(1 for n in notes if 12 <= n < 14),
        'passable': sum(1 for n in notes if 10 <= n < 12),
        'insuffisant': sum(1 for n in notes if n < 10)
    }
    
    # Récupérer la configuration de l'application
    config = Configuration.query.first()
    
    # Récupérer le niveau et la classe si spécifiés
    niveau = Niveau.query.get(niveau_id) if niveau_id else None
    classe = Classe.query.get(classe_id) if classe_id else None
    
    # Calculer la moyenne générale de l'établissement pour comparaison
    all_moyennes = db.session.query(NoteS1.moy_d).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active,
               NoteS1.moy_d.isnot(None)).all()
    
    all_moyenne = sum([m.moy_d for m in all_moyennes]) / len(all_moyennes) if all_moyennes else 0
    difference_moyenne = moyenne - all_moyenne
    
    # Préparer les données de retour
    report_data = {
        'stats': {
            'total_eleves': total_eleves,
            'moyenne_generale': round(moyenne, 2),
            'eleves_moyenne': sum(1 for n in notes if n >= 10),
            'taux_reussite': round(taux_reussite_global, 2),
            'min': round(min_note, 2),
            'max': round(max_note, 2),
            'mediane': round(mediane, 2),
            'ecart_type': round(ecart_type, 2),
            'total_garcons': total_garcons,
            'total_filles': total_filles,
            'pct_garcons': round(pct_garcons, 2),
            'pct_filles': round(pct_filles, 2),
            'moyenne_garcons': round(moyenne_garcons, 2),
            'moyenne_filles': round(moyenne_filles, 2),
            'reussite_garcons': reussite_garcons,
            'reussite_filles': reussite_filles,
            'taux_reussite_garcons': round(taux_reussite_garcons, 2),
            'taux_reussite_filles': round(taux_reussite_filles, 2),
            'tranches': tranches,
            'moyenne_generale_etablissement': round(all_moyenne, 2),
            'difference_moyenne': round(difference_moyenne, 2)
        },
        'config': {
            'nom_etablissement': config.nom_etablissement if config else 'Établissement'
        },
        'filter': {
            'discipline': discipline.libelle,
            'niveau': niveau.libelle if niveau else None,
            'classe': classe.libelle if classe else None
        },
        'annee_scolaire': annee_active
    }
    
    # Enregistrer le rapport pour référence ultérieure
    import json
    import datetime
    
    now = datetime.datetime.now()
    rapport = Rapport(
        type='discipline',
        date_creation=now,
        contenu=json.dumps(report_data),
        discipline_id=discipline_id,
        niveau_id=niveau_id,
        classe_id=classe_id,
        annee_scolaire=annee_active
    )
    db.session.add(rapport)
    db.session.commit()
    
    # Ajouter l'ID du rapport aux données de retour
    report_data['rapport_id'] = rapport.id
    
    return jsonify(report_data)

@semestre1_bp.route('/api/disciplines')
def api_get_disciplines():
    """API pour récupérer toutes les disciplines"""
    disciplines = Discipline.query.order_by(Discipline.libelle).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/<int:classe_id>')
def api_get_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines d'une classe spécifique"""
    # Récupérer la classe pour déterminer le niveau
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à cette classe via l'année en cours
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).filter(
        Eleve.classe_id == classe_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>')
def api_get_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines d'un niveau spécifique"""
    # Récupérer l'année active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes pour ce niveau
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).filter(
        Classe.niveau_id == niveau_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])

@semestre1_bp.route('/api/discipline_report')
def api_discipline_report_analysis():
    """API pour générer un rapport d'analyse par discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id', type=int)
    classe_id = request.args.get('classe_id', type=int)
    niveau_id = request.args.get('niveau_id', type=int)
    
    if not discipline_id:
        return jsonify({'error': 'Discipline non spécifiée'}), 400
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Construire la requête de base
    query = db.session.query(
        NoteS1.valeur.label('note'),
        Eleve.sexe,
        Classe.id.label('classe_id'),
        Classe.libelle.label('classe_libelle'),
        Niveau.id.label('niveau_id'),
        Niveau.libelle.label('niveau_libelle')
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).join(
        Niveau, Classe.niveau_id == Niveau.id
    ).filter(
        NoteS1.discipline_id == discipline_id,
        NoteS1.annee_scolaire == annee_active
    )
    
    # Filtrer par classe si spécifié
    if classe_id:
        query = query.filter(Classe.id == classe_id)
    
    # Filtrer par niveau si spécifié
    if niveau_id:
        query = query.filter(Niveau.id == niveau_id)
    
    # Exécuter la requête
    results = query.all()
    
    if not results:
        return jsonify({
            'discipline_id': discipline_id,
            'discipline_name': discipline.libelle,
            'niveau_id': niveau_id,
            'classe_id': classe_id,
            'results': [],
            'general_stats': {
                'average': 0,
                'highest': 0,
                'lowest': 0,
                'total_students': 0
            },
            'distribution': [0, 0, 0, 0, 0, 0, 0]  # Distribution vide
        })
    
    # Calculer les statistiques générales
    all_notes = [r.note for r in results]
    average = sum(all_notes) / len(all_notes)
    highest = max(all_notes)
    lowest = min(all_notes)
    total_students = len(all_notes)
    
    # Calculer la distribution des notes
    distribution = [0] * 7  # [0-5, 5-10, 10-12, 12-14, 14-16, 16-18, 18-20]
    for note in all_notes:
        if note < 5:
            distribution[0] += 1
        elif note < 10:
            distribution[1] += 1
        elif note < 12:
            distribution[2] += 1
        elif note < 14:
            distribution[3] += 1
        elif note < 16:
            distribution[4] += 1
        elif note < 18:
            distribution[5] += 1
        else:
            distribution[6] += 1
    
    # Regrouper les résultats par classe
    class_results = {}
    for r in results:
        class_id = r.classe_id
        if class_id not in class_results:
            class_results[class_id] = {
                'classe_id': class_id,
                'classe_name': r.classe_libelle,
                'notes': []
            }
        class_results[class_id]['notes'].append(r.note)
    
    # Calculer les statistiques par classe
    class_stats = []
    for class_id, data in class_results.items():
        notes = data['notes']
        class_stats.append({
            'classe_id': data['classe_id'],
            'classe_name': data['classe_name'],
            'average': sum(notes) / len(notes),
            'highest': max(notes),
            'lowest': min(notes),
            'student_count': len(notes)
        })
    
    # Trier les résultats par moyenne décroissante
    class_stats.sort(key=lambda x: x['average'], reverse=True)
    
    # Construire la réponse
    response = {
        'discipline_id': discipline_id,
        'discipline_name': discipline.libelle,
        'niveau_id': niveau_id,
        'classe_id': classe_id,
        'results': class_stats,
        'general_stats': {
            'average': average,
            'highest': highest,
            'lowest': lowest,
            'total_students': total_students
        },
        'distribution': distribution
    }
    
    return jsonify(response)

@semestre1_bp.route('/api/disciplines_by_niveau/<int:niveau_id>')
def api_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines par niveau"""
    disciplines = Discipline.query.filter_by(niveau_id=niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/api/disciplines_by_classe/<int:classe_id>')
def api_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines par classe"""
    # Récupérer le niveau associé à la classe
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à ce niveau
    disciplines = Discipline.query.filter_by(niveau_id=classe.niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/discipline_analysis')
@login_required
def discipline_analysis_admin():
    """Page for analyzing discipline statistics"""
    # Get all niveaux for filtering
    niveaux = Niveau.query.all()
    
    # Get all disciplines initially (will be filtered by JS)
    disciplines = Discipline.query.all()
    
    # Get current date for reporting
    current_date = datetime.datetime.now().strftime("%d/%m/%Y")
    
    return render_template(
        'semestre1/discipline_analysis.html',
        title='Analyse par Discipline',
        niveaux=niveaux,
        disciplines=disciplines,
        current_date=current_date
    )

@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>', methods=['GET'])
def get_disciplines_by_niveau_v2(niveau_id):
    """API route to get disciplines by niveau"""
    try:
        # Get all disciplines for classes in this niveau
        classes = Classe.query.filter_by(niveau_id=niveau_id).all()
        classe_ids = [c.id for c in classes]
        
        # Find disciplines associated with these classes
        disciplines = Discipline.query.filter(Discipline.classe_id.in_(classe_ids)).all()
        
        disciplines_data = [{'id': d.id, 'libelle': d.libelle} for d in disciplines]
        return jsonify({'status': 'success', 'disciplines': disciplines_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@semestre1_bp.route('/api/stats/discipline')
def discipline_stats():
    """API pour récupérer les statistiques d'une discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    sexe = request.args.get('sexe')
    note_min = request.args.get('note_min', '0')
    note_max = request.args.get('note_max', '20')
    
    # Convertir en float pour les comparaisons
    try:
        note_min = float(note_min)
        note_max = float(note_max)
    except (ValueError, TypeError):
        note_min = 0
        note_max = 20
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Vérifier si la discipline est spécifiée
    if not discipline_id:
        return jsonify({'error': 'Une discipline doit être spécifiée'}), 400
    
    # Construire la requête de base
    q = db.session.query(NoteS1).join(Eleve, NoteS1.eleve_ien == Eleve.ien)
    q = q.join(Classe, Eleve.classe_id == Classe.id)
    q = q.join(Niveau, Classe.niveau_id == Niveau.id)
    
    # Appliquer les filtres
    q = q.filter(NoteS1.annee_scolaire == annee_active)
    q = q.filter(NoteS1.discipline_id == discipline_id)
    
    if niveau_id:
        q = q.filter(Niveau.id == niveau_id)
    
    if classe_id:
        q = q.filter(Classe.id == classe_id)
    
    if sexe:
        if sexe == 'M':
            q = q.filter(Eleve.sexe.in_(['M', 'H']))
        else:
            q = q.filter(Eleve.sexe == 'F')
    
    q = q.filter(NoteS1.moy_d >= note_min, NoteS1.moy_d <= note_max)
    
    # Récupérer les données
    resultats = q.all()
    
    # Statistiques globales
    total_eleves = len(resultats)
    
    # Initialiser les statistiques
    stats = {
        'nb_eleves': 0,
        'moyenne_discipline': 0,
        'nb_moyenne': 0,
        'taux_reussite': 0,
        'min': 0,
        'max': 0
    }
    
    if total_eleves > 0:
        # Extraire les moyennes valides
        moyennes = [r.moy_d for r in resultats if r.moy_d is not None]
        
        # Calculer les statistiques
        stats = {
            'nb_eleves': total_eleves,
            'moyenne_discipline': round(sum(moyennes) / len(moyennes), 2) if moyennes else 0,
            'nb_moyenne': q.filter(NoteS1.moy_d >= 10).count(),
            'taux_reussite': round((q.filter(NoteS1.moy_d >= 10).count() / total_eleves * 100) if total_eleves > 0 else 0),
            'min': round(min(moyennes), 2) if moyennes else 0,
            'max': round(max(moyennes), 2) if moyennes else 0
        }
    
    return jsonify(stats)

@semestre1_bp.route('/report/discipline/<int:rapport_id>/download', methods=['GET'])
def download_discipline_report(rapport_id):
    """
    Télécharger le rapport d'analyse de discipline au format PDF
    """
    from app.models.models import Rapport, Discipline, AnneeAcademique, Niveau, Classe
    import json
    from flask import render_template, make_response
    import pdfkit
    from datetime import datetime
    import os
    
    # Récupérer le rapport
    rapport = Rapport.query.get_or_404(rapport_id)
    
    if rapport.type != 'discipline':
        return jsonify({'error': 'Type de rapport incorrect'}), 400
    
    # Récupérer les données associées
    discipline = Discipline.query.get(rapport.discipline_id)
    annee = AnneeAcademique.query.get(rapport.annee_id)
    niveau = Niveau.query.get(rapport.niveau_id) if rapport.niveau_id else None
    classe = Classe.query.get(rapport.classe_id) if rapport.classe_id else None
    
    # Convertir le contenu JSON en dictionnaire
    contenu = json.loads(rapport.contenu)
    
    # Préparer les données pour le template
    context = {
        'titre': f"Rapport d'analyse - {discipline.libelle}",
        'discipline': discipline.libelle,
        'annee': annee.libelle,
        'niveau': niveau.libelle if niveau else "Tous les niveaux",
        'classe': classe.libelle if classe else "Toutes les classes",
        'date_creation': rapport.date_creation.strftime('%d/%m/%Y %H:%M'),
        'statistiques': contenu.get('statistiques', {}),
        'stats_genre': contenu.get('stats_genre', {}),
        'stats_reussite': contenu.get('stats_reussite', {}),
        'tranches': contenu.get('tranches', {}),
        'tranches_pourcentage': contenu.get('tranches_pourcentage', {})
    }
    
    # Générer le HTML du rapport
    html = render_template('semestre1/report.html', **context, print_mode=True)
    
    # Configurer pdfkit
    options = {
        'page-size': 'A4',
        'encoding': 'UTF-8',
        'margin-top': '1cm',
        'margin-right': '1cm',
        'margin-bottom': '1cm',
        'margin-left': '1cm',
        'enable-local-file-access': ''
    }
    
    # Chemin pour enregistrer le PDF temporairement
    filename = f"discipline_report_{rapport_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    temp_path = os.path.join('app', 'static', 'uploads', 'reports', filename)
    
    # Créer le dossier de destination s'il n'existe pas
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
    
    # Générer le PDF
    css_path = os.path.join('app', 'static', 'css', 'print.css')
    pdfkit.from_string(html, temp_path, options=options, css=css_path)
    
    # Renvoyer le PDF au client
    with open(temp_path, 'rb') as f:
        binary_pdf = f.read()
    
    response = make_response(binary_pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=rapport_discipline_{discipline.libelle}_{annee.libelle}.pdf'
    
    # Supprimer le fichier temporaire après l'avoir envoyé
    os.remove(temp_path)
    
    return response

@semestre1_bp.route('/api/report/discipline', methods=['POST'])
def api_generate_discipline_report():
    """
    API pour générer un rapport de discipline.
    Paramètres:
    - discipline_id: ID de la discipline
    - niveau_id: (optionnel) ID du niveau
    - classe_id: (optionnel) ID de la classe
    """
    discipline_id = request.args.get('discipline_id')
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    
    if not discipline_id:
        return jsonify({'error': 'discipline_id est obligatoire'}), 400
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Construire la requête de base pour les notes
    query = db.session.query(NoteS1, Eleve).\
        join(Eleve, NoteS1.eleve_ien == Eleve.ien).\
        join(Classe, Eleve.classe_id == Classe.id).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active)
    
    # Appliquer les filtres
    if niveau_id:
        query = query.join(Classe, Eleve.classe_id == Classe.id).\
                filter(Classe.niveau_id == niveau_id)
    if classe_id:
        query = query.filter(Eleve.classe_id == classe_id)
    
    # Récupérer les données
    notes_eleves = query.all()
    
    if not notes_eleves:
        return jsonify({'error': 'Aucune donnée trouvée pour ces critères'}), 404
    
    # Calculer les statistiques globales
    notes = [n.moy_d for n, _ in notes_eleves if n.moy_d is not None]
    total_eleves = len(notes)
    
    if total_eleves == 0:
        return jsonify({'error': 'Aucune note valide trouvée pour ces critères'}), 404
    
    # Statistiques générales
    moyenne = sum(notes) / total_eleves
    min_note = min(notes)
    max_note = max(notes)
    
    # Utiliser pandas pour calculer la médiane et l'écart-type
    notes_series = pd.Series(notes)
    mediane = float(notes_series.median())
    ecart_type = float(notes_series.std())
    
    # Statistiques par sexe
    notes_garcons = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe in ('M', 'H')]
    notes_filles = [n.moy_d for n, e in notes_eleves if n.moy_d is not None and e.sexe == 'F']
    
    total_garcons = len(notes_garcons)
    total_filles = len(notes_filles)
    
    moyenne_garcons = sum(notes_garcons) / total_garcons if total_garcons > 0 else 0
    moyenne_filles = sum(notes_filles) / total_filles if total_filles > 0 else 0
    
    reussite_garcons = sum(1 for n in notes_garcons if n >= 10)
    reussite_filles = sum(1 for n in notes_filles if n >= 10)
    
    taux_reussite_global = sum(1 for n in notes if n >= 10) / total_eleves * 100
    taux_reussite_garcons = reussite_garcons / total_garcons * 100 if total_garcons > 0 else 0
    taux_reussite_filles = reussite_filles / total_filles * 100 if total_filles > 0 else 0
    
    pct_garcons = (total_garcons / total_eleves * 100) if total_eleves > 0 else 0
    pct_filles = (total_filles / total_eleves * 100) if total_filles > 0 else 0
    
    # Répartition par tranches de notes
    tranches = {
        'tres_bien': sum(1 for n in notes if n >= 16),
        'bien': sum(1 for n in notes if 14 <= n < 16),
        'assez_bien': sum(1 for n in notes if 12 <= n < 14),
        'passable': sum(1 for n in notes if 10 <= n < 12),
        'insuffisant': sum(1 for n in notes if n < 10)
    }
    
    # Récupérer la configuration de l'application
    config = Configuration.query.first()
    
    # Récupérer le niveau et la classe si spécifiés
    niveau = Niveau.query.get(niveau_id) if niveau_id else None
    classe = Classe.query.get(classe_id) if classe_id else None
    
    # Calculer la moyenne générale de l'établissement pour comparaison
    all_moyennes = db.session.query(NoteS1.moy_d).\
        filter(NoteS1.discipline_id == discipline_id, 
               NoteS1.annee_scolaire == annee_active,
               NoteS1.moy_d.isnot(None)).all()
    
    all_moyenne = sum([m.moy_d for m in all_moyennes]) / len(all_moyennes) if all_moyennes else 0
    difference_moyenne = moyenne - all_moyenne
    
    # Préparer les données de retour
    report_data = {
        'stats': {
            'total_eleves': total_eleves,
            'moyenne_generale': round(moyenne, 2),
            'eleves_moyenne': sum(1 for n in notes if n >= 10),
            'taux_reussite': round(taux_reussite_global, 2),
            'min': round(min_note, 2),
            'max': round(max_note, 2),
            'mediane': round(mediane, 2),
            'ecart_type': round(ecart_type, 2),
            'total_garcons': total_garcons,
            'total_filles': total_filles,
            'pct_garcons': round(pct_garcons, 2),
            'pct_filles': round(pct_filles, 2),
            'moyenne_garcons': round(moyenne_garcons, 2),
            'moyenne_filles': round(moyenne_filles, 2),
            'reussite_garcons': reussite_garcons,
            'reussite_filles': reussite_filles,
            'taux_reussite_garcons': round(taux_reussite_garcons, 2),
            'taux_reussite_filles': round(taux_reussite_filles, 2),
            'tranches': tranches,
            'moyenne_generale_etablissement': round(all_moyenne, 2),
            'difference_moyenne': round(difference_moyenne, 2)
        },
        'config': {
            'nom_etablissement': config.nom_etablissement if config else 'Établissement'
        },
        'filter': {
            'discipline': discipline.libelle,
            'niveau': niveau.libelle if niveau else None,
            'classe': classe.libelle if classe else None
        },
        'annee_scolaire': annee_active
    }
    
    # Enregistrer le rapport pour référence ultérieure
    import json
    import datetime
    
    now = datetime.datetime.now()
    rapport = Rapport(
        type='discipline',
        date_creation=now,
        contenu=json.dumps(report_data),
        discipline_id=discipline_id,
        niveau_id=niveau_id,
        classe_id=classe_id,
        annee_scolaire=annee_active
    )
    db.session.add(rapport)
    db.session.commit()
    
    # Ajouter l'ID du rapport aux données de retour
    report_data['rapport_id'] = rapport.id
    
    return jsonify(report_data)

@semestre1_bp.route('/api/disciplines')
def api_get_disciplines():
    """API pour récupérer toutes les disciplines"""
    disciplines = Discipline.query.order_by(Discipline.libelle).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/<int:classe_id>')
def api_get_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines d'une classe spécifique"""
    # Récupérer la classe pour déterminer le niveau
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à cette classe via l'année en cours
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).filter(
        Eleve.classe_id == classe_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])


@semestre1_bp.route('/api/disciplines/niveau/<int:niveau_id>')
def api_get_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines d'un niveau spécifique"""
    # Récupérer l'année active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Récupérer les disciplines à partir des notes existantes pour ce niveau
    disciplines = db.session.query(Discipline).join(
        NoteS1, NoteS1.discipline_id == Discipline.id
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).filter(
        Classe.niveau_id == niveau_id,
        NoteS1.annee_scolaire == annee_active
    ).distinct().order_by(Discipline.libelle).all()
    
    return jsonify([{
        'id': d.id, 
        'libelle': d.libelle,
        'code': d.code
    } for d in disciplines])

@semestre1_bp.route('/api/discipline_report')
def api_discipline_report_analysis():
    """API pour générer un rapport d'analyse par discipline"""
    # Récupérer les paramètres de la requête
    discipline_id = request.args.get('discipline_id', type=int)
    classe_id = request.args.get('classe_id', type=int)
    niveau_id = request.args.get('niveau_id', type=int)
    
    if not discipline_id:
        return jsonify({'error': 'Discipline non spécifiée'}), 400
    
    # Récupérer la discipline
    discipline = Discipline.query.get_or_404(discipline_id)
    
    # Récupérer l'année scolaire active
    annee_scolaire = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee_scolaire.libelle if annee_scolaire else '2024-2025'
    
    # Construire la requête de base
    query = db.session.query(
        NoteS1.valeur.label('note'),
        Eleve.sexe,
        Classe.id.label('classe_id'),
        Classe.libelle.label('classe_libelle'),
        Niveau.id.label('niveau_id'),
        Niveau.libelle.label('niveau_libelle')
    ).join(
        Eleve, NoteS1.eleve_ien == Eleve.ien
    ).join(
        Classe, Eleve.classe_id == Classe.id
    ).join(
        Niveau, Classe.niveau_id == Niveau.id
    ).filter(
        NoteS1.discipline_id == discipline_id,
        NoteS1.annee_scolaire == annee_active
    )
    
    # Filtrer par classe si spécifié
    if classe_id:
        query = query.filter(Classe.id == classe_id)
    
    # Filtrer par niveau si spécifié
    if niveau_id:
        query = query.filter(Niveau.id == niveau_id)
    
    # Exécuter la requête
    results = query.all()
    
    if not results:
        return jsonify({
            'discipline_id': discipline_id,
            'discipline_name': discipline.libelle,
            'niveau_id': niveau_id,
            'classe_id': classe_id,
            'results': [],
            'general_stats': {
                'average': 0,
                'highest': 0,
                'lowest': 0,
                'total_students': 0
            },
            'distribution': [0, 0, 0, 0, 0, 0, 0]  # Distribution vide
        })
    
    # Calculer les statistiques générales
    all_notes = [r.note for r in results]
    average = sum(all_notes) / len(all_notes)
    highest = max(all_notes)
    lowest = min(all_notes)
    total_students = len(all_notes)
    
    # Calculer la distribution des notes
    distribution = [0] * 7  # [0-5, 5-10, 10-12, 12-14, 14-16, 16-18, 18-20]
    for note in all_notes:
        if note < 5:
            distribution[0] += 1
        elif note < 10:
            distribution[1] += 1
        elif note < 12:
            distribution[2] += 1
        elif note < 14:
            distribution[3] += 1
        elif note < 16:
            distribution[4] += 1
        elif note < 18:
            distribution[5] += 1
        else:
            distribution[6] += 1
    
    # Regrouper les résultats par classe
    class_results = {}
    for r in results:
        class_id = r.classe_id
        if class_id not in class_results:
            class_results[class_id] = {
                'classe_id': class_id,
                'classe_name': r.classe_libelle,
                'notes': []
            }
        class_results[class_id]['notes'].append(r.note)
    
    # Calculer les statistiques par classe
    class_stats = []
    for class_id, data in class_results.items():
        notes = data['notes']
        class_stats.append({
            'classe_id': data['classe_id'],
            'classe_name': data['classe_name'],
            'average': sum(notes) / len(notes),
            'highest': max(notes),
            'lowest': min(notes),
            'student_count': len(notes)
        })
    
    # Trier les résultats par moyenne décroissante
    class_stats.sort(key=lambda x: x['average'], reverse=True)
    
    # Construire la réponse
    response = {
        'discipline_id': discipline_id,
        'discipline_name': discipline.libelle,
        'niveau_id': niveau_id,
        'classe_id': classe_id,
        'results': class_stats,
        'general_stats': {
            'average': average,
            'highest': highest,
            'lowest': lowest,
            'total_students': total_students
        },
        'distribution': distribution
    }
    
    return jsonify(response)

@semestre1_bp.route('/api/disciplines_by_niveau/<int:niveau_id>')
def api_disciplines_by_niveau(niveau_id):
    """API pour récupérer les disciplines par niveau"""
    disciplines = Discipline.query.filter_by(niveau_id=niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/api/disciplines_by_classe/<int:classe_id>')
def api_disciplines_by_classe(classe_id):
    """API pour récupérer les disciplines par classe"""
    # Récupérer le niveau associé à la classe
    classe = Classe.query.get_or_404(classe_id)
    
    # Récupérer les disciplines associées à ce niveau
    disciplines = Discipline.query.filter_by(niveau_id=classe.niveau_id).all()
    return jsonify([{
        'id': d.id,
        'libelle': d.libelle
    } for d in disciplines])

@semestre1_bp.route('/discipline_analysis')
@login_required
def discipline_analysis_admin():
    """Page for analyzing discipline statistics"""
    # Get all niveaux for filtering
    niveaux = Niveau.query.all()
    
    # Get all disciplines initially (will be filtered by JS)
    disciplines = Discipline.query.all()
    
    # Get current date for reporting
    current_date = datetime.datetime.now().strftime("%d/%m/%Y")
    
    return render_template(
        'semestre1/discipline_analysis.html',
        title='Analyse par Discipline',
        niveaux=niveaux,
        disciplines=disciplines,
        current_date=current_date
    )
