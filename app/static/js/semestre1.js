/**
 * Scripts pour le module Semestre 1
 */

// Attendre que le document soit complètement chargé
document.addEventListener('DOMContentLoaded', function() {
    // Initialiser les fonctionnalités de la page
    initMoyennesAnalysis();
    initDisciplineAnalysis();
    initReportForms();
});

/**
 * Initialiser les fonctionnalités d'analyse des moyennes
 */
function initMoyennesAnalysis() {
    // Gestion de la sélection de niveau pour charger les classes correspondantes
    const niveauSelect = document.getElementById('niveau-select');
    const classeSelect = document.getElementById('classe-select');
    
    if (niveauSelect && classeSelect) {
        niveauSelect.addEventListener('change', function() {
            const niveauId = this.value;
            if (niveauId) {
                // Vider le select des classes
                classeSelect.innerHTML = '<option value="">Toutes les classes</option>';
                
                // Charger les classes du niveau sélectionné
                fetch(`/semestre1/api/classes/${niveauId}`)
                    .then(response => response.json())
                    .then(classes => {
                        // Ajouter les options de classes
                        classes.forEach(classe => {
                            const option = document.createElement('option');
                            option.value = classe.id;
                            option.textContent = classe.libelle;
                            classeSelect.appendChild(option);
                        });
                    })
                    .catch(error => {
                        console.error('Erreur lors du chargement des classes:', error);
                    });
            }
        });
    }
    
    // Gestion du graphique de répartition par mentions (si présent)
    const mentionsChartCanvas = document.getElementById('mentionsChart');
    if (mentionsChartCanvas) {
        const ctx = mentionsChartCanvas.getContext('2d');
        const mentionsLabels = JSON.parse(mentionsChartCanvas.dataset.labels || '[]');
        const mentionsData = JSON.parse(mentionsChartCanvas.dataset.values || '[]');
        
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: mentionsLabels,
                datasets: [{
                    data: mentionsData,
                    backgroundColor: [
                        '#4CAF50', // Félicitations
                        '#8BC34A', // Encouragements
                        '#CDDC39', // Tableau d'honneur
                        '#FFC107', // Passable
                        '#FF9800', // Doit redoubler d'effort
                        '#FF5722', // Avertissement
                        '#F44336'  // Blâme
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                    },
                    title: {
                        display: true,
                        text: 'Répartition par mentions'
                    }
                }
            }
        });
    }

    // Charger les statistiques dynamiquement lorsque les filtres changent
    const statsForm = document.getElementById('moyennes-filter-form');
    const statsContainer = document.getElementById('stats-container');
    
    if (statsForm && statsContainer) {
        statsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(statsForm);
            const params = new URLSearchParams();
            
            // Ajouter tous les champs du formulaire à l'URL
            for (const [key, value] of formData.entries()) {
                if (value) {
                    params.append(key, value);
                }
            }
            
            // Effectuer la requête AJAX pour récupérer les statistiques
            fetch(`/semestre1/api/stats/moyennes?${params.toString()}`)
                .then(response => response.json())
                .then(data => {
                    // Mettre à jour les statistiques affichées
                    document.getElementById('total-eleves').textContent = data.total_eleves;
                    document.getElementById('moyenne-generale').textContent = data.moyenne_generale;
                    document.getElementById('eleves-moyenne').textContent = data.eleves_moyenne;
                    document.getElementById('taux-reussite').textContent = data.taux_reussite + '%';
                    document.getElementById('min-moyenne').textContent = data.min;
                    document.getElementById('max-moyenne').textContent = data.max;
                    
                    // Mettre à jour les statistiques par sexe
                    document.getElementById('count-hommes').textContent = data.count_hommes;
                    document.getElementById('count-femmes').textContent = data.count_femmes;
                    document.getElementById('taux-hommes').textContent = data.taux_hommes + '%';
                    document.getElementById('taux-femmes').textContent = data.taux_femmes + '%';
                })
                .catch(error => {
                    console.error('Erreur lors de la récupération des statistiques:', error);
                });
        });
    }
}

/**
 * Initialiser les fonctionnalités d'analyse par discipline
 */
