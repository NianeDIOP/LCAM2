from flask import Blueprint, render_template, current_app, jsonify, request, flash, redirect, url_for
from app.models.models import Niveau, Classe, Eleve, Discipline, NoteS1, MoyenneGeneraleS1, AnneeScolaire
from app import db
import pandas as pd
import os
from werkzeug.utils import secure_filename
import re
import datetime

semestre1_bp = Blueprint('semestre1', __name__)

@semestre1_bp.route('/')
def index():
    # Determine active tab from query parameter (overview, moyennes, disciplines, reports, import)
    active_tab = request.args.get('tab', 'overview')
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
                              'moyenne_generale': round(moyenne_generale, 2),
                              'eleves_moyenne': eleves_moyenne,
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
    niveau_id = request.args.get('niveau_id')
    classe_id = request.args.get('classe_id')
    # Récupérer l'année scolaire active
    annee = AnneeScolaire.query.filter_by(etat='actif').first()
    annee_active = annee.libelle if annee else '2024-2025'
    # Filtrer élèves de la classe
    query = db.session.query(MoyenneGeneraleS1).join(Eleve, MoyenneGeneraleS1.eleve_ien==Eleve.ien)
    if classe_id:
        query = query.filter(Eleve.classe_id==classe_id)
    query = query.filter(MoyenneGeneraleS1.annee_scolaire==annee_active)
    moys = query.with_entities(MoyenneGeneraleS1.moyenne)
    total = query.count()
    reussite = query.filter(MoyenneGeneraleS1.moyenne>=10).count()
    moyenne = round(sum([m.moyenne or 0 for m in moys]) / total,2) if total>0 else 0
    taux = round((reussite/total*100),2) if total>0 else 0
    return jsonify({
        'total_eleves': total,
        'moyenne_generale': moyenne,
        'eleves_moyenne': reussite,
        'taux_reussite': taux
    })

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
            
        # Extraction des colonnes Moy D
        colonnes_moy_d = [i for i, col in enumerate(sous_colonnes) if col == "Moy D"]
        df_detail_moy_d = df_detail.iloc[:, colonnes_moy_d]
        noms_moy_d = [disciplines[i] for i in colonnes_moy_d]
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
            
        # Pour chaque discipline
        for discipline_nom in df_detail_moy_d.columns:
            # Vérifier si la discipline existe
            discipline = Discipline.query.filter_by(libelle=discipline_nom).first()
                
            if not discipline:
                # Créer la discipline
                discipline = Discipline(
                    libelle=discipline_nom,
                    coefficient=1.0,
                    type='principale'
                )
                db.session.add(discipline)
                db.session.flush()  # Pour obtenir l'ID généré
                
            disciplines_ajoutees.add(discipline_nom)
                
            # Pour chaque élève, ajouter les notes de cette discipline
            for idx, row in df_final.iterrows():
                ien = str(row["IEN"])
                if pd.isna(ien) or ien == "" or pd.isna(row[discipline_nom]):
                    continue
                    
                # Trouver les valeurs Moy DD et Comp D si disponibles
                moy_dd = 0
                comp_d = 0
                    
                # Créer la note
                note = NoteS1(
                    eleve_ien=ien,
                    discipline_id=discipline.id,
                    moy_dd=moy_dd,
                    comp_d=comp_d,
                    moy_d=float(row[discipline_nom]) if not pd.isna(row[discipline_nom]) else 0,
                    rang_d=0,  # Rang non disponible dans les détails
                    annee_scolaire=annee_scolaire
                )
                db.session.add(note)
            
        db.session.commit()
            
        return {
            'success': True, 
            'message': f"Importation réussie: {eleves_ajoutes} élèves et {len(disciplines_ajoutees)} disciplines."
        }
            
    except Exception as e:
        db.session.rollback()
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
