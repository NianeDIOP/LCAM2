document.addEventListener('DOMContentLoaded', function() {
    createCharts();
    setupFilters();
    setupSidebarTabNavigation();
    setupImportHistoryPDFExport(); // Ajout de la nouvelle fonction pour l'historique d'importation
    createAppreciationsObservationsCharts(); // Ajout des graphiques appréciations et observations pour la page analyse des moyennes
    
    // Enable hash-based tab activation
    if (window.location.hash) {
        const hash = window.location.hash;
        const triggerEl = document.querySelector(`.sidebar .list-group-item[href="${hash}"]`);
        if (triggerEl) {
            const tab = new bootstrap.Tab(triggerEl);
            tab.show();
        }
    }
});

// Fonction pour configurer correctement l'activation des onglets via la sidebar
function setupSidebarTabNavigation() {
    // Sélectionner tous les liens de la sidebar avec data-bs-toggle="tab"
    const tabTriggerEls = document.querySelectorAll('.sidebar .list-group-item[data-bs-toggle="tab"]');
    
    tabTriggerEls.forEach(triggerEl => {
        triggerEl.addEventListener('click', function(event) {
            event.preventDefault();
            
            // Récupérer le target (id de l'onglet à afficher)
            const targetId = this.getAttribute('href');
            
            // Supprimer la classe active de tous les liens de la sidebar
            document.querySelectorAll('.sidebar .list-group-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // Ajouter la classe active à l'élément cliqué
            this.classList.add('active');
            
            // Masquer tous les onglets
            document.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.remove('show', 'active');
            });
            
            // Afficher l'onglet ciblé
            const targetPane = document.querySelector(targetId);
            if (targetPane) {
                targetPane.classList.add('show', 'active');
            }
            
            // Mettre à jour l'URL avec le hash
            history.pushState(null, null, targetId);
        });
    });
}

function createCharts() {
    const ctxConfig = [
        { id: 'moyennesNiveauChart', labelKey: 'niveau_stats', valueKey: 'moyenne', chartLabel: 'Moyenne générale', max: 20, bg: 'rgba(94, 53, 177, 0.7)', border: 'rgba(94, 53, 177, 1)' },
        { id: 'tauxReussiteChart', labelKey: 'niveau_stats', valueKey: 'taux_reussite', chartLabel: 'Taux de réussite (%)', max: 100, bg: 'rgba(46, 204, 113, 0.7)', border: 'rgba(46, 204, 113, 1)' }
    ];
    ctxConfig.forEach(cfg => {
        const canvas = document.getElementById(cfg.id);
        if (!canvas) return;
        const labelsRaw = canvas.getAttribute('data-labels');
        const valuesRaw = canvas.getAttribute('data-values');
        if (!labelsRaw || !valuesRaw || labelsRaw === '' || valuesRaw === '') return;
        let labels = [];
        let values = [];
        try {
            labels = JSON.parse(labelsRaw);
            values = JSON.parse(valuesRaw);
        } catch (e) {
            console.warn('Invalid JSON for chart', cfg.id, e);
            return;
        }
        new Chart(canvas, {
            type: 'bar',
            data: { labels: labels, datasets: [{ label: cfg.chartLabel, data: values, backgroundColor: cfg.bg, borderColor: cfg.border, borderWidth: 1 }] },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, max: cfg.max } }, plugins: { legend: { display: true, position: 'top' } } }
        });
    });
}

function setupFilters() {
    setupNiveauClasseSelects('niveau','classe');
    setupNiveauClasseSelects('niveauDiscipline','classeDiscipline');
    setupNiveauClasseSelects('niveau_id','classe_id');
    setupClasseDisciplineSelects('classeDiscipline','discipline');
    document.getElementById('btnFiltrerMoyennes')?.addEventListener('click', filtrerMoyennes);
    document.getElementById('btnFiltrerDisciplines')?.addEventListener('click', filtrerDisciplines);
}

