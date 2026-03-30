/**
 * Composant Carte — Leaflet avec fond OpenStreetMap (compatible HTTP local).
 * Cercles de nœuds colorés selon seuils (Vert/Jaune/Rouge).
 * Icône Passerelle (Gateway) distincte.
 */

let map;
const markers = {};
let gatewayMarker = null;

// ─── Seuils de couleur ────────────────────────────────────────────────────────
// temp_warning: 40°C (risque), temp_critical: 50°C (alerte)
// smoke sur échelle brute 0–4095
const THRESHOLDS = {
    temp_warning:    40,  temp_critical:    50,
    hum_warning:     55,  hum_critical:     13,
    smoke_warning:  300,  smoke_critical:  700,
    risk_warning:   0.3,  risk_critical:   0.7,
};

// ─── Coordonnées de la passerelle ────────────────────────────────────────────
const GATEWAY_POS = [45.515, -73.575];

/**
 * Calculer la couleur d'un nœud selon ses données et le statut.
 */
function _nodeColor(sensor) {
    const status = sensor.status;
    if (status === 'disconnected') return { fill: '#6b7896', border: '#8899bb', glow: null };
    if (status === 'waiting')      return { fill: '#5e6a80', border: '#7a8aa0', glow: null };

    // Critique → Rouge
    if (
        status === 'alert' ||
        (sensor.temperature != null && sensor.temperature >= THRESHOLDS.temp_critical) ||
        (sensor.humidity    != null && sensor.humidity    <= THRESHOLDS.hum_critical)  ||
        (sensor.smoke_level != null && sensor.smoke_level >= THRESHOLDS.smoke_critical)||
        sensor.smoke_trigger
    ) {
        return { fill: '#e74c3c', border: '#ff6b6b', glow: 'rgba(231,76,60,0.5)' };
    }

    // Moyen → Jaune
    if (
        status === 'warning' ||
        (sensor.temperature != null && sensor.temperature >= THRESHOLDS.temp_warning) ||
        (sensor.humidity    != null && sensor.humidity    <= THRESHOLDS.hum_warning)  ||
        (sensor.smoke_level != null && sensor.smoke_level >= THRESHOLDS.smoke_warning)
    ) {
        return { fill: '#f0b429', border: '#ffd166', glow: 'rgba(240,180,41,0.45)' };
    }

    // Normal → Vert
    return { fill: '#2ecc71', border: '#55efc4', glow: 'rgba(46,204,113,0.4)' };
}

/**
 * Créer l'icône SVG d'un nœud LoRa.
 */
function _makeNodeIcon(sensor) {
    const c = _nodeColor(sensor);
    const isAlert = sensor.status === 'alert' || sensor.smoke_trigger;
    const glowStyle = c.glow ? `filter:drop-shadow(0 0 8px ${c.glow});` : '';
    const pulse = isAlert
        ? `<circle cx="18" cy="18" r="17" fill="none" stroke="${c.fill}" stroke-width="2" opacity="0.4">
             <animate attributeName="r" from="17" to="26" dur="1.2s" repeatCount="indefinite"/>
             <animate attributeName="opacity" from="0.5" to="0" dur="1.2s" repeatCount="indefinite"/>
           </circle>` : '';

    return L.divIcon({
        html: `<svg width="36" height="36" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg" style="${glowStyle}">
            ${pulse}
            <circle cx="18" cy="18" r="14" fill="${c.fill}" stroke="${c.border}" stroke-width="2.5"/>
            <circle cx="18" cy="18" r="6" fill="white" opacity="0.9"/>
            <circle cx="18" cy="18" r="3" fill="${c.fill}"/>
        </svg>`,
        iconSize: [36, 36],
        iconAnchor: [18, 18],
        className: '',
    });
}

/**
 * Créer l'icône de la Passerelle (Gateway).
 */
function _makeGatewayIcon() {
    return L.divIcon({
        html: `<svg width="44" height="52" viewBox="0 0 44 52" xmlns="http://www.w3.org/2000/svg">
            <path d="M22 2 C11 2 3 10 3 20 C3 32 22 50 22 50 C22 50 41 32 41 20 C41 10 33 2 22 2Z"
                  fill="#4d8fff" stroke="#1a6eff" stroke-width="2"/>
            <rect x="19" y="11" width="6" height="2.5" rx="1" fill="white"/>
            <rect x="20.5" y="13.5" width="3" height="10" rx="1" fill="white"/>
            <path d="M14 15 Q17 11 22 11 Q27 11 30 15" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" opacity="0.8"/>
            <path d="M10 18 Q16 10 22 10 Q28 10 34 18" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" opacity="0.45"/>
        </svg>`,
        iconSize: [44, 52],
        iconAnchor: [22, 50],
        className: '',
    });
}

/**
 * Contenu popup d'un nœud.
 */
