/**
 * Composant Détails — Sidebar droite.
 * Affiche température, humidité, fumée (MQ-2 brut 0–4095), RSSI, risque IA.
 */

export function showDetails(sensor, sensorId) {
    if (!sensor) return;

    const temp   = sensor.temperature;
    const hum    = sensor.humidity;
    const smoke  = sensor.smoke_level;
    const rssi   = sensor.rssi;
    const risk   = sensor.risk;
    const status = sensor.status || 'normal';

    // Nom + statut
    _setText('selected-name', `${sensor.name || sensorId} — ${sensor.zone || ''}`);

    const badge = document.getElementById('selected-status-badge');
    if (badge) {
        const labels = {
            normal:       '✓ NORMAL',
            warning:      '⚠ VIGILANCE',
            alert:        '🔥 ALERTE',
            disconnected: '✕ DÉCONNECTÉ',
            waiting:      '⏳ EN ATTENTE',
        };
        badge.textContent = `● ${labels[status] || status.toUpperCase()}`;
        badge.className = `selected-status-badge ${status}`;
    }

    // RSSI
    const rssiEl = document.getElementById('rssi-value');
    if (rssiEl) rssiEl.textContent = rssi != null ? rssi : '--';

    // Température — barre sur 0–80°C max
    _setText('detail-temp', temp != null ? `${temp}°C` : '--°C');
    if (temp != null) _setBar('detail-temp-bar', Math.min(temp / 80 * 100, 100));

    // Humidité — barre directement en %
    _setText('detail-humidity', hum != null ? `${hum}%` : '--%');
    if (hum != null) _setBar('detail-humidity-bar', hum);

    // Fumée (MQ-2) — valeur brute 0–4095
    _setText('detail-smoke', smoke != null ? `${smoke} / 4095` : '-- / 4095');
    if (smoke != null) _setBar('detail-smoke-bar', Math.min(smoke / 4095 * 100, 100));

    // Badge fumée déclenché
    const smokeTrigBadge = document.getElementById('smoke-trigger-badge');
    if (smokeTrigBadge) {
        smokeTrigBadge.style.display = sensor.smoke_trigger ? 'inline-block' : 'none';
    }

    // Risque IA — valeur entre 0 et 1, affichée en %
    const riskPct = risk != null ? (risk * 100).toFixed(1) : '--';
    _setText('detail-risk', `${riskPct}%`);
    if (risk != null) _setBar('detail-risk-bar', risk * 100);
}

export function updateSummary(sensors) {
    let normal = 0, warning = 0, alert = 0, disconnected = 0;

    Object.values(sensors).forEach((s) => {
        if      (s.status === 'alert')        alert++;
        else if (s.status === 'warning')      warning++;
        else if (s.status === 'disconnected') disconnected++;
        else                                  normal++;
    });

    _setText('count-normal',       normal);
    _setText('count-warning',      warning);
    _setText('count-alert',        alert);
    _setText('count-disconnected', disconnected);
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function _setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function _setBar(id, percent) {
    const el = document.getElementById(id);
    if (el) el.style.width = `${Math.max(0, Math.min(100, percent))}%`;
}