function setupNiveauClasseSelects(niveauId, classeId) {
    const niv = document.getElementById(niveauId);
    const cls = document.getElementById(classeId);
    if (!niv || !cls) return;
    niv.addEventListener('change', function() {
        cls.disabled = true;
        cls.innerHTML = '<option>Chargement...</option>';
        
        if (!this.value) {
            cls.innerHTML = '<option value="">Sélectionner un niveau d\'abord</option>';
            cls.disabled = true;
            return;
        }
        
        // Construire l'URL directement sans utiliser replace
        const url = `/semestre1/api/classes/${this.value}`;
        console.log('Chargement des classes depuis:', url);
        
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Erreur HTTP: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                cls.innerHTML = '<option value="">Sélectionner une classe</option>';
                if (data && data.length > 0) {
                    data.forEach(item => cls.appendChild(Object.assign(document.createElement('option'), 
                        { value: item.id, textContent: item.libelle })));
                    cls.disabled = false;
                } else {
                    cls.innerHTML = '<option value="">Aucune classe disponible</option>';
                    cls.disabled = true;
                }
            })
            .catch(error => { 
                console.error('Erreur chargement classes:', error);
                cls.innerHTML = '<option>Erreur de chargement</option>'; 
                cls.disabled = false; 
            });
    });
}

function setupClasseDisciplineSelects(classeId, disciplineId) {
    const cls = document.getElementById(classeId);
    const dis = document.getElementById(disciplineId);
    if (!cls || !dis) return;
    cls.addEventListener('change', function() {
        dis.disabled = true;
        dis.innerHTML = '<option>Chargement...</option>';
        
        if (!this.value) {
            dis.innerHTML = '<option value="">Sélectionner une classe d\'abord</option>';
            dis.disabled = true;
            return;
        }
        
        // Construire l'URL directement sans utiliser replace
        const url = `/semestre1/api/disciplines/${this.value}`;
        console.log('Chargement des disciplines depuis:', url);
        
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Erreur HTTP: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                dis.innerHTML = '<option value="">Sélectionner une discipline</option>';
                if (data && data.length > 0) {
                    data.forEach(item => dis.appendChild(Object.assign(document.createElement('option'), 
                        { value: item.id, textContent: item.libelle })));
                    dis.disabled = false;
                } else {
                    dis.innerHTML = '<option value="">Aucune discipline disponible</option>';
                    dis.disabled = true;
                }
            })
            .catch(error => { 
                console.error('Erreur chargement disciplines:', error);
                dis.innerHTML = '<option>Erreur de chargement</option>'; 
                dis.disabled = false; 
            });
    });
}

function filtrerMoyennes() {
    const niv = document.getElementById('niveau').value;
    const cls = document.getElementById('classe').value;
    const sexe = document.getElementById('sexe').value;
    const noteMin = document.getElementById('note_min').value || 0;
    const noteMax = document.getElementById('note_max').value || 20;
    const container = document.getElementById('moyennesStats');
    if (!container) return;
    
    container.innerHTML = `<div class="alert alert-info"><i class="fas fa-spinner fa-spin me-2"></i>Chargement...</div>`;
    const url = `${window.apiEndpoints.statsMoyennes}?niveau_id=${niv}&classe_id=${cls}&sexe=${sexe}&note_min=${noteMin}&note_max=${noteMax}`;
    console.log(`Fetching statsMoyennes from URL: ${url}`);
    fetch(url)
        .then(r => r.json())
        .then(data => {
            // Render updated bootstrap cards in container
            container.innerHTML = `
                <div class="col-lg-3 col-md-6">
                    <div class="card stat-card">
                        <div class="icon text-primary"><i class="fas fa-users"></i></div>
                        <div class="value">${data.total_eleves}</div>
                        <div class="label">Effectif total</div>
                        <small class="text-muted">Hommes: ${data.count_hommes} (${data.taux_hommes}%)</small><br>
                        <small class="text-muted">Femmes: ${data.count_femmes} (${data.taux_femmes}%)</small>
                    </div>
                </div>
                <div class="col-lg-3 col-md-6">
                    <div class="card stat-card">
                        <div class="icon text-success"><i class="fas fa-user-check"></i></div>
                        <div class="value">${data.eleves_moyenne}</div>
                        <div class="label">Élèves ≥ 10</div>
                        <small class="text-muted">Hommes: ${data.reussite_hommes} (${data.taux_reussite_hommes}%)</small><br>
                        <small class="text-muted">Femmes: ${data.reussite_femmes} (${data.taux_reussite_femmes}%)</small>
                    </div>
                </div>
                <div class="col-lg-3 col-md-6">
                    <div class="card stat-card">
                        <div class="icon text-info"><i class="fas fa-calculator"></i></div>
                        <div class="value">${data.moyenne_generale}</div>
                        <div class="label">Moyenne générale</div>
                        <small class="text-muted">Min: ${data.min} / Max: ${data.max}</small>
                    </div>
                </div>
                <div class="col-lg-3 col-md-6">
                    <div class="card h-100">
                        <div class="card-body p-2 d-flex flex-column">
                            <canvas id="mentionsChart" class="flex-fill"></canvas>
                            <hr class="my-2">
                            <canvas id="performanceChart" class="flex-fill"></canvas>
                        </div>
                    </div>
                </div>
            `;
            // Refresh charts with updated data
            createMoyennesCharts(data);
        })
        .catch(error => {
            console.error('Erreur chargement moyennes:', error);
            container.innerHTML = `<div class="alert alert-danger"><i class="fas fa-exclamation-circle me-2"></i>Erreur lors du chargement des données.<br>URL: ${url}<br>Message: ${error.message}</div>`;
        });
}