function initDisciplineAnalysis() {
    // Gestion de la sélection de niveau pour charger les classes correspondantes
    const niveauSelect = document.getElementById('discipline-niveau-select');
    const classeSelect = document.getElementById('discipline-classe-select');
    const disciplineSelect = document.getElementById('discipline-select');
    
    if (niveauSelect && classeSelect && disciplineSelect) {
        // Gestion du changement de niveau
        niveauSelect.addEventListener('change', function() {
            const niveauId = this.value;
            if (niveauId) {
                // Vider le select des classes
                classeSelect.innerHTML = '<option value="">Sélectionnez une classe</option>';
                
                // Charger les classes du niveau sélectionné
                fetch(`/semestre1/api/classes/${niveauId}`)
                    .then(response => response.json())
                    .then(classes => {
                        // Ajouter les options de classes
                        classes.forEach(classe => {
                            const option = document.createElement('option');
                            option.value = classe.id;
                            option.textContent = classe.libelle;
                            classeSelect.appendChild(option);
                        });
                        
                        // Activer le select des classes
                        classeSelect.disabled = false;
                    })
                    .catch(error => {
                        console.error('Erreur lors du chargement des classes:', error);
                    });
                
                // Vider et désactiver le select des disciplines
                disciplineSelect.innerHTML = '<option value="">Sélectionnez une discipline</option>';
                disciplineSelect.disabled = true;
                
                // Charger les disciplines disponibles pour le niveau sélectionné
                fetch(`/semestre1/api/disciplines/niveau/${niveauId}`)
                    .then(response => response.json())
                    .then(disciplines => {
                        // Ajouter les options de disciplines
                        disciplines.forEach(discipline => {
                            const option = document.createElement('option');
                            option.value = discipline.id;
                            option.textContent = discipline.libelle;
                            disciplineSelect.appendChild(option);
                        });
                        
                        // Activer le select des disciplines
                        disciplineSelect.disabled = false;
                    })
                    .catch(error => {
                        console.error('Erreur lors du chargement des disciplines par niveau:', error);
                    });
            }
        });
        
        // Gestion du changement de classe
        classeSelect.addEventListener('change', function() {
            const classeId = this.value;
            if (classeId) {
                // Vider le select des disciplines
                disciplineSelect.innerHTML = '<option value="">Sélectionnez une discipline</option>';
                
                // Charger les disciplines disponibles pour la classe sélectionnée
                fetch(`/semestre1/api/disciplines/${classeId}`)
                    .then(response => response.json())
                    .then(disciplines => {
                        // Ajouter les options de disciplines
                        disciplines.forEach(discipline => {
                            const option = document.createElement('option');
                            option.value = discipline.id;
                            option.textContent = discipline.libelle;
                            disciplineSelect.appendChild(option);
                        });
                        
                        // Activer le select des disciplines
                        disciplineSelect.disabled = false;
                    })
                    .catch(error => {
                        console.error('Erreur lors du chargement des disciplines:', error);
                    });
            }
        });
    }

    // Charger les statistiques de discipline dynamiquement
    const disciplineForm = document.getElementById('discipline-filter-form');
    const statsContainer = document.getElementById('discipline-stats-container');
    
    if (disciplineForm && statsContainer) {
        disciplineForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(disciplineForm);
            const params = new URLSearchParams();
            
            // Ajouter tous les champs du formulaire à l'URL
            for (const [key, value] of formData.entries()) {
                if (value) {
                    params.append(key, value);
                }
            }
            
            // Vérifier que la discipline est sélectionnée
            const disciplineId = formData.get('discipline_id');
            if (!disciplineId) {
                alert('Veuillez sélectionner une discipline.');
                return;
            }
            
            // Effectuer la requête AJAX pour récupérer les statistiques
            fetch(`/semestre1/api/stats/discipline?${params.toString()}`)
                .then(response => response.json())
                .then(data => {
                    // Mettre à jour les statistiques affichées
                    document.getElementById('discipline-nb-eleves').textContent = data.nb_eleves;
                    document.getElementById('discipline-moyenne').textContent = data.moyenne_discipline;
                    document.getElementById('discipline-nb-moyenne').textContent = data.nb_moyenne;
                    document.getElementById('discipline-taux-reussite').textContent = data.taux_reussite + '%';
                    document.getElementById('discipline-min').textContent = data.min;
                    document.getElementById('discipline-max').textContent = data.max;
                    
                    // Afficher le conteneur des statistiques
                    statsContainer.style.display = 'block';
                })
                .catch(error => {
                    console.error('Erreur lors de la récupération des statistiques de discipline:', error);
                });
        });
    }
}

/**
 * Initialiser les formulaires de génération de rapports
 */
