/**
 * Composant Liste des nœuds LoRa — Sidebar gauche.
 * Nomenclature : "LoRa nœud 1/2/3" — statut Déconnecté via Watchdog.
 * Fumée affichée en valeur brute x/4095 (MQ-2 analogique).
 */

const STATUS_LABELS = {
    normal:       '✓ Connecté',
    warning:      '⚠ Connecté',
    alert:        '🔥 Connecté',
    disconnected: '✕ Déconnecté',
    waiting:      '⏳ En attente',
};

/**
 * Mettre à jour la liste dans la sidebar.
 */
export function updateSensorList(sensors, onSelect) {
    const list = document.getElementById('sensor-list');
    if (!list) return;

    list.innerHTML = '';

    Object.entries(sensors).forEach(([sensorId, sensor]) => {
        const status = sensor.status || 'normal';
        const statusClass = `status-${status}`;
        const riskPct = sensor.risk != null ? (sensor.risk * 100).toFixed(1) : '--';
        const riskBadge = status === 'alert' ? 'alert'
            : status === 'warning' ? 'warning' : 'normal';
        const connLabel = STATUS_LABELS[status] || '–';

        // Ligne RSSI
        const rssiHtml = sensor.rssi != null
            ? `<span class="sensor-rssi">📶 ${sensor.rssi} dBm</span>`
            : `<span class="sensor-rssi" style="color:var(--text-muted)">📶 --</span>`;

        // Ligne fumée brute x/4095 (nœud MQ-2)
        const smokeHtml = sensor.smoke_level != null
            ? `<span>💨 ${sensor.smoke_level}/4095${sensor.smoke_trigger ? ' 🔥' : ''}</span>`
            : '';

        const item = document.createElement('div');
        item.className = `sensor-item ${statusClass}`;
        item.id = `card-${sensorId}`;
        item.innerHTML = `
            <div class="sensor-header">
                <span class="sensor-id">${sensor.name || sensorId}</span>
                <div class="sensor-status" id="dot-${sensorId}"></div>
            </div>
            <div class="sensor-info">
                <span style="color:var(--text-muted)">Zone: ${sensor.zone || '--'}</span>
                <span style="font-size:10px;">${connLabel}</span>
            </div>
            <div class="sensor-info">
                <span>🌡️ ${sensor.temperature != null ? sensor.temperature + '°C' : '--'}</span>
                <span>💧 ${sensor.humidity != null ? sensor.humidity + '%' : '--'}</span>
            </div>
            ${smokeHtml
                ? `<div class="sensor-info"><span>${smokeHtml}</span>${rssiHtml}</div>`
                : `<div class="sensor-info"><span></span>${rssiHtml}</div>`
            }
            <div class="sensor-info" style="margin-top:4px;">
                <span style="color:var(--text-muted);font-size:10px;">
                    ${sensor.last_seen ? '🕐 ' + new Date(sensor.last_seen).toLocaleTimeString('fr-CA') : ''}
                </span>
                <span class="risk-badge ${riskBadge}">Risque: ${riskPct}%</span>
            </div>
            <button class="btn-details">Voir détails</button>
        `;

        item.querySelector('.btn-details').addEventListener('click', (e) => {
            e.stopPropagation();
            if (onSelect) onSelect(sensorId);
        });
        item.addEventListener('click', () => { if (onSelect) onSelect(sensorId); });

        list.appendChild(item);
    });
}