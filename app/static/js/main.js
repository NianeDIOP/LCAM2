// Attendre que le document soit chargé
document.addEventListener('DOMContentLoaded', function() {
    // Activer les tooltips Bootstrap
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    if (tooltips.length > 0) {
        tooltips.forEach(tooltip => {
            new bootstrap.Tooltip(tooltip);
        });
    }
    
    // Activer les popovers Bootstrap
    const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
    if (popovers.length > 0) {
        popovers.forEach(popover => {
            new bootstrap.Popover(popover);
        });
    }
    
    // Navigation responsive
    const navbarToggler = document.querySelector('.navbar-toggler');
    if (navbarToggler) {
        navbarToggler.addEventListener('click', function() {
            // Ouvre/ferme le menu hamburger sans affecter la sidebar
            const navbarCollapse = document.querySelector('.navbar-collapse');
            if (navbarCollapse) {
                navbarCollapse.classList.toggle('show');
            }
        });
    }
    
    // Activer les liens de navigation actifs
    const currentLocation = window.location.pathname;
    
    // Pour les liens de la navbar
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && currentLocation.startsWith(href) && href !== '/') {
            link.classList.add('active');
        } else if (href === '/' && currentLocation === '/') {
            link.classList.add('active');
        }
    });
    
    // Pour les liens de la sidebar (si elle existe)
    const sidebarLinks = document.querySelectorAll('.sidebar .list-group-item');
    sidebarLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && (currentLocation.startsWith(href) || window.location.href.includes(href))) {
            link.classList.add('active');
        }
    });
    
    // Gestion de la sidebar responsive
    const sidebar = document.querySelector('.sidebar');
    
    // Créer un bouton pour afficher/masquer la sidebar en mobile si elle existe
    if (sidebar) {
        // Vérifier si le bouton toggle existe déjà
        let toggleButton = document.querySelector('.sidebar-toggle-btn');
        
        if (!toggleButton) {
            // Créer le bouton
            toggleButton = document.createElement('button');
            toggleButton.className = 'sidebar-toggle-btn';
            toggleButton.innerHTML = '<i class="fas fa-bars"></i>';
            document.body.appendChild(toggleButton);
            
            // Gérer l'affichage/masquage de la sidebar
            toggleButton.addEventListener('click', function() {
                sidebar.classList.toggle('show');
                document.body.classList.toggle('sidebar-open');
            });
        }
        
        // Fermer la sidebar quand on clique en dehors
        document.addEventListener('click', function(event) {
            const isClickInsideSidebar = sidebar.contains(event.target);
            const isClickOnToggleButton = toggleButton.contains(event.target);
            
            if (!isClickInsideSidebar && !isClickOnToggleButton && sidebar.classList.contains('show')) {
                sidebar.classList.remove('show');
                document.body.classList.remove('sidebar-open');
            }
        });
        
        // Ajouter une classe au body pour indiquer qu'il y a une sidebar
        document.body.classList.add('has-sidebar');
    }
    
    // Gestion des onglets
    const tabLinks = document.querySelectorAll('[data-bs-toggle="tab"]');
    tabLinks.forEach(link => {
        link.addEventListener('click', function(event) {
            event.preventDefault();
            
            const target = this.getAttribute('data-bs-target') || this.getAttribute('href');
            
            // Désactiver tous les onglets
            tabLinks.forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Masquer tous les contenus d'onglets
            const tabContents = document.querySelectorAll('.tab-pane');
            tabContents.forEach(content => {
                content.classList.remove('show', 'active');
            });
            
            // Activer l'onglet cliqué
            this.classList.add('active');
            
            // Afficher le contenu correspondant
            const targetContent = document.querySelector(target);
            if (targetContent) {
                targetContent.classList.add('show', 'active');
            }
            
            // Mettre à jour l'URL si nécessaire (pour les onglets dans les pages principales)
            if (target.startsWith('#tab-')) {
                const tabName = target.replace('#tab-', '');
                const url = new URL(window.location);
                url.searchParams.set('tab', tabName);
                window.history.pushState({}, '', url);
            }
        });
    });
    
    // Activer l'onglet à partir de l'URL si un paramètre 'tab' est présent
    const urlParams = new URLSearchParams(window.location.search);
    const tabParam = urlParams.get('tab');
    
    if (tabParam) {
        const tabToActivate = document.querySelector(`[data-bs-target="#tab-${tabParam}"], [href="#tab-${tabParam}"]`);
        if (tabToActivate) {
            tabToActivate.click();
        }
    }
    
    // Gestion des charts (s'ils existent)
    setupCharts();
    
    // Gestion des filtres dynamiques
    setupFilters();
    
    console.log('LCAMS application initialized');
});

