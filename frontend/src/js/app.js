/**
 * Application principale — Dashboard Floranet.
 *
 * Synchronisation TDMA : l'UI se rafraîchit toutes les 6s (durée d'un créneau)
 * mais ne "pousse" de données visuelles que si les données ont réellement changé
 * (contrôlé par le backend via réception réelle de paquets LoRa).
 *
 * Watchdog : si un nœud ne répond plus, le backend le marque "disconnected"
 * (2 cycles TDMA = 36s). L'UI reflète ce statut immédiatement.
 */

import { api }                                  from './services/api.js';
import { initMap, updateMarkers, centerOn }      from './components/map.js';
import { updateSensorList }                      from './components/sensorList.js';
import { showDetails, updateSummary }            from './components/detailPanel.js';

// ─── Constantes TDMA ─────────────────────────────────────────────────────────
const TDMA_SLOT_DURATION = 6000;   // 6s par créneau
const TDMA_CYCLE         = 18000;  // 18s cycle complet
const WATCHDOG_TIMEOUT   = 36000;  // 36s = 2 cycles → déconnexion

// ─── État global ─────────────────────────────────────────────────────────────
let currentSensors    = {};
let selectedSensorId  = null;
let drawerOpen        = false;

// ─── Initialisation ──────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    console.log('=== FLORANET DASHBOARD INIT ===');

    initMap('map', onSensorSelect);
    initDrawer();
    fetchData();

    // Rafraîchissement aligné sur le créneau TDMA (6s)
    setInterval(fetchData, TDMA_SLOT_DURATION);

    console.log(`[TDMA] Rafraîchissement toutes les ${TDMA_SLOT_DURATION / 1000}s`);
});

// ─── Récupération des données ─────────────────────────────────────────────────

async function fetchData() {
    try {
        const data = await api.getAllSensors();
        currentSensors = data.sensors;

        updateMarkers(currentSensors);
        updateSensorList(currentSensors, onSensorSelect);
        updateSummary(currentSensors);
        updateAlertBanner(currentSensors);
        updateLastSeen();

        // Rafraîchir le panneau de détails si un nœud est sélectionné
        if (selectedSensorId && currentSensors[selectedSensorId]) {
            showDetails(currentSensors[selectedSensorId], selectedSensorId);
        }

        // Mettre à jour les stats du drawer si ouvert
        if (drawerOpen) fetchDrawerStats();

        console.log('[OK] Données TDMA —', Object.keys(currentSensors).length, 'nœuds');
    } catch (error) {
        console.error('[ERREUR] Fetch données:', error.message);
    }
}

// ─── Sélection d'un nœud ─────────────────────────────────────────────────────

function onSensorSelect(sensorId) {
    selectedSensorId = sensorId;
    const sensor = currentSensors[sensorId];
    if (!sensor) return;

    showDetails(sensor, sensorId);

    if (sensor.latitude && sensor.longitude) {
        centerOn(sensor.latitude, sensor.longitude, 14);
    }

    console.log('[SELECT]', sensorId, '—', sensor.name, '—', sensor.status);
}

// ─── Bannière d'alerte ───────────────────────────────────────────────────────

function updateAlertBanner(sensors) {
    const banner = document.getElementById('alert-banner');
    if (!banner) return;

    const alertSensors = Object.entries(sensors)
        .filter(([, s]) => s.status === 'alert');

    if (alertSensors.length > 0) {
        const [alertId, alertData] = alertSensors[0];
        banner.style.display = 'flex';

        const title  = document.getElementById('alert-title');
        const detail = document.getElementById('alert-detail');

        if (title) title.textContent = `ALERTE — ${alertData.name}`;

        let detailText = `Zone ${alertData.zone} — Risque: ${(alertData.risk * 100).toFixed(1)}% — ${alertData.temperature}°C`;
        if (alertData.smoke_trigger) detailText += ' — 💨 FUMÉE DÉTECTÉE';
        if (detail) detail.textContent = detailText;

        const btn = document.getElementById('alert-btn');
        if (btn) btn.onclick = () => onSensorSelect(alertId);
    } else {
        banner.style.display = 'none';
    }
}

// ─── "Dernière mise à jour" ───────────────────────────────────────────────────

function updateLastSeen() {
    const el = document.getElementById('last-update-time');
    if (!el) return;
    el.textContent = new Date().toLocaleTimeString('fr-CA');
}

// ─── Drawer — Statistiques réseau ────────────────────────────────────────────

function initDrawer() {
    const drawerBtn  = document.getElementById('drawer-btn');
    const drawerEl   = document.getElementById('stats-drawer');
    const overlay    = document.getElementById('drawer-overlay');
    const closeBtn   = document.getElementById('drawer-close');

    function openDrawer() {
        drawerEl.classList.add('open');
        overlay.classList.add('open');
        drawerOpen = true;
        fetchDrawerStats();
    }

    function closeDrawer() {
        drawerEl.classList.remove('open');
        overlay.classList.remove('open');
        drawerOpen = false;
    }

    if (drawerBtn) drawerBtn.addEventListener('click', openDrawer);
    if (closeBtn)  closeBtn.addEventListener('click', closeDrawer);
    if (overlay)   overlay.addEventListener('click', closeDrawer);
}

async function fetchDrawerStats() {
    try {
        const avgs = await api.getAverages();

        _setText('avg-temp',     avgs.temp_moyenne    != null ? `${avgs.temp_moyenne}°C`        : '--°C');
        _setText('avg-humidity', avgs.humidite_moyenne != null ? `${avgs.humidite_moyenne}%`    : '--%');
        _setText('avg-smoke',    avgs.fumee_max        != null ? `${avgs.fumee_max} / 4095`     : '-- / 4095');

        // Calculer le risque moyen depuis le cache
        const risks = Object.values(currentSensors)
            .filter(s => s.risk != null)
            .map(s => s.risk);
        const avgRisk = risks.length > 0
            ? (risks.reduce((a, b) => a + b, 0) / risks.length * 100).toFixed(1)
            : '--';
        _setText('avg-risk', avgRisk !== '--' ? `${avgRisk}%` : '--%');

        // Visualisation TDMA — créneau actif selon l'heure
        _updateTDMASlots();
    } catch (e) {
        console.warn('[Drawer] Erreur stats:', e.message);
    }
}

function _updateTDMASlots() {
    const nowSec = (Date.now() / 1000) % 18; // Position dans le cycle de 18s
    const activeSlot = nowSec < 6 ? 1 : nowSec < 12 ? 2 : 3;

    [1, 2, 3].forEach(i => {
        const el = document.getElementById(`tdma-${i}`);
        if (!el) return;
        el.classList.toggle('active', i === activeSlot);
    });
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function _setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

console.log('=== APP FLORANET CHARGÉE ===');