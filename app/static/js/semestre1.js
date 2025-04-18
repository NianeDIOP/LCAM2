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
    if (!niv||!cls) return;
    niv.addEventListener('change', function() {
        cls.disabled = true;
        cls.innerHTML = '<option>Chargement...</option>';
        const url = `{{ url_for('semestre1.get_classes', niveau_id=0) }}`.replace('0', this.value);
        fetch(url).then(r=>r.json()).then(data=>{
            cls.innerHTML = '<option value="">Sélectionner</option>';
            data.forEach(item=>cls.appendChild(Object.assign(document.createElement('option'),{value:item.id,textContent:item.libelle})));
            cls.disabled = false;
        }).catch(_=>{cls.innerHTML='<option>Erreur</option>';cls.disabled=false;});
    });
}

function setupClasseDisciplineSelects(classeId, disciplineId) {
    const cls = document.getElementById(classeId);
    const dis = document.getElementById(disciplineId);
    if (!cls||!dis) return;
    cls.addEventListener('change', function() {
        dis.disabled = true;
        dis.innerHTML = '<option>Chargement...</option>';
        const url = `{{ url_for('semestre1.get_disciplines', classe_id=0) }}`.replace('0', this.value);
        fetch(url).then(r=>r.json()).then(data=>{
            dis.innerHTML = '<option value="">Sélectionner</option>';
            data.forEach(item=>dis.appendChild(Object.assign(document.createElement('option'),{value:item.id,textContent:item.libelle})));
            dis.disabled = false;
        }).catch(_=>{dis.innerHTML='<option>Erreur</option>';dis.disabled=false;});
    });
}

function filtrerMoyennes() {
    const cid = document.getElementById('classe').value;
    const container = document.getElementById('moyennesStats');
    if (!cid) return container.innerHTML='<div class="alert alert-warning"><i class="fas fa-exclamation-triangle me-2"></i>Veuillez sélectionner une classe</div>';
    container.innerHTML='<div class="alert alert-info"><i class="fas fa-spinner fa-spin me-2"></i>Chargement...</div>';
    fetch(`{{ url_for('semestre1.stats_moyennes') }}?classe_id=${cid}`)
        .then(r=>r.json()).then(data=>{
            container.innerHTML = `...`; // simplified for brevity
        }).catch(_=>container.innerHTML='<div class="alert alert-danger"><i class="fas fa-exclamation-circle me-2"></i>Erreur de chargement</div>');
}

function filtrerDisciplines() {
    const cid = document.getElementById('classeDiscipline').value;
    const did = document.getElementById('discipline').value;
    const container = document.getElementById('disciplinesStats');
    if (!cid||!did) return container.innerHTML='<div class="alert alert-warning"><i class="fas fa-exclamation-triangle me-2"></i>Veuillez sélectionner</div>';
    container.innerHTML='<div class="alert alert-info"><i class="fas fa-spinner fa-spin me-2"></i>Chargement...</div>';
    fetch(`{{ url_for('semestre1.stats_discipline') }}?classe_id=${cid}&discipline_id=${did}`)
        .then(r=>r.json()).then(data=>{
            container.innerHTML = `...`; // simplified
        }).catch(_=>container.innerHTML='<div class="alert alert-danger"><i class="fas fa-exclamation-circle me-2"></i>Erreur</div>');
}