function initReportForms() {
    // Formulaire de rapport moyennes
    const moyennesReportForm = document.getElementById('moyennes-report-form');
    if (moyennesReportForm) {
        const niveauSelect = moyennesReportForm.querySelector('#rapport-niveau-select');
        const classeSelect = moyennesReportForm.querySelector('#rapport-classe-select');
        
        // Gestion du changement de niveau pour charger les classes
        if (niveauSelect && classeSelect) {
            niveauSelect.addEventListener('change', function() {
                const niveauId = this.value;
                if (niveauId && niveauId !== 'all') {
                    // Vider le select des classes
                    classeSelect.innerHTML = '<option value="all">Toutes les classes</option>';
                    
                    // Charger les classes du niveau sélectionné
                    fetch(`/semestre1/api/classes/${niveauId}`)
                        .then(response => response.json())
                        .then(classes => {
                            // Ajouter les options de classes
                            classes.forEach(classe => {
                                const option = document.createElement('option');
                                option.value = classe.id;
                                option.textContent = classe.libelle;
                                classeSelect.appendChild(option);
                            });
                            
                            // Activer le select des classes
                            classeSelect.disabled = false;
                        })
                        .catch(error => {
                            console.error('Erreur lors du chargement des classes:', error);
                        });
                } else {
                    // Si "Tous les niveaux" est sélectionné, désactiver le select des classes
                    classeSelect.innerHTML = '<option value="all">Toutes les classes</option>';
                    classeSelect.disabled = true;
                }
            });
        }
        
        // Gestion de la soumission du formulaire de rapport moyennes
        moyennesReportForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(moyennesReportForm);
            const niveauId = formData.get('niveau_id');
            const classeId = formData.get('classe_id');
            const format = formData.get('format');
            
            // Préparer les données pour la requête
            const requestData = {
                type: 'moyennes',
                niveau_id: niveauId,
                classe_id: classeId,
                format: format
            };
            
            // Afficher indicateur de chargement
            const submitBtn = moyennesReportForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Génération en cours...';
            submitBtn.disabled = true;
            
            // Envoyer la requête pour générer le rapport
            fetch('/semestre1/api/report/moyennes-generales?' + new URLSearchParams({
                niveau_id: niveauId,
                classe_id: classeId
            }))
                .then(response => response.json())
                .then(data => {
                    // Restaurer le bouton
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                    
                    // Afficher le rapport généré
                    if (data.stats) {
                        displayMoyennesReport(data);
                    } else {
                        alert('Aucune donnée disponible pour ce rapport.');
                    }
                })
                .catch(error => {
                    console.error('Erreur lors de la génération du rapport:', error);
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                    alert('Une erreur est survenue lors de la génération du rapport.');
                });
        });
    }
    
    // Formulaire de rapport discipline
    const disciplineReportForm = document.getElementById('discipline-report-form');
    if (disciplineReportForm) {
        const niveauSelect = disciplineReportForm.querySelector('#rapport-discipline-niveau-select');
        const classeSelect = disciplineReportForm.querySelector('#rapport-discipline-classe-select');
        const disciplineSelect = disciplineReportForm.querySelector('#rapport-discipline-select');
        
        // Gestion du changement de niveau
        if (niveauSelect && classeSelect && disciplineSelect) {
            niveauSelect.addEventListener('change', function() {
                const niveauId = this.value;
                if (niveauId && niveauId !== 'all') {
                    // Vider le select des classes
                    classeSelect.innerHTML = '<option value="all">Toutes les classes</option>';
                    
                    // Charger les classes du niveau sélectionné
                    fetch(`/semestre1/api/classes/${niveauId}`)
                        .then(response => response.json())
                        .then(classes => {
                            // Ajouter les options de classes
                            classes.forEach(classe => {
                                const option = document.createElement('option');
                                option.value = classe.id;
                                option.textContent = classe.libelle;
                                classeSelect.appendChild(option);
                            });
                            
                            // Activer le select des classes
                            classeSelect.disabled = false;
                        })
                        .catch(error => {
                            console.error('Erreur lors du chargement des classes:', error);
                        });
                    
                    // Charger les disciplines pour le niveau sélectionné
                    fetch(`/semestre1/api/disciplines/niveau/${niveauId}`)
                        .then(response => response.json())
                        .then(disciplines => {
                            // Vider et remplir le select des disciplines
                            disciplineSelect.innerHTML = '<option value="">Sélectionnez une discipline</option>';
                            disciplines.forEach(discipline => {
                                const option = document.createElement('option');
                                option.value = discipline.id;
                                option.textContent = discipline.libelle;
                                disciplineSelect.appendChild(option);
                            });
                            
                            // Activer le select des disciplines
                            disciplineSelect.disabled = false;
                        })
                        .catch(error => {
                            console.error('Erreur lors du chargement des disciplines par niveau:', error);
                        });
                } else {
                    // Si "Tous les niveaux" est sélectionné
                    classeSelect.innerHTML = '<option value="all">Toutes les classes</option>';
                    classeSelect.disabled = true;
                    
                    // Charger toutes les disciplines disponibles
                    fetch('/semestre1/api/disciplines')
                        .then(response => response.json())
                        .then(disciplines => {
                            // Vider et remplir le select des disciplines
                            disciplineSelect.innerHTML = '<option value="">Sélectionnez une discipline</option>';
                            disciplines.forEach(discipline => {
                                const option = document.createElement('option');
                                option.value = discipline.id;
                                option.textContent = discipline.libelle;
                                disciplineSelect.appendChild(option);
                            });
                            
                            // Activer le select des disciplines
                            disciplineSelect.disabled = false;
                        })
                        .catch(error => {
                            console.error('Erreur lors du chargement des disciplines:', error);
                        });
                }
            });
            
            // Gestion du changement de classe
            classeSelect.addEventListener('change', function() {
                const classeId = this.value;
                if (classeId && classeId !== 'all') {
                    // Charger les disciplines pour la classe sélectionnée
                    fetch(`/semestre1/api/disciplines/${classeId}`)
                        .then(response => response.json())
                        .then(disciplines => {
                            // Vider et remplir le select des disciplines
                            disciplineSelect.innerHTML = '<option value="">Sélectionnez une discipline</option>';
                            disciplines.forEach(discipline => {
                                const option = document.createElement('option');
                                option.value = discipline.id;
                                option.textContent = discipline.libelle;
                                disciplineSelect.appendChild(option);
                            });
                            
                            // Activer le select des disciplines
                            disciplineSelect.disabled = false;
                        })
                        .catch(error => {
                            console.error('Erreur lors du chargement des disciplines:', error);
                        });
                } else if (niveauSelect.value && niveauSelect.value !== 'all') {
                    // Si "Toutes les classes" mais avec un niveau spécifique
                    fetch(`/semestre1/api/disciplines/niveau/${niveauSelect.value}`)
                        .then(response => response.json())
                        .then(disciplines => {
                            // Vider et remplir le select des disciplines
                            disciplineSelect.innerHTML = '<option value="">Sélectionnez une discipline</option>';
                            disciplines.forEach(discipline => {
                                const option = document.createElement('option');
                                option.value = discipline.id;
                                option.textContent = discipline.libelle;
                                disciplineSelect.appendChild(option);
                            });
                            
                            // Activer le select des disciplines
                            disciplineSelect.disabled = false;
                        })
                        .catch(error => {
                            console.error('Erreur lors du chargement des disciplines par niveau:', error);
                        });
                }
            });
        }
        
        // Gestion de la soumission du formulaire de rapport discipline
        disciplineReportForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(disciplineReportForm);
            const disciplineId = formData.get('discipline_id');
            const niveauId = formData.get('niveau_id');
            const classeId = formData.get('classe_id');
            const format = formData.get('format');
            
            // Vérifier que la discipline est sélectionnée
            if (!disciplineId) {
                alert('Veuillez sélectionner une discipline.');
                return;
            }
            
            // Afficher indicateur de chargement
            const submitBtn = disciplineReportForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Génération en cours...';
            submitBtn.disabled = true;
            
            // Préparer les paramètres de requête
            const params = new URLSearchParams({
                discipline_id: disciplineId
            });
            
            if (niveauId && niveauId !== 'all') {
                params.append('niveau_id', niveauId);
            }
            
            if (classeId && classeId !== 'all') {
                params.append('classe_id', classeId);
            }
            
            // Envoyer la requête pour générer le rapport
            fetch('/semestre1/api/report/discipline?' + params.toString())
                .then(response => response.json())
                .then(data => {
                    // Restaurer le bouton
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                    
                    // Afficher le rapport généré
                    if (data.stats) {
                        displayDisciplineReport(data);
                    } else {
                        alert('Aucune donnée disponible pour ce rapport.');
                    }
                })
                .catch(error => {
                    console.error('Erreur lors de la génération du rapport:', error);
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                    alert('Une erreur est survenue lors de la génération du rapport.');
                });
        });
    }
    
    // Gérer les boutons de téléchargement des rapports récents
    const recentReportsContainer = document.getElementById('recent-reports-container');
    if (recentReportsContainer) {
        recentReportsContainer.addEventListener('click', function(e) {
            if (e.target && e.target.classList.contains('download-report-btn')) {
                e.preventDefault();
                const reportId = e.target.dataset.reportId;
                const format = e.target.dataset.format || 'pdf';
                
                if (reportId) {
                    window.location.href = `/semestre1/api/download-report/${reportId}?format=${format}`;
                }
            }
            
            if (e.target && e.target.classList.contains('delete-report-btn')) {
                e.preventDefault();
                const reportId = e.target.dataset.reportId;
                
                if (reportId && confirm('Êtes-vous sûr de vouloir supprimer ce rapport ?')) {
                    fetch(`/semestre1/api/delete-report/${reportId}`, {
                        method: 'DELETE'
                    })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                // Supprimer l'élément du DOM
                                const reportRow = e.target.closest('tr');
                                if (reportRow) {
                                    reportRow.remove();
                                }
                            } else {
                                alert('Erreur lors de la suppression du rapport.');
                            }
                        })
                        .catch(error => {
                            console.error('Erreur lors de la suppression du rapport:', error);
                            alert('Une erreur est survenue lors de la suppression du rapport.');
                        });
                }
            }
        });
        
        // Charger la liste des rapports récents
        loadRecentReports();
    }
}