function _popupContent(sensorId, sensor) {
    const statusLabel = {
        normal:       '<span style="color:#2ecc71">● Normal</span>',
        warning:      '<span style="color:#f0b429">● Vigilance</span>',
        alert:        '<span style="color:#e74c3c">🔥 ALERTE</span>',
        disconnected: '<span style="color:#6b7896">✕ Déconnecté</span>',
        waiting:      '<span style="color:#5e6a80">⏳ En attente</span>',
    }[sensor.status] || '–';

    const smokeRow = sensor.smoke_level != null
        ? `<div style="display:flex;justify-content:space-between;padding:4px 0;">
              <span>💨 Fumée</span>
              <strong style="color:#ffb347">${sensor.smoke_level}/4095${sensor.smoke_trigger ? ' 🔥' : ''}</strong>
           </div>` : '';

    const rssiRow = sensor.rssi != null
        ? `<div style="display:flex;justify-content:space-between;padding:4px 0;">
              <span>📶 RSSI</span>
              <strong style="color:#00d4ff;font-family:monospace">${sensor.rssi} dBm</strong>
           </div>` : '';

    return `<div style="min-width:180px;font-family:'Syne',sans-serif;">
        <div style="font-weight:800;font-size:14px;margin-bottom:8px;color:#e8eaf0">${sensor.name || sensorId}</div>
        <div style="font-size:12px;color:#9aa3b5;margin-bottom:8px;">${sensor.zone || ''} — ${statusLabel}</div>
        <div style="font-size:12px;border-top:1px solid #363c4a;padding-top:8px;">
            <div style="display:flex;justify-content:space-between;padding:4px 0;">
                <span>🌡️ Température</span>
                <strong style="color:#ff6b6b">${sensor.temperature != null ? sensor.temperature + '°C' : '--'}</strong>
            </div>
            <div style="display:flex;justify-content:space-between;padding:4px 0;">
                <span>💧 Humidité</span>
                <strong style="color:#4fc3f7">${sensor.humidity != null ? sensor.humidity + '%' : '--'}</strong>
            </div>
            ${smokeRow}
            ${rssiRow}
            <div style="display:flex;justify-content:space-between;padding:4px 0;">
                <span>🤖 Risque IA</span>
                <strong style="color:#a78bfa">${sensor.risk != null ? (sensor.risk * 100).toFixed(1) + '%' : '--'}</strong>
            </div>
        </div>
    </div>`;
}

/**
 * Initialiser la carte Leaflet avec fond OpenStreetMap.
 * OSM fonctionne en HTTP et HTTPS, pas de clé requise.
 */
export function initMap(elementId = 'map', onMarkerClick = null) {
    map = L.map(elementId, { zoomControl: true }).setView([45.52, -73.58], 13);

    // Fond OpenStreetMap standard — compatible HTTP local (pas de mixed-content)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
    }).addTo(map);

    window._onMarkerClick = onMarkerClick;

    // Ajouter la passerelle
    _initGateway();

    console.log('[Map] Carte initialisée — fond OpenStreetMap');
}

function _initGateway() {
    if (gatewayMarker) return;
    gatewayMarker = L.marker(GATEWAY_POS, { icon: _makeGatewayIcon(), zIndexOffset: 1000 })
        .addTo(map)
        .bindPopup(
            `<div style="font-family:'Syne',sans-serif;min-width:160px;">
                <div style="font-weight:800;font-size:14px;color:#e8eaf0;margin-bottom:6px;">📡 Passerelle LoRa</div>
                <div style="font-size:12px;color:#4d8fff;">● Active — Base</div>
                <div style="font-size:11px;color:#9aa3b5;margin-top:6px;">Cycle TDMA : 18s / 3 nœuds</div>
             </div>`,
            { className: 'dark-popup' }
        );
}

/**
 * Mettre à jour les marqueurs des nœuds sur la carte.
 */
export function updateMarkers(sensors) {
    Object.entries(sensors).forEach(([sensorId, sensor]) => {
        const { latitude, longitude } = sensor;
        if (!latitude || !longitude) return;

        const icon = _makeNodeIcon(sensor);

        if (!markers[sensorId]) {
            markers[sensorId] = L.marker([latitude, longitude], { icon })
                .addTo(map)
                .bindPopup(_popupContent(sensorId, sensor), { maxWidth: 240 });

            markers[sensorId].on('click', () => {
                if (window._onMarkerClick) window._onMarkerClick(sensorId);
                markers[sensorId].setPopupContent(_popupContent(sensorId, sensor));
            });
        } else {
            markers[sensorId].setIcon(icon);
            markers[sensorId].setPopupContent(_popupContent(sensorId, sensor));
        }
    });
}

/**
 * Centrer la carte sur une position.
 */
export function centerOn(lat, lng, zoom = 14) {
    if (map) map.setView([lat, lng], zoom);
}