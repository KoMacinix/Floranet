/**
 * Application principale — Dashboard de Surveillance des Incendies.
 *
 * Orchestre les composants : carte, liste des capteurs, panneau de détails.
 * Rafraîchit les données toutes les 5 secondes via l'API backend.
 */

import { api } from './services/api.js';
import { initMap, updateMarkers, centerOn } from './components/map.js';
import { updateSensorList } from './components/sensorList.js';
import { showDetails, updateSummary } from './components/detailPanel.js';

// ─── État global ────────────────────────────────────────────────────────────

const UPDATE_INTERVAL = 5000;
let currentSensors = {};
let selectedSensorId = null;

// ─── Initialisation ─────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    console.log('=== INITIALISATION DU DASHBOARD ===');

    initMap('map', onSensorSelect);
    fetchData();
    setInterval(fetchData, UPDATE_INTERVAL);
    startClock();
});

// ─── Récupération des données ───────────────────────────────────────────────

async function fetchData() {
    try {
        const data = await api.getAllSensors();
        currentSensors = data.sensors;

        updateMarkers(currentSensors);
        updateSensorList(currentSensors, onSensorSelect);
        updateSummary(currentSensors);
        updateAlertBanner(currentSensors);

        // Rafraîchir le panneau de détails si un capteur est sélectionné
        if (selectedSensorId && currentSensors[selectedSensorId]) {
            showDetails(currentSensors[selectedSensorId], selectedSensorId);
        }

        console.log('[OK] Données rafraîchies —', Object.keys(currentSensors).length, 'capteurs');
    } catch (error) {
        console.error('[ERREUR] Impossible de récupérer les données:', error.message);
    }
}

// ─── Sélection d'un capteur ─────────────────────────────────────────────────

function onSensorSelect(sensorId) {
    selectedSensorId = sensorId;
    const sensor = currentSensors[sensorId];
    if (!sensor) return;

    showDetails(sensor, sensorId);

    if (sensor.latitude && sensor.longitude) {
        centerOn(sensor.latitude, sensor.longitude, 14);
    }

    console.log('[SELECT]', sensorId, '—', sensor.name);
}

// ─── Bannière d'alerte ──────────────────────────────────────────────────────

function updateAlertBanner(sensors) {
    const banner = document.getElementById('alert-banner');
    if (!banner) return;

    const alertSensors = Object.entries(sensors)
        .filter(([, s]) => s.status === 'alert');

    if (alertSensors.length > 0) {
        const [alertId, alertData] = alertSensors[0];
        banner.style.display = 'flex';

        const title = document.getElementById('alert-title');
        const detail = document.getElementById('alert-detail');
        if (title) title.textContent = `ALERTE INCENDIE — ${alertData.name}`;
        if (detail) detail.textContent = `Zone ${alertData.zone} — Risque: ${(alertData.risk * 100).toFixed(1)}% — ${alertData.temperature}°C`;

        const btn = document.getElementById('alert-btn');
        if (btn) {
            btn.onclick = () => onSensorSelect(alertId);
        }
    } else {
        banner.style.display = 'none';
    }
}

// ─── Horloge ────────────────────────────────────────────────────────────────

function startClock() {
    const el = document.getElementById('time');
    if (!el) return;

    function tick() {
        el.textContent = '⏰ ' + new Date().toLocaleTimeString('fr-CA');
    }
    tick();
    setInterval(tick, 1000);
}

console.log('=== APP CHARGÉE ===');