function filtrerDisciplines() {
    const cid = document.getElementById('classeDiscipline').value;
    const did = document.getElementById('discipline').value;
    const container = document.getElementById('disciplinesStats');
    if (!container) return;
    
    if (!cid||!did) return container.innerHTML='<div class="alert alert-warning"><i class="fas fa-exclamation-triangle me-2"></i>Veuillez sélectionner</div>';
    container.innerHTML='<div class="alert alert-info"><i class="fas fa-spinner fa-spin me-2"></i>Chargement...</div>';
    const url = `${window.apiEndpoints.statsDiscipline}?classe_id=${cid}&discipline_id=${did}`;
    fetch(url)
        .then(r=>r.json()).then(data=>{
            container.innerHTML = `
                <div class="row">
                    <div class="col-md-2 mb-3">
                        <div class="stat-card">
                            <div class="icon text-primary mb-3">
                                <i class="fas fa-user-graduate fa-2x"></i>
                            </div>
                            <div class="value text-primary">${data.nb_eleves}</div>
                            <div class="label">Élèves</div>
                        </div>
                    </div>
                    <div class="col-md-2 mb-3">
                        <div class="stat-card">
                            <div class="icon text-info mb-3">
                                <i class="fas fa-calculator fa-2x"></i>
                            </div>
                            <div class="value text-info">${data.moyenne_discipline}</div>
                            <div class="label">Moyenne</div>
                        </div>
                    </div>
                    <div class="col-md-2 mb-3">
                        <div class="stat-card">
                            <div class="icon text-success mb-3">
                                <i class="fas fa-check-circle fa-2x"></i>
                            </div>
                            <div class="value text-success">${data.nb_moyenne}</div>
                            <div class="label">≥ 10</div>
                        </div>
                    </div>
                    <div class="col-md-2 mb-3">
                        <div class="stat-card">
                            <div class="icon text-warning mb-3">
                                <i class="fas fa-award fa-2x"></i>
                            </div>
                            <div class="value text-warning">${data.taux_reussite}%</div>
                            <div class="label">Taux</div>
                        </div>
                    </div>
                    <div class="col-md-2 mb-3">
                        <div class="stat-card">
                            <div class="icon text-danger mb-3">
                                <i class="fas fa-arrow-down fa-2x"></i>
                            </div>
                            <div class="value text-danger">${data.min}</div>
                            <div class="label">Min</div>
                        </div>
                    </div>
                    <div class="col-md-2 mb-3">
                        <div class="stat-card">
                            <div class="icon text-primary mb-3">
                                <i class="fas fa-arrow-up fa-2x"></i>
                            </div>
                            <div class="value text-primary">${data.max}</div>
                            <div class="label">Max</div>
                        </div>
                    </div>
                </div>
            `;
        }).catch(_=>container.innerHTML='<div class="alert alert-danger"><i class="fas fa-exclamation-circle me-2"></i>Erreur</div>');
}

