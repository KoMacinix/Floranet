/**
 * Composant Carte — Gestion de la carte Leaflet et des marqueurs.
 */

let map;
const markers = {};

const icons = {
    normal: L.divIcon({
        html: '<div style="background:#4CAF50;width:30px;height:30px;border-radius:50%;border:3px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3);"></div>',
        iconSize: [30, 30],
        className: '',
    }),
    warning: L.divIcon({
        html: '<div style="background:#FF9800;width:30px;height:30px;border-radius:50%;border:3px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3);"></div>',
        iconSize: [30, 30],
        className: '',
    }),
    alert: L.divIcon({
        html: '<div style="background:#F44336;width:30px;height:30px;border-radius:50%;border:3px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3);"></div>',
        iconSize: [30, 30],
        className: '',
    }),
};

/**
 * Initialiser la carte Leaflet.
 * @param {string} elementId - ID de l'élément HTML
 * @param {Function} onMarkerClick - Callback quand un marqueur est cliqué
 */
export function initMap(elementId = 'map', onMarkerClick = null) {
    map = L.map(elementId).setView([45.52, -73.58], 12);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);

    window._onMarkerClick = onMarkerClick;
    console.log('[Map] Carte initialisée');
}

/**
 * Mettre à jour les marqueurs sur la carte.
 * @param {Object} sensors - Données des capteurs
 */
export function updateMarkers(sensors) {
    Object.entries(sensors).forEach(([sensorId, sensor]) => {
        const { latitude, longitude, status } = sensor;

        if (!markers[sensorId]) {
            markers[sensorId] = L.marker([latitude, longitude]).addTo(map);
            markers[sensorId].on('click', () => {
                if (window._onMarkerClick) window._onMarkerClick(sensorId);
            });
        }

        markers[sensorId].setIcon(icons[status] || icons.normal);
    });
}

/**
 * Centrer la carte sur un capteur.
 * @param {number} lat
 * @param {number} lng
 * @param {number} zoom
 */
export function centerOn(lat, lng, zoom = 14) {
    if (map) map.setView([lat, lng], zoom);
}