// Fonction pour initialiser les graphiques
function setupCharts() {
    // Initialiser les charts seulement s'ils existent dans la page
    if (typeof Chart !== 'undefined') {
        // Pour les charts existants, assurez-vous qu'ils utilisent le thème
        Chart.defaults.color = '#6c757d';
        Chart.defaults.font.family = "'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif";
        
        // Moyennes par niveau (si le canvas existe)
        const moyennesNiveauCtx = document.getElementById('moyennesNiveauChart');
        if (moyennesNiveauCtx) {
            // Récupérer les données si disponibles dans des attributs data
            const labels = moyennesNiveauCtx.getAttribute('data-labels') ? 
                JSON.parse(moyennesNiveauCtx.getAttribute('data-labels')) : 
                ['6ème', '5ème', '4ème', '3ème'];
            
            const values = moyennesNiveauCtx.getAttribute('data-values') ? 
                JSON.parse(moyennesNiveauCtx.getAttribute('data-values')) : 
                [0, 0, 0, 0];
            
            // Créer le chart
            new Chart(moyennesNiveauCtx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Moyenne générale',
                        data: values,
                        backgroundColor: 'rgba(99, 102, 241, 0.7)',
                        borderColor: 'rgba(99, 102, 241, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 20
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    }
                }
            });
        }
        
        // Taux de réussite (si le canvas existe)
        const tauxReussiteCtx = document.getElementById('tauxReussiteChart');
        if (tauxReussiteCtx) {
            // Récupérer les données si disponibles
            const labels = tauxReussiteCtx.getAttribute('data-labels') ? 
                JSON.parse(tauxReussiteCtx.getAttribute('data-labels')) : 
                ['6ème', '5ème', '4ème', '3ème'];
            
            const values = tauxReussiteCtx.getAttribute('data-values') ? 
                JSON.parse(tauxReussiteCtx.getAttribute('data-values')) : 
                [0, 0, 0, 0];
            
            // Créer le chart
            new Chart(tauxReussiteCtx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Taux de réussite (%)',
                        data: values,
                        backgroundColor: 'rgba(46, 204, 113, 0.7)',
                        borderColor: 'rgba(46, 204, 113, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    }
                }
            });
        }
    }
}