// New: Function for import history PDF export
function setupImportHistoryPDFExport() {
    const exportButton = document.getElementById('btnExportImportHistoryPDF');
    
    if (!exportButton) return;
    
    exportButton.addEventListener('click', function() {
        const table = document.getElementById('tableImportHistory');
        
        if (!table) {
            console.error('Tableau d\'historique des importations non trouvé');
            return;
        }
        
        // Afficher une notification
        const notification = document.createElement('div');
        notification.classList.add('alert', 'alert-info', 'position-fixed', 'top-0', 'end-0', 'm-3');
        notification.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Génération du PDF en cours...';
        notification.style.zIndex = '9999';
        document.body.appendChild(notification);
        
        // Utiliser setTimeout pour permettre à l'UI de se mettre à jour
        setTimeout(() => {
            try {
                // Créer un nouveau document PDF A4
                const { jsPDF } = window.jspdf;
                const doc = new jsPDF('p', 'mm', 'a4');
                
                // Configurer le document
                const pageWidth = doc.internal.pageSize.getWidth();
                const pageHeight = doc.internal.pageSize.getHeight();
                const margin = 15;
                const contentWidth = pageWidth - 2 * margin;
                
                // Ajouter un en-tête
                const today = new Date();
                const dateStr = today.toLocaleDateString('fr-FR');
                
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(16);
                doc.text('LCAMS - Historique des Importations', pageWidth / 2, margin + 5, { align: 'center' });
                
                doc.setFont('helvetica', 'normal');
                doc.setFontSize(10);
                doc.text(`Généré le: ${dateStr}`, pageWidth - margin, margin + 10, { align: 'right' });
                
                // Extraire les données du tableau
                const headers = Array.from(table.querySelectorAll('thead th'))
                    .map(th => th.textContent.trim())
                    .filter(text => text !== 'Actions'); // Exclure la colonne Actions
                
                const rows = Array.from(table.querySelectorAll('tbody tr')).map(tr => {
                    const cells = Array.from(tr.querySelectorAll('td'));
                    // Ne prendre que les deux premières colonnes (Niveau et Classe)
                    return cells.slice(0, 2).map(td => td.textContent.trim());
                });
                
                // Calculer la hauteur des cellules et le nombre de lignes par page
                const cellHeight = 8;
                const headerHeight = 10;
                const tableStartY = margin + 20;
                const tableWidth = contentWidth;
                const columnWidths = [tableWidth * 0.5, tableWidth * 0.5]; // 50% pour chaque colonne
                
                // Définir la hauteur disponible pour le tableau sur la première page
                const firstPageTableSpace = pageHeight - tableStartY - margin;
                const rowsPerPage = Math.floor((pageHeight - tableStartY - margin) / cellHeight);
                
                // Générer l'en-tête du tableau
                let currentPage = 1;
                let y = tableStartY;
                
                // Fonction pour dessiner l'en-tête du tableau
                function drawTableHeader() {
                    doc.setFillColor(240, 240, 240);
                    doc.rect(margin, y, tableWidth, headerHeight, 'F');
                    
                    doc.setFont('helvetica', 'bold');
                    doc.setFontSize(10);
                    
                    let x = margin;
                    headers.forEach((header, i) => {
                        doc.text(header, x + columnWidths[i] / 2, y + headerHeight / 2, { align: 'center', baseline: 'middle' });
                        x += columnWidths[i];
                    });
                    
                    y += headerHeight;
                }
                
                // Dessiner l'en-tête du tableau sur la première page
                drawTableHeader();
                
                // Dessiner les lignes du tableau
                doc.setFont('helvetica', 'normal');
                
                rows.forEach((row, rowIndex) => {
                    // Vérifier si une nouvelle page est nécessaire
                    if (rowIndex > 0 && rowIndex % rowsPerPage === 0) {
                        // Ajouter une nouvelle page
                        doc.addPage();
                        currentPage++;
                        y = margin + 10; // Réinitialiser la position Y en haut de la page avec un petit espace
                        
                        // Ajouter l'en-tête de page
                        doc.setFont('helvetica', 'bold');
                        doc.setFontSize(14);
                        doc.text('LCAMS - Historique des Importations (suite)', pageWidth / 2, margin, { align: 'center' });
                        
                        doc.setFontSize(10);
                        doc.text(`Page ${currentPage}`, pageWidth - margin, margin, { align: 'right' });
                        
                        y += 10; // Espace après l'en-tête
                        
                        // Redessiner l'en-tête du tableau
                        drawTableHeader();
                    }
                    
                    // Dessiner la ligne du tableau
                    let x = margin;
                    let fillColor = rowIndex % 2 === 0 ? 255 : 245;
                    doc.setFillColor(fillColor, fillColor, fillColor);
                    doc.rect(margin, y, tableWidth, cellHeight, 'F');
                    
                    // Dessiner le contenu des cellules
                    doc.setFillColor(0);
                    row.forEach((cell, i) => {
                        // Tronquer si le texte est trop long
                        let cellText = cell;
                        const fontSize = 10;
                        doc.setFontSize(fontSize);
                        
                        if (doc.getTextWidth(cellText) > columnWidths[i] - 4) {
                            // Réduire le texte jusqu'à ce qu'il rentre
                            while (doc.getTextWidth(cellText + '...') > columnWidths[i] - 4 && cellText.length > 0) {
                                cellText = cellText.slice(0, -1);
                            }
                            cellText += '...';
                        }
                        
                        doc.text(cellText, x + columnWidths[i] / 2, y + cellHeight / 2, { align: 'center', baseline: 'middle' });
                        x += columnWidths[i];
                    });
                    
                    y += cellHeight;
                });
                
                // Ajouter le numéro de page en bas de chaque page
                const totalPages = Math.ceil(rows.length / rowsPerPage);
                
                for (let i = 0; i < totalPages; i++) {
                    doc.setPage(i + 1);
                    doc.setFont('helvetica', 'normal');
                    doc.setFontSize(8);
                    doc.text(`Page ${i + 1}/${totalPages}`, pageWidth / 2, pageHeight - 10, { align: 'center' });
                }
                
                // Enregistrer le PDF
                doc.save('historique_importations.pdf');
                
                // Supprimer la notification
                document.body.removeChild(notification);
                
                // Afficher confirmation
                const confirmNotif = document.createElement('div');
                confirmNotif.classList.add('alert', 'alert-success', 'position-fixed', 'top-0', 'end-0', 'm-3');
                confirmNotif.innerHTML = '<i class="fas fa-check me-2"></i>PDF généré avec succès';
                confirmNotif.style.zIndex = '9999';
                document.body.appendChild(confirmNotif);
                
                // Supprimer la notification après 3 secondes
                setTimeout(() => {
                    document.body.removeChild(confirmNotif);
                }, 3000);
                
            } catch (error) {
                console.error('Erreur lors de la génération du PDF:', error);
                document.body.removeChild(notification);
                
                const errorNotif = document.createElement('div');
                errorNotif.classList.add('alert', 'alert-danger', 'position-fixed', 'top-0', 'end-0', 'm-3');
                errorNotif.innerHTML = `<i class="fas fa-exclamation-circle me-2"></i>Erreur: ${error.message}`;
                errorNotif.style.zIndex = '9999';
                document.body.appendChild(errorNotif);
                
                setTimeout(() => {
                    document.body.removeChild(errorNotif);
                }, 5000);
            }
        }, 100);
    });
}