/**
 * Charger la liste des rapports récents
 */
function loadRecentReports() {
    const recentReportsContainer = document.getElementById('recent-reports-container');
    if (recentReportsContainer) {
        fetch('/semestre1/api/reports/recent')
            .then(response => response.json())
            .then(reports => {
                // Vider le tableau
                const tbody = recentReportsContainer.querySelector('tbody');
                if (!tbody) return;
                
                tbody.innerHTML = '';
                
                if (reports.length === 0) {
                    // Afficher un message si aucun rapport
                    const tr = document.createElement('tr');
                    tr.innerHTML = '<td colspan="5" class="text-center">Aucun rapport récent</td>';
                    tbody.appendChild(tr);
                } else {
                    // Afficher la liste des rapports
                    reports.forEach(report => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>${report.type_display}</td>
                            <td>${report.niveau}</td>
                            <td>${report.classe}</td>
                            <td>${report.date}</td>
                            <td class="text-end">
                                <button class="btn btn-sm btn-primary download-report-btn" data-report-id="${report.id}" data-format="pdf">
                                    <i class="fas fa-download"></i> PDF
                                </button>
                                <button class="btn btn-sm btn-success download-report-btn" data-report-id="${report.id}" data-format="excel">
                                    <i class="fas fa-file-excel"></i> Excel
                                </button>
                                <button class="btn btn-sm btn-danger delete-report-btn" data-report-id="${report.id}">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
            })
            .catch(error => {
                console.error('Erreur lors du chargement des rapports récents:', error);
                const tbody = recentReportsContainer.querySelector('tbody');
                if (tbody) {
                    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Erreur lors du chargement des rapports</td></tr>';
                }
            });
    }
}

/**
 * Afficher un rapport de moyennes générales
 */
function displayMoyennesReport(data) {
    // Récupérer le conteneur de rapport
    const reportContainer = document.getElementById('report-moyennes-container');
    if (!reportContainer) return;
    
    // Construire le contenu du rapport
    const stats = data.stats;
    const config = data.config;
    const filter = data.filter || {};
    
    // Construire le titre du rapport avec filtres
    let reportTitle = 'Rapport des Moyennes Générales';
    if (filter.niveau) {
        reportTitle += ` - ${filter.niveau}`;
    }
    if (filter.classe) {
        reportTitle += ` - ${filter.classe}`;
    }
    
    // Construire l'HTML du rapport
    const reportContent = `
        <div class="text-center mb-4">
            <h3 class="mb-0">${config.nom_etablissement || 'Établissement'}</h3>
            <h4>${reportTitle}</h4>
            <p class="text-muted">Année scolaire: ${data.annee_scolaire}</p>
        </div>
        <div class="row">
            <div class="col-md-6">
                <div class="card mb-3">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">Statistiques globales</h5>
                    </div>
                    <div class="card-body">
                        <table class="table table-sm table-striped">
                            <tr>
                                <th>Nombre total d'élèves</th>
                                <td>${stats.total_eleves}</td>
                            </tr>
                            <tr>
                                <th>Moyenne générale</th>
                                <td>${stats.moyenne_generale}</td>
                            </tr>
                            <tr>
                                <th>Élèves ayant la moyenne</th>
                                <td>${stats.eleves_moyenne} (${stats.taux_reussite}%)</td>
                            </tr>
                            <tr>
                                <th>Plus forte moyenne</th>
                                <td>${stats.plus_forte_moyenne}</td>
                            </tr>
                            <tr>
                                <th>Plus faible moyenne</th>
                                <td>${stats.plus_faible_moyenne}</td>
                            </tr>
                            <tr>
                                <th>Médiane</th>
                                <td>${stats.mediane}</td>
                            </tr>
                            <tr>
                                <th>Écart-type</th>
                                <td>${stats.ecart_type}</td>
                            </tr>
                        </table>
                    </div>
                </div>
                <div class="card mb-3">
                    <div class="card-header bg-info text-white">
                        <h5 class="mb-0">Statistiques par sexe</h5>
                    </div>
                    <div class="card-body">
                        <table class="table table-sm table-striped">
                            <thead>
                                <tr>
                                    <th></th>
                                    <th>Garçons</th>
                                    <th>Filles</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <th>Nombre</th>
                                    <td>${stats.total_garcons} (${stats.pct_garcons}%)</td>
                                    <td>${stats.total_filles} (${stats.pct_filles}%)</td>
                                </tr>
                                <tr>
                                    <th>Moyenne</th>
                                    <td>${stats.moyenne_garcons}</td>
                                    <td>${stats.moyenne_filles}</td>
                                </tr>
                                <tr>
                                    <th>Réussite</th>
                                    <td>${stats.reussite_garcons} (${stats.taux_reussite_garcons}%)</td>
                                    <td>${stats.reussite_filles} (${stats.taux_reussite_filles}%)</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card mb-3">
                    <div class="card-header bg-success text-white">
                        <h5 class="mb-0">Répartition par mentions</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="report-mentions-chart" height="200"></canvas>
                        <table class="table table-sm table-striped mt-3">
                            <tr>
                                <th>Félicitations</th>
                                <td>${stats.felicitations}</td>
                            </tr>
                            <tr>
                                <th>Encouragements</th>
                                <td>${stats.encouragements}</td>
                            </tr>
                            <tr>
                                <th>Tableau d'honneur</th>
                                <td>${stats.tableau_honneur}</td>
                            </tr>
                            <tr>
                                <th>Passable</th>
                                <td>${stats.passable}</td>
                            </tr>
                            <tr>
                                <th>Insuffisant</th>
                                <td>${stats.insuffisant}</td>
                            </tr>
                        </table>
                    </div>
                </div>
                <div class="card mb-3">
                    <div class="card-header bg-warning text-dark">
                        <h5 class="mb-0">Observations conseil</h5>
                    </div>
                    <div class="card-body">
                        <table class="table table-sm table-striped">
                            <tr>
                                <th>Satisfait, doit continuer</th>
                                <td>${stats.doit_continuer}</td>
                            </tr>
                            <tr>
                                <th>Peut mieux faire</th>
                                <td>${stats.mieux_faire}</td>
                            </tr>
                            <tr>
                                <th>Risque de redoubler</th>
                                <td>${stats.risque_redoubler}</td>
                            </tr>
                        </table>
                    </div>
                </div>
                <div class="d-flex justify-content-end">
                    <button class="btn btn-sm btn-primary" onclick="window.print()">
                        <i class="fas fa-print"></i> Imprimer ce rapport
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Mettre à jour le conteneur avec le contenu du rapport
    reportContainer.innerHTML = reportContent;
    reportContainer.style.display = 'block';
    
    // Initialiser le graphique de répartition par mentions
    const mentionsCtx = document.getElementById('report-mentions-chart').getContext('2d');
    new Chart(mentionsCtx, {
        type: 'pie',
        data: {
            labels: ['Félicitations', 'Encouragements', 'Tableau d\'honneur', 'Passable', 'Insuffisant'],
            datasets: [{
                data: [
                    stats.felicitations,
                    stats.encouragements,
                    stats.tableau_honneur,
                    stats.passable,
                    stats.insuffisant
                ],
                backgroundColor: [
                    '#4CAF50', // Félicitations
                    '#8BC34A', // Encouragements
                    '#CDDC39', // Tableau d'honneur
                    '#FFC107', // Passable
                    '#F44336'  // Insuffisant
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                }
            }
        }
    });
    
    // Faire défiler jusqu'au rapport
    reportContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Afficher un rapport de discipline
 */
function displayDisciplineReport(data) {
    // Récupérer le conteneur du dashboard
    const reportContainer = document.getElementById('report-discipline-container');
    if (!reportContainer) return;
    
    // Construire le contenu du rapport
    const stats = data.stats;
    const config = data.config;
    const filter = data.filter || {};
    
    // Construire le titre du rapport avec filtres
    let reportTitle = `Rapport de la discipline: ${filter.discipline}`;
    if (filter.niveau) {
        reportTitle += ` - ${filter.niveau}`;
    }
    if (filter.classe) {
        reportTitle += ` - ${filter.classe}`;
    }
    
    // Construire l'HTML du rapport
    const reportContent = `
        <div class="text-center mb-4 report-header">
            <h3 class="mb-0">${config.nom_etablissement || 'Établissement'}</h3>
            <h4>${reportTitle}</h4>
            <p class="text-muted">Année scolaire: ${data.annee_scolaire}</p>
        </div>
        <div class="row">
            <div class="col-md-6">
                <div class="card mb-3">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">Statistiques globales</h5>
                    </div>
                    <div class="card-body">
                        <table class="table table-sm table-striped">
                            <tr>
                                <th>Nombre total d'élèves</th>
                                <td>${stats.total_eleves}</td>
                            </tr>
                            <tr>
                                <th>Moyenne de la discipline</th>
                                <td>${stats.moyenne_generale}</td>
                            </tr>
                            <tr>
                                <th>Élèves ayant la moyenne</th>
                                <td>${stats.eleves_moyenne} (${stats.taux_reussite}%)</td>
                            </tr>
                            <tr>
                                <th>Note la plus forte</th>
                                <td>${stats.max}</td>
                            </tr>
                            <tr>
                                <th>Note la plus basse</th>
                                <td>${stats.min}</td>
                            </tr>
                            <tr>
                                <th>Médiane</th>
                                <td>${stats.mediane}</td>
                            </tr>
                            <tr>
                                <th>Écart-type</th>
                                <td>${stats.ecart_type}</td>
                            </tr>
                        </table>
                    </div>
                </div>
                <div class="card mb-3">
                    <div class="card-header bg-info text-white">
                        <h5 class="mb-0">Statistiques par sexe</h5>
                    </div>
                    <div class="card-body">
                        <table class="table table-sm table-striped">
                            <thead>
                                <tr>
                                    <th></th>
                                    <th>Garçons</th>
                                    <th>Filles</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <th>Nombre</th>
                                    <td>${stats.total_garcons} (${stats.pct_garcons}%)</td>
                                    <td>${stats.total_filles} (${stats.pct_filles}%)</td>
                                </tr>
                                <tr>
                                    <th>Moyenne</th>
                                    <td>${stats.moyenne_garcons}</td>
                                    <td>${stats.moyenne_filles}</td>
                                </tr>
                                <tr>
                                    <th>Réussite</th>
                                    <td>${stats.reussite_garcons} (${stats.taux_reussite_garcons}%)</td>
                                    <td>${stats.reussite_filles} (${stats.taux_reussite_filles}%)</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card mb-3">
                    <div class="card-header bg-success text-white">
                        <h5 class="mb-0">Répartition par tranches de notes</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="report-notes-chart" height="200"></canvas>
                        <div class="report-chart-data">
                            <table class="table table-sm table-striped mt-3">
                                <tr>
                                    <th>Très bien (16-20)</th>
                                    <td>${stats.tranches.tres_bien}</td>
                                </tr>
                                <tr>
                                    <th>Bien (14-16)</th>
                                    <td>${stats.tranches.bien}</td>
                                </tr>
                                <tr>
                                    <th>Assez bien (12-14)</th>
                                    <td>${stats.tranches.assez_bien}</td>
                                </tr>
                                <tr>
                                    <th>Passable (10-12)</th>
                                    <td>${stats.tranches.passable}</td>
                                </tr>
                                <tr>
                                    <th>Insuffisant (< 10)</th>
                                    <td>${stats.tranches.insuffisant}</td>
                                </tr>
                            </table>
                        </div>
                    </div>
                </div>
                <div class="card mb-3">
                    <div class="card-header bg-warning text-dark">
                        <h5 class="mb-0">Comparaison avec la moyenne générale</h5>
                    </div>
                    <div class="card-body">
                        <table class="table table-sm table-striped">
                            <tr>
                                <th>Moyenne générale de l'établissement</th>
                                <td>${stats.moyenne_generale_etablissement}</td>
                            </tr>
                            <tr>
                                <th>Différence</th>
                                <td class="${stats.difference_moyenne >= 0 ? 'text-success' : 'text-danger'}">
                                    ${stats.difference_moyenne >= 0 ? '+' : ''}${stats.difference_moyenne}
                                </td>
                            </tr>
                        </table>
                    </div>
                </div>
                <div class="d-flex justify-content-end">
                    <button class="btn btn-sm btn-primary print-report-btn" onclick="printDisciplineReport()">
                        <i class="fas fa-print"></i> Imprimer ce rapport
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Mettre à jour le conteneur avec le contenu du rapport
    reportContainer.innerHTML = reportContent;
    reportContainer.style.display = 'block';
    
    // Initialiser le graphique de répartition par notes
    const notesCtx = document.getElementById('report-notes-chart').getContext('2d');
    new Chart(notesCtx, {
        type: 'pie',
        data: {
            labels: ['Très bien (16-20)', 'Bien (14-16)', 'Assez bien (12-14)', 'Passable (10-12)', 'Insuffisant (< 10)'],
            datasets: [{
                data: [
                    stats.tranches.tres_bien,
                    stats.tranches.bien,
                    stats.tranches.assez_bien,
                    stats.tranches.passable,
                    stats.tranches.insuffisant
                ],
                backgroundColor: [
                    '#4CAF50', // Très bien
                    '#8BC34A', // Bien
                    '#CDDC39', // Assez bien
                    '#FFC107', // Passable
                    '#F44336'  // Insuffisant
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                }
            }
        }
    });
    
    // Préparer également le contenu pour l'impression
    const printPreviewContainer = document.getElementById('print-preview-container');
    if (printPreviewContainer) {
        printPreviewContainer.querySelector('#report-discipline-container').innerHTML = reportContent;
        
        // Réinitialiser le graphique dans le conteneur d'impression
        setTimeout(() => {
            if (printPreviewContainer.querySelector('#report-notes-chart')) {
                const printNotesCtx = printPreviewContainer.querySelector('#report-notes-chart').getContext('2d');
                new Chart(printNotesCtx, {
                    type: 'pie',
                    data: {
                        labels: ['Très bien (16-20)', 'Bien (14-16)', 'Assez bien (12-14)', 'Passable (10-12)', 'Insuffisant (< 10)'],
                        datasets: [{
                            data: [
                                stats.tranches.tres_bien,
                                stats.tranches.bien,
                                stats.tranches.assez_bien,
                                stats.tranches.passable,
                                stats.tranches.insuffisant
                            ],
                            backgroundColor: [
                                '#4CAF50', // Très bien
                                '#8BC34A', // Bien
                                '#CDDC39', // Assez bien
                                '#FFC107', // Passable
                                '#F44336'  // Insuffisant
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: false,
                        plugins: {
                            legend: {
                                position: 'right',
                            }
                        }
                    }
                });
            }
        }, 100);
    }
    
    // Faire défiler jusqu'au rapport
    reportContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Fonction spécifique pour l'impression du rapport de discipline
 */
function printDisciplineReport() {
    // Récupérer le contenu du rapport
    const reportContent = document.getElementById('reportContent');
    if (!reportContent) return;
    
    // Créer une nouvelle fenêtre pour l'impression
    const printWindow = window.open('', '_blank', 'width=1100,height=800');
    printWindow.document.write('<html><head><title>Rapport Discipline LCAMS</title>');
    
    // Inclure Chart.js pour les graphiques
    printWindow.document.write('<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>');
    
    // Style optimisé pour l'impression
    printWindow.document.write(`
    <style>
        @page { 
            size: A4; 
            margin: 10mm; 
        }
        body { 
            padding: 0; 
            margin: 0;
            font-family: Arial, sans-serif;
            font-size: 11pt;
            background-color: white;
            color: black;
        }
        .report-header {
            margin-bottom: 10mm;
            border-bottom: 1px solid #ccc;
            padding-bottom: 5mm;
            text-align: center;
        }
        .report-header h3 {
            font-size: 18pt;
            font-weight: bold;
            margin: 0 0 3mm 0;
        }
        .report-header h4 {
            font-size: 16pt;
            margin: 0 0 3mm 0;
        }
        .report-header p {
            font-size: 11pt;
            color: #666;
            margin: 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 5mm;
            page-break-inside: avoid;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 2mm 3mm;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        .row {
            display: flex;
            flex-wrap: wrap;
            margin: 0 -5mm;
            clear: both;
        }
        .col-md-6 {
            width: 48%;
            float: left;
            box-sizing: border-box;
            padding: 0 5mm;
            margin-bottom: 10mm;
        }
        .card {
            border: 1px solid #ddd;
            border-radius: 3mm;
            margin-bottom: 5mm;
            page-break-inside: avoid;
        }
        .card-header {
            background-color: #f2f2f2;
            padding: 3mm;
            border-bottom: 1px solid #ddd;
            font-weight: bold;
        }
        .card-body {
            padding: 3mm;
        }
        .bg-primary {
            background-color: #e6f2ff !important;
        }
        .bg-info {
            background-color: #e6f9ff !important;
        }
        .bg-success {
            background-color: #e6ffee !important;
        }
        .bg-warning {
            background-color: #fffce6 !important;
        }
        .text-white, .text-dark {
            color: #000 !important;
        }
        .text-center {
            text-align: center;
        }
        .mb-3 {
            margin-bottom: 3mm;
        }
        .mb-4 {
            margin-bottom: 5mm;
        }
        .chart-container {
            height: 70mm;
            margin: 3mm 0;
            page-break-inside: avoid;
        }
        .text-success {
            color: #28a745;
        }
        .text-danger {
            color: #dc3545;
        }
        canvas {
            max-height: 70mm;
            page-break-before: avoid;
            page-break-after: avoid;
        }
        .table-sm td, .table-sm th {
            padding: 1mm 2mm;
        }
        .table-striped tbody tr:nth-of-type(odd) {
            background-color: rgba(0, 0, 0, 0.03);
        }
        @media print {
            .no-print {
                display: none !important;
            }
            .page-break {
                page-break-before: always;
            }
            canvas {
                max-width: 100%;
            }
        }
    </style>
    `);
    
    printWindow.document.write('</head><body>');
    
    // Récupérer les données du rapport original
    const headerInfo = {
        etablissement: reportContent.querySelector('.text-center h3')?.textContent || 'Établissement',
        titre: reportContent.querySelector('.text-center h4')?.textContent || 'Rapport Discipline',
        anneeScolaire: reportContent.querySelector('.text-center .text-muted')?.textContent || '',
    };
    
    // Construction de l'en-tête du rapport
    printWindow.document.write(`
        <div class="report-header">
            <h3>${headerInfo.etablissement}</h3>
            <h4>${headerInfo.titre}</h4>
            <p>${headerInfo.anneeScolaire}</p>
        </div>
    `);
    
    // Copier le contenu principal du rapport
    const rowContent = reportContent.querySelector('.row')?.cloneNode(true);
    
    if (rowContent) {
        // Supprimer tous les boutons du contenu
        const buttons = rowContent.querySelectorAll('button');
        buttons.forEach(button => button.remove());
        
        // Ajouter le contenu à la fenêtre d'impression
        printWindow.document.write('<div class="row">');
        printWindow.document.write(rowContent.innerHTML);
        printWindow.document.write('</div>');
        
        // Extraire les données des graphiques du rapport original
        const notesChartEl = reportContent.querySelector('#report-notes-chart');
        if (notesChartEl) {
            // Récupérer les données du tableau dans le rapport
            const notesLabels = ['Très bien (16-20)', 'Bien (14-16)', 'Assez bien (12-14)', 'Passable (10-12)', 'Insuffisant (< 10)'];
            const notesData = [];
            
            // Récupérer les données du tableau
            const tableRows = reportContent.querySelectorAll('.card-body table tr');
            tableRows.forEach(row => {
                const label = row.querySelector('th')?.textContent;
                if (label && (
                    label.includes('Très bien') || 
                    label.includes('Bien') && !label.includes('Très') && !label.includes('Assez') || 
                    label.includes('Assez bien') || 
                    label.includes('Passable') || 
                    label.includes('Insuffisant')
                )) {
                    const value = parseInt(row.querySelector('td')?.textContent || '0', 10);
                    notesData.push(value);
                }
            });
            
            // Ajouter le script pour recréer le graphique dans la nouvelle fenêtre
            printWindow.document.write(`
                <script>
                document.addEventListener('DOMContentLoaded', function() {
                    // Attendre que le contenu soit chargé
                    setTimeout(function() {
                        try {
                            const notesChartEl = document.getElementById('report-notes-chart');
                            if (notesChartEl) {
                                const notesCtx = notesChartEl.getContext('2d');
                                new Chart(notesCtx, {
                                    type: 'pie',
                                    data: {
                                        labels: ${JSON.stringify(notesLabels)},
                                        datasets: [{
                                            data: ${JSON.stringify(notesData)},
                                            backgroundColor: [
                                                '#4CAF50', // Très bien
                                                '#8BC34A', // Bien
                                                '#CDDC39', // Assez bien
                                                '#FFC107', // Passable
                                                '#F44336'  // Insuffisant
                                            ],
                                            borderWidth: 1
                                        }]
                                    },
                                    options: {
                                        responsive: true,
                                        maintainAspectRatio: false,
                                        animation: false,
                                        plugins: {
                                            legend: {
                                                position: 'right',
                                                labels: {
                                                    font: {
                                                        size: 11
                                                    }
                                                }
                                            }
                                        }
                                    }
                                });
                                console.log("Graphique créé avec succès");
                            } else {
                                console.error("Élément canvas non trouvé");
                            }
                        } catch(e) {
                            console.error("Erreur lors de la création du graphique:", e);
                        }
                    }, 500);
                });
                </script>
            `);
        }
    } else {
        // Fallback si le contenu n'est pas trouvé
        printWindow.document.write('<div class="text-center">Erreur: Impossible de récupérer les données du rapport</div>');
    }
    
    // Fermer le document
    printWindow.document.write('</body></html>');
    printWindow.document.close();
    
    // Attendre que le contenu et les scripts soient chargés avant d'imprimer
    printWindow.onload = function() {
        setTimeout(() => {
            printWindow.focus();
            printWindow.print();
            // La fenêtre se fermera automatiquement après l'impression dans la plupart des navigateurs
            // ou restera ouverte si l'utilisateur annule l'impression
        }, 1000);
    };
}

document.addEventListener('DOMContentLoaded', function() {
    // Éléments du formulaire pour l'analyse des moyennes
    const niveauSelect = document.getElementById('niveau_id');
    const classeSelect = document.getElementById('classe_id');
    const disciplineSelect = document.getElementById('discipline_id');
    const generateButton = document.getElementById('generate-discipline-report');
    const reportContainer = document.getElementById('discipline-report-container');
    const loadingSpinner = document.getElementById('loading-spinner');

    // Mise à jour des classes lorsqu'un niveau est sélectionné
    if (niveauSelect) {
        niveauSelect.addEventListener('change', function() {
            const niveauId = this.value;
            
            // Réinitialiser les sélecteurs
            classeSelect.innerHTML = '<option value="">Sélectionner une classe</option>';
            disciplineSelect.innerHTML = '<option value="">Sélectionner une discipline</option>';
            
            if (niveauId) {
                // Charger les classes pour ce niveau
                fetch(`/api/classes/niveau/${niveauId}`)
                    .then(response => response.json())
                    .then(data => {
                        data.forEach(classe => {
                            const option = document.createElement('option');
                            option.value = classe.id;
                            option.textContent = classe.libelle;
                            classeSelect.appendChild(option);
                        });
                    })
                    .catch(error => console.error('Erreur:', error));
                
                // Charger les disciplines pour ce niveau
                fetch(`/api/disciplines/niveau/${niveauId}`)
                    .then(response => response.json())
                    .then(data => {
                        data.forEach(discipline => {
                            const option = document.createElement('option');
                            option.value = discipline.id;
                            option.textContent = discipline.libelle;
                            disciplineSelect.appendChild(option);
                        });
                    })
                    .catch(error => console.error('Erreur:', error));
            }
        });
    }

    // Mise à jour des disciplines lorsqu'une classe est sélectionnée
    if (classeSelect) {
        classeSelect.addEventListener('change', function() {
            const classeId = this.value;
            
            // Réinitialiser le sélecteur de disciplines
            disciplineSelect.innerHTML = '<option value="">Sélectionner une discipline</option>';
            
            if (classeId) {
                // Charger les disciplines pour cette classe
                fetch(`/api/disciplines/${classeId}`)
                    .then(response => response.json())
                    .then(data => {
                        data.forEach(discipline => {
                            const option = document.createElement('option');
                            option.value = discipline.id;
                            option.textContent = discipline.libelle;
                            disciplineSelect.appendChild(option);
                        });
                    })
                    .catch(error => console.error('Erreur:', error));
            }
        });
    }

    // Générer le rapport lorsque le bouton est cliqué
    if (generateButton) {
        generateButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Récupérer les valeurs sélectionnées
            const niveauId = niveauSelect?.value;
            const classeId = classeSelect?.value;
            const disciplineId = disciplineSelect?.value;
            
            // Valider les entrées
            if (!disciplineId) {
                alert('Veuillez sélectionner une discipline');
                return;
            }
            
            // Afficher l'indicateur de chargement
            if (loadingSpinner) {
                loadingSpinner.style.display = 'block';
            }
            
            // Construire les paramètres de la requête
            const params = new URLSearchParams();
            if (classeId) params.append('classe_id', classeId);
            if (niveauId) params.append('niveau_id', niveauId);
            params.append('discipline_id', disciplineId);
            
            // Envoyer la requête pour générer le rapport
            fetch(`/semestre1/api/discipline_report?${params.toString()}`)
                .then(response => response.json())
                .then(data => {
                    if (loadingSpinner) {
                        loadingSpinner.style.display = 'none';
                    }
                    
                    if (reportContainer) {
                        // Afficher le rapport
                        displayDisciplineReport(data, reportContainer);
                    }
                })
                .catch(error => {
                    console.error('Erreur:', error);
                    if (loadingSpinner) {
                        loadingSpinner.style.display = 'none';
                    }
                    alert('Une erreur est survenue lors de la génération du rapport.');
                });
        });
    }

    // Fonction pour afficher le rapport de discipline
    function displayDisciplineReport(data, container) {
        // Vider le conteneur
        container.innerHTML = '';
        
        if (!data || !data.results || data.results.length === 0) {
            container.innerHTML = '<div class="alert alert-info">Aucune donnée disponible pour cette sélection.</div>';
            return;
        }

        // Créer le container pour les statistiques générales
        const statsDiv = document.createElement('div');
        statsDiv.className = 'mb-4 p-3 bg-light rounded';
        
        const statsTitle = document.createElement('h4');
        statsTitle.textContent = `Statistiques pour ${data.discipline_name}`;
        statsDiv.appendChild(statsTitle);
        
        // Ajouter les statistiques générales
        const statsList = document.createElement('ul');
        statsList.className = 'list-group';
        
        const stats = [
            { label: 'Moyenne générale', value: data.general_stats.average.toFixed(2) },
            { label: 'Note la plus élevée', value: data.general_stats.highest.toFixed(2) },
            { label: 'Note la plus basse', value: data.general_stats.lowest.toFixed(2) },
            { label: 'Nombre d\'élèves', value: data.general_stats.total_students }
        ];
        
        stats.forEach(stat => {
            const item = document.createElement('li');
            item.className = 'list-group-item d-flex justify-content-between';
            item.innerHTML = `<span>${stat.label}:</span> <strong>${stat.value}</strong>`;
            statsList.appendChild(item);
        });
        
        statsDiv.appendChild(statsList);
        container.appendChild(statsDiv);
        
        // Créer le conteneur pour le graphique
        const chartDiv = document.createElement('div');
        chartDiv.className = 'mb-4';
        
        const chartCanvas = document.createElement('canvas');
        chartCanvas.id = 'disciplineDistributionChart';
        chartDiv.appendChild(chartCanvas);
        container.appendChild(chartDiv);
        
        // Créer le graphique de distribution des notes
        const ctx = chartCanvas.getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['0-5', '5-10', '10-12', '12-14', '14-16', '16-18', '18-20'],
                datasets: [{
                    label: 'Nombre d\'élèves',
                    data: data.distribution,
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.5)',
                        'rgba(255, 159, 64, 0.5)',
                        'rgba(255, 205, 86, 0.5)',
                        'rgba(75, 192, 192, 0.5)',
                        'rgba(54, 162, 235, 0.5)',
                        'rgba(153, 102, 255, 0.5)',
                        'rgba(201, 203, 207, 0.5)'
                    ],
                    borderColor: [
                        'rgb(255, 99, 132)',
                        'rgb(255, 159, 64)',
                        'rgb(255, 205, 86)',
                        'rgb(75, 192, 192)',
                        'rgb(54, 162, 235)',
                        'rgb(153, 102, 255)',
                        'rgb(201, 203, 207)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Nombre d\'élèves'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Plages de notes'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Distribution des notes'
                    },
                    legend: {
                        display: false
                    }
                }
            }
        });
        
        // Créer le tableau des résultats par classe
        if (data.results.length > 0) {
            const tableDiv = document.createElement('div');
            tableDiv.className = 'table-responsive mt-4';
            
            const table = document.createElement('table');
            table.className = 'table table-striped table-bordered';
            
            // En-tête du tableau
            const thead = document.createElement('thead');
            thead.className = 'table-dark';
            const headerRow = document.createElement('tr');
            
            const headers = ['Classe', 'Moyenne', 'Note max', 'Note min', 'Nombre d\'élèves'];
            headers.forEach(header => {
                const th = document.createElement('th');
                th.textContent = header;
                headerRow.appendChild(th);
            });
            
            thead.appendChild(headerRow);
            table.appendChild(thead);
            
            // Corps du tableau
            const tbody = document.createElement('tbody');
            
            data.results.forEach(result => {
                const row = document.createElement('tr');
                
                const classCell = document.createElement('td');
                classCell.textContent = result.classe_name;
                row.appendChild(classCell);
                
                const avgCell = document.createElement('td');
                avgCell.textContent = result.average.toFixed(2);
                row.appendChild(avgCell);
                
                const maxCell = document.createElement('td');
                maxCell.textContent = result.highest.toFixed(2);
                row.appendChild(maxCell);
                
                const minCell = document.createElement('td');
                minCell.textContent = result.lowest.toFixed(2);
                row.appendChild(minCell);
                
                const countCell = document.createElement('td');
                countCell.textContent = result.student_count;
                row.appendChild(countCell);
                
                tbody.appendChild(row);
            });
            
            table.appendChild(tbody);
            tableDiv.appendChild(table);
            container.appendChild(tableDiv);
        }
        
        // Ajouter le bouton de téléchargement du rapport
        const downloadBtn = document.createElement('button');
        downloadBtn.className = 'btn btn-primary mt-4';
        downloadBtn.textContent = 'Télécharger le rapport';
        downloadBtn.addEventListener('click', function() {
            const params = new URLSearchParams();
            params.append('discipline_id', data.discipline_id);
            if (data.niveau_id) params.append('niveau_id', data.niveau_id);
            if (data.classe_id) params.append('classe_id', data.classe_id);
            
            window.open(`/semestre1/discipline_report_download?${params.toString()}`, '_blank');
        });
        
        container.appendChild(downloadBtn);
    }
});