// Fonction pour configurer les filtres dynamiques
function setupFilters() {
    // Gestion des sélects dépendants niveau/classe
    const niveauSelects = document.querySelectorAll('select[name="niveau_id"]');
    
    niveauSelects.forEach(niveauSelect => {
        if (niveauSelect) {
            // Trouver le select de classe associé (dans le même formulaire ou groupe)
            const parentForm = niveauSelect.closest('form') || niveauSelect.closest('.row') || niveauSelect.closest('.card-body');
            const classeSelect = parentForm ? parentForm.querySelector('select[name="classe_id"]') : null;
            
            if (classeSelect) {
                niveauSelect.addEventListener('change', function() {
                    const niveauId = this.value;
                    if (!niveauId) {
                        classeSelect.innerHTML = '<option value="">Sélectionner une classe</option>';
                        classeSelect.disabled = true;
                        return;
                    }
                    
                    classeSelect.disabled = true;
                    classeSelect.innerHTML = '<option value="">Chargement...</option>';
                    
                    // Chemin de l'endpoint pour récupérer les classes
                    // Note: Vous devrez ajuster l'URL en fonction de votre application
                    const url = `/semestre1/api/classes/${niveauId}`;
                    
                    // Requête AJAX pour récupérer les classes du niveau
                    fetch(url)
                        .then(response => response.json())
                        .then(data => {
                            classeSelect.innerHTML = '<option value="">Sélectionner une classe</option>';
                            
                            data.forEach(classe => {
                                const option = document.createElement('option');
                                option.value = classe.id;
                                option.textContent = classe.libelle;
                                classeSelect.appendChild(option);
                            });
                            
                            classeSelect.disabled = false;
                        })
                        .catch(error => {
                            console.error('Erreur lors du chargement des classes:', error);
                            classeSelect.innerHTML = '<option value="">Erreur de chargement</option>';
                            classeSelect.disabled = false;
                        });
                });
            }
        }
    });
    
    // Gestion des sélects dépendants classe/discipline
    const classeSelects = document.querySelectorAll('select[name="classe_id"]');
    
    classeSelects.forEach(classeSelect => {
        if (classeSelect) {
            // Trouver le select de discipline associé
            const parentForm = classeSelect.closest('form') || classeSelect.closest('.row') || classeSelect.closest('.card-body');
            const disciplineSelect = parentForm ? parentForm.querySelector('select[name="discipline_id"]') : null;
            
            if (disciplineSelect) {
                classeSelect.addEventListener('change', function() {
                    const classeId = this.value;
                    if (!classeId) {
                        disciplineSelect.innerHTML = '<option value="">Sélectionner une discipline</option>';
                        disciplineSelect.disabled = true;
                        return;
                    }
                    
                    disciplineSelect.disabled = true;
                    disciplineSelect.innerHTML = '<option value="">Chargement...</option>';
                    
                    // Chemin de l'endpoint pour récupérer les disciplines
                    const url = `/semestre1/api/disciplines/${classeId}`;
                    
                    // Requête AJAX pour récupérer les disciplines de la classe
                    fetch(url)
                        .then(response => response.json())
                        .then(data => {
                            disciplineSelect.innerHTML = '<option value="">Sélectionner une discipline</option>';
                            
                            data.forEach(discipline => {
                                const option = document.createElement('option');
                                option.value = discipline.id;
                                option.textContent = discipline.libelle;
                                disciplineSelect.appendChild(option);
                            });
                            
                            disciplineSelect.disabled = false;
                        })
                        .catch(error => {
                            console.error('Erreur lors du chargement des disciplines:', error);
                            disciplineSelect.innerHTML = '<option value="">Erreur de chargement</option>';
                            disciplineSelect.disabled = false;
                        });
                });
            }
        }
    });
}

// Fonction pour confirmer une action
function confirmAction(message) {
    return confirm(message || 'Êtes-vous sûr de vouloir effectuer cette action ?');
}

// Fonction pour formater les nombres
function formatNumber(number, decimals = 2) {
    if (isNaN(number)) return '0,00';
    return number.toFixed(decimals).replace('.', ',');
}

// Fonction pour montrer un chargement
function showLoading(element, message = 'Chargement...') {
    if (element) {
        element.innerHTML = `
            <div class="d-flex justify-content-center align-items-center p-4">
                <div class="spinner-border text-primary me-2" role="status">
                    <span class="visually-hidden">Chargement...</span>
                </div>
                <span>${message}</span>
            </div>
        `;
    }
}

// Fonction pour créer une notification de succès
function showSuccess(message, duration = 3000) {
    // Créer une alerte Bootstrap
    const alertEl = document.createElement('div');
    alertEl.className = 'alert alert-success alert-dismissible fade show position-fixed';
    alertEl.style.top = '20px';
    alertEl.style.right = '20px';
    alertEl.style.zIndex = '9999';
    alertEl.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
    alertEl.innerHTML = `
        <i class="fas fa-check-circle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Ajouter au document
    document.body.appendChild(alertEl);
    
    // Créer un Toast Bootstrap si disponible
    if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
        const toast = new bootstrap.Toast(alertEl, { delay: duration });
        toast.show();
    } else {
        // Fallback si Toast n'est pas disponible
        setTimeout(() => {
            alertEl.classList.remove('show');
            setTimeout(() => alertEl.remove(), 300);
        }, duration);
    }
}

// Fonction pour créer une notification d'erreur
function showError(message, duration = 5000) {
    // Créer une alerte Bootstrap
    const alertEl = document.createElement('div');
    alertEl.className = 'alert alert-danger alert-dismissible fade show position-fixed';
    alertEl.style.top = '20px';
    alertEl.style.right = '20px';
    alertEl.style.zIndex = '9999';
    alertEl.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
    alertEl.innerHTML = `
        <i class="fas fa-exclamation-circle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Ajouter au document
    document.body.appendChild(alertEl);
    
    // Créer un Toast Bootstrap si disponible
    if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
        const toast = new bootstrap.Toast(alertEl, { delay: duration });
        toast.show();
    } else {
        // Fallback si Toast n'est pas disponible
        setTimeout(() => {
            alertEl.classList.remove('show');
            setTimeout(() => alertEl.remove(), 300);
        }, duration);
    }
}