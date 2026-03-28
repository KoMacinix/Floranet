/**
 * Service API — Communication avec le backend FastAPI.
 */

const API_URL = 'http://127.0.0.1:8000';

export const api = {

    /**
     * Récupérer les données de tous les capteurs.
     * @returns {Promise<{timestamp: string, sensors: Object}>}
     */
    async getAllSensors() {
        const res = await fetch(`${API_URL}/api/sensors`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    /**
     * Récupérer les données d'un capteur spécifique.
     * @param {string} sensorId
     * @returns {Promise<Object>}
     */
    async getSensor(sensorId) {
        const res = await fetch(`${API_URL}/api/sensors/${sensorId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    /**
     * Récupérer l'historique d'un capteur.
     * @param {string} sensorId
     * @param {number} limit
     * @returns {Promise<{sensor_id: string, count: number, history: Array}>}
     */
    async getHistory(sensorId, limit = 100) {
        const res = await fetch(`${API_URL}/api/history/${sensorId}?limit=${limit}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    /**
     * Récupérer le statut global du système.
     * @returns {Promise<Object>}
     */
    async getStatus() {
        const res = await fetch(`${API_URL}/api/status`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },
};
