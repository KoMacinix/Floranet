/**
 * Composant Liste des capteurs — Sidebar gauche.
 */

/**
 * Mettre à jour la liste des capteurs dans la sidebar.
 * @param {Object} sensors - Données des capteurs
 * @param {Function} onSelect - Callback quand un capteur est sélectionné
 */
export function updateSensorList(sensors, onSelect) {
    const list = document.getElementById('sensor-list');
    if (!list) return;

    list.innerHTML = '';

    Object.entries(sensors).forEach(([sensorId, sensor]) => {
        const statusClass = `status-${sensor.status || 'normal'}`;
        const riskPct = sensor.risk != null ? (sensor.risk * 100).toFixed(1) : '--';
        const riskBadge = sensor.status === 'alert' ? 'alert'
            : sensor.status === 'warning' ? 'warning' : 'normal';

        const item = document.createElement('div');
        item.className = `sensor-item ${statusClass}`;
        item.id = `card-${sensorId}`;
        item.innerHTML = `
            <div class="sensor-header">
                <span class="sensor-id">${sensor.name || sensorId}</span>
                <div class="sensor-status" id="dot-${sensorId}"></div>
            </div>
            <div class="sensor-info">
                <span>Zone: ${sensor.zone || '--'}</span>
                <span>${sensor.temperature != null ? '✓ Connecté' : '✗ En attente'}</span>
            </div>
            <div class="sensor-info">
                <span>🌡️ ${sensor.temperature != null ? sensor.temperature + '°C' : '--'}</span>
                <span>💧 ${sensor.humidity != null ? sensor.humidity + '%' : '--'}</span>
            </div>
            <div class="sensor-info">
                <span></span>
                <span class="risk-badge ${riskBadge}">Risque: ${riskPct}%</span>
            </div>
            <button class="btn-details">Voir détails</button>
        `;

        const btn = item.querySelector('.btn-details');
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (onSelect) onSelect(sensorId);
        });
        item.addEventListener('click', () => {
            if (onSelect) onSelect(sensorId);
        });

        list.appendChild(item);
    });
}