// New: create charts for mentions and performance categories
function createMoyennesCharts(data = null) {
    if (!data) {
        // If no data provided, fetch global stats
        fetch(window.apiEndpoints.statsMoyennes)
            .then(response => response.json())
            .then(data => {
                createMentionsChart(data);
                createPerformanceChart(data);
            })
            .catch(err => console.error('Erreur chargement mentions/performance:', err));
    } else {
        // Use provided data
        createMentionsChart(data);
        createPerformanceChart(data);
    }
}

function createMentionsChart(data) {
    const mCtx = document.getElementById('mentionsChart');
    if (!mCtx) return;
    
    // Clear any existing charts on this canvas
    if (Chart.getChart(mCtx)) {
        Chart.getChart(mCtx).destroy();
    }
    
    const labels = Object.keys(data.mention_counts);
    const values = Object.values(data.mention_counts);
    
    new Chart(mCtx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Nombre d\'élèves',
                data: values,
                backgroundColor: [
                    'rgba(52, 152, 219, 0.7)',
                    'rgba(46, 204, 113, 0.7)',
                    'rgba(155, 89, 182, 0.7)',
                    'rgba(241, 196, 15, 0.7)',
                    'rgba(231, 76, 60, 0.7)'
                ],
                borderColor: [
                    'rgba(52, 152, 219, 1)',
                    'rgba(46, 204, 113, 1)',
                    'rgba(155, 89, 182, 1)',
                    'rgba(241, 196, 15, 1)',
                    'rgba(231, 76, 60, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true }
            },
            plugins: {
                legend: { display: false },
                title: {
                    display: true,
                    text: 'Répartition par mention',
                    font: { size: 10 }
                }
            }
        }
    });
}

