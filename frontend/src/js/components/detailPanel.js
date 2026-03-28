/**
 * Composant Détails — Sidebar droite (métriques d'un capteur sélectionné).
 */

/**
 * Afficher les détails d'un capteur dans le panneau de droite.
 * @param {Object} sensor - Données du capteur
 * @param {string} sensorId - ID du capteur
 */
export function showDetails(sensor, sensorId) {
    if (!sensor) return;

    const temp = sensor.temperature != null ? sensor.temperature : '--';
    const hum = sensor.humidity != null ? sensor.humidity : '--';
    const riskPct = sensor.risk != null ? (sensor.risk * 100).toFixed(1) : '--';

    // Nom et statut
    _setText('selected-name', `${sensor.name || sensorId} — ${sensor.zone || ''}`);

    const badge = document.getElementById('selected-status-badge');
    if (badge) {
        const statusText = sensor.status === 'alert' ? '🔥 ALERTE'
            : sensor.status === 'warning' ? '⚠ VIGILANCE' : '✓ NORMAL';
        badge.textContent = `● ${statusText}`;
        badge.className = `selected-status-badge ${sensor.status || 'normal'}`;
    }

    // Métriques
    _setText('detail-temp', `${temp}°C`);
    _setText('detail-humidity', `${hum}%`);
    _setText('detail-risk', `${riskPct}%`);

    // Barres de progression
    if (typeof temp === 'number') {
        _setBar('detail-temp-bar', Math.min(temp / 80 * 100, 100));
    }
    if (typeof hum === 'number') {
        _setBar('detail-humidity-bar', hum);
    }
    if (sensor.risk != null) {
        _setBar('detail-risk-bar', sensor.risk * 100);
    }

    // Compteurs globaux (calculés dans app.js et passés ici)
    // On ne les met à jour que si les éléments existent
}

/**
 * Mettre à jour les compteurs du résumé système.
 * @param {Object} sensors - Toutes les données capteurs
 */
export function updateSummary(sensors) {
    let normal = 0, warning = 0, alert = 0;

    Object.values(sensors).forEach((s) => {
        if (s.status === 'alert') alert++;
        else if (s.status === 'warning') warning++;
        else normal++;
    });

    _setText('count-normal', normal);
    _setText('count-warning', warning);
    _setText('count-alert', alert);
}


// ─── Helpers ────────────────────────────────────────────────────────────────

function _setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function _setBar(id, percent) {
    const el = document.getElementById(id);
    if (el) el.style.width = `${Math.max(0, Math.min(100, percent))}%`;
}
