document.addEventListener('DOMContentLoaded', function() {
    createCharts();
    setupFilters();
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

function createCharts() {
    const ctxConfig = [
        { id: 'moyennesNiveauChart', labelKey: 'niveau_stats', valueKey: 'moyenne', chartLabel: 'Moyenne générale', max: 20, bg: 'rgba(94, 53, 177, 0.7)', border: 'rgba(94, 53, 177, 1)' },
        { id: 'tauxReussiteChart', labelKey: 'niveau_stats', valueKey: 'taux_reussite', chartLabel: 'Taux de réussite (%)', max: 100, bg: 'rgba(46, 204, 113, 0.7)', border: 'rgba(46, 204, 113, 1)' }
    ];
    ctxConfig.forEach(cfg => {
        const canvas = document.getElementById(cfg.id);
        if (!canvas) return;
        const labels = canvas.getAttribute('data-labels') ? JSON.parse(canvas.getAttribute('data-labels')) : [];
        const values = canvas.getAttribute('data-values') ? JSON.parse(canvas.getAttribute('data-values')) : [];
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
        // Build URL from apiEndpoints
        const url = window.apiEndpoints.getClasses.replace('0', this.value);
        fetch(url).then(r => r.json()).then(data => {
            cls.innerHTML = '<option value="">Sélectionner</option>';
            data.forEach(item => cls.appendChild(Object.assign(document.createElement('option'), { value: item.id, textContent: item.libelle })));
            cls.disabled = false;
        }).catch(_ => { cls.innerHTML = '<option>Erreur</option>'; cls.disabled = false; });
    });
}

function setupClasseDisciplineSelects(classeId, disciplineId) {
    const cls = document.getElementById(classeId);
    const dis = document.getElementById(disciplineId);
    if (!cls || !dis) return;
    cls.addEventListener('change', function() {
        dis.disabled = true;
        dis.innerHTML = '<option>Chargement...</option>';
        // Build URL from apiEndpoints
        const url = window.apiEndpoints.getDisciplines.replace('0', this.value);
        fetch(url).then(r => r.json()).then(data => {
            dis.innerHTML = '<option value="">Sélectionner</option>';
            data.forEach(item => dis.appendChild(Object.assign(document.createElement('option'), { value: item.id, textContent: item.libelle })));
            dis.disabled = false;
        }).catch(_ => { dis.innerHTML = '<option>Erreur</option>'; dis.disabled = false; });
    });
}

function filtrerMoyennes() {
    const niv = document.getElementById('niveau').value;
    const cls = document.getElementById('classe').value;
    const sexe = document.getElementById('sexe').value;
    const noteMin = document.getElementById('note_min').value || 0;
    const noteMax = document.getElementById('note_max').value || 20;
    const container = document.getElementById('moyennesStats');
    if (!cls) {
        return container.innerHTML = `<div class="alert alert-warning"><i class="fas fa-exclamation-triangle me-2"></i>Veuillez sélectionner une classe</div>`;
    }
    container.innerHTML = `<div class="alert alert-info"><i class="fas fa-spinner fa-spin me-2"></i>Chargement...</div>`;
    const url = `${window.apiEndpoints.statsMoyennes}?niveau_id=${niv}&classe_id=${cls}&sexe=${sexe}&note_min=${noteMin}&note_max=${noteMax}`;
    console.log(`Fetching statsMoyennes from URL: ${url}`);
    fetch(url)
        .then(r => r.json())
        .then(data => {
            // Render updated bootstrap cards in container
            container.innerHTML = `
                <div class="row g-2">
                    <div class="col-6 col-xl-3">
                        <div class="card stat-card">
                            <div class="icon text-primary"><i class="fas fa-users"></i></div>
                            <div class="value">${data.total_eleves}</div>
                            <div class="label">Effectif total</div>
                        </div>
                    </div>
                    <div class="col-6 col-xl-3">
                        <div class="card stat-card">
                            <div class="icon text-success"><i class="fas fa-user-check"></i></div>
                            <div class="value">${data.eleves_moyenne}</div>
                            <div class="label">Élèves ≥10</div>
                        </div>
                    </div>
                    <div class="col-6 col-xl-3">
                        <div class="card stat-card">
                            <div class="icon text-info"><i class="fas fa-calculator"></i></div>
                            <div class="value">${data.moyenne_generale}</div>
                            <div class="label">Note Moyenne</div>
                        </div>
                    </div>
                    <div class="col-6 col-xl-3">
                        <div class="card stat-card">
                            <div class="icon text-warning"><i class="fas fa-chart-bar"></i></div>
                            <div class="value">Min ${data.min} / Max ${data.max}</div>
                            <div class="label">Extrêmes</div>
                        </div>
                    </div>
                </div>`;
            // Refresh charts with updated data
            createMoyennesCharts();
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
    if (!cid||!did) return container.innerHTML='<div class="alert alert-warning"><i class="fas fa-exclamation-triangle me-2"></i>Veuillez sélectionner</div>';
    container.innerHTML='<div class="alert alert-info"><i class="fas fa-spinner fa-spin me-2"></i>Chargement...</div>';
    const url = `${window.apiEndpoints.statsDiscipline}?classe_id=${cid}&discipline_id=${did}`;
    fetch(url)
        .then(r=>r.json()).then(data=>{
            container.innerHTML = `...`; // simplified
        }).catch(_=>container.innerHTML='<div class="alert alert-danger"><i class="fas fa-exclamation-circle me-2"></i>Erreur</div>');
}

// New: create charts for mentions and performance categories
function createMoyennesCharts() {
    // Fetch global stats for mentions and performance
    fetch(window.apiEndpoints.statsMoyennes)
        .then(response => response.json())
        .then(data => {
            // Mentions bar chart
            const mCtx = document.getElementById('mentionsChart');
            if (mCtx) {
                const labels = Object.keys(data.mention_counts);
                const values = Object.values(data.mention_counts);
                new Chart(mCtx, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Nombre d\'élèves',
                            data: values,
                            backgroundColor: 'rgba(52, 152, 219, 0.7)',
                            borderColor: 'rgba(52, 152, 219, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: { beginAtZero: true }
                        },
                        plugins: { legend: { display: false } }
                    }
                });
            }
            // Performance pie chart
            const pCtx = document.getElementById('performanceChart');
            if (pCtx) {
                const labels = Object.keys(data.performance_counts);
                const values = Object.values(data.performance_counts);
                new Chart(pCtx, {
                    type: 'pie',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: values,
                            backgroundColor: [
                                '#28a745','#17a2b8','#007bff','#ffc107','#dc3545'
                            ]
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { position: 'bottom' } }
                    }
                });
            }
        })
        .catch(err => console.error('Erreur chargement mentions/performance:', err));
}