function createPerformanceChart(data) {
    const pCtx = document.getElementById('performanceChart');
    if (!pCtx) return;
    
    // Clear any existing charts on this canvas
    if (Chart.getChart(pCtx)) {
        Chart.getChart(pCtx).destroy();
    }
    
    const labels = Object.keys(data.performance_counts);
    const values = Object.values(data.performance_counts);
    
    new Chart(pCtx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    '#28a745',   // Excellent - Vert
                    '#17a2b8',   // Satisfait - Bleu clair 
                    '#007bff',   // Peut mieux faire - Bleu
                    '#ffc107',   // Risque redoublement - Jaune
                    '#dc3545'    // Risque exclusion - Rouge
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { 
                    position: 'right',
                    labels: {
                        font: { size: 9 }
                    }
                },
                title: {
                    display: true,
                    text: 'Catégories de performance',
                    font: { size: 10 }
                }
            }
        }
    });
}

// Ajout des graphiques appréciations et observations pour la page analyse des moyennes
function createAppreciationsObservationsCharts() {
    // Barres appréciations
    const apprCanvas = document.getElementById('appreciationsBarChart');
    if (apprCanvas) {
        const labelsRaw = apprCanvas.getAttribute('data-labels');
        const valuesRaw = apprCanvas.getAttribute('data-values');
        if (labelsRaw && valuesRaw && labelsRaw !== '' && valuesRaw !== '') {
            const labels = JSON.parse(labelsRaw);
            const values = JSON.parse(valuesRaw);
            if (Chart.getChart(apprCanvas)) Chart.getChart(apprCanvas).destroy();
            new Chart(apprCanvas, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: "Nombre d'élèves",
                        data: values,
                        backgroundColor: [
                            '#1976d2', '#388e3c', '#7b1fa2', '#fbc02d', '#ffa726', '#ff7043', '#c62828'
                        ],
                        borderColor: [
                            '#1565c0', '#2e7d32', '#6a1b9a', '#f9a825', '#fb8c00', '#d84315', '#b71c1c'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        title: {
                            display: true,
                            text: 'Répartition des appréciations',
                            font: { size: 12 }
                        }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }
    }
    // Camembert observations
    const obsCanvas = document.getElementById('observationsPieChart');
    if (obsCanvas) {
        const labelsRaw = obsCanvas.getAttribute('data-labels');
        const valuesRaw = obsCanvas.getAttribute('data-values');
        if (labelsRaw && valuesRaw && labelsRaw !== '' && valuesRaw !== '') {
            const labels = JSON.parse(labelsRaw);
            const values = JSON.parse(valuesRaw);
            if (Chart.getChart(obsCanvas)) Chart.getChart(obsCanvas).destroy();
            new Chart(obsCanvas, {
                type: 'pie',
                data: {
                    labels: labels,
                    datasets: [{
                        data: values,
                        backgroundColor: [
                            '#388e3c', '#1976d2', '#fbc02d', '#ffa726', '#c62828', '#6d4c41'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { font: { size: 11 } } },
                        title: {
                            display: true,
                            text: 'Répartition des observations',
                            font: { size: 12 }
                        }
                    }
                }
            });
        }
    }
}