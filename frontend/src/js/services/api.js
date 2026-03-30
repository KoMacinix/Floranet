/**
 * Service API — Communication avec le backend FastAPI.
 * Synchronisé TDMA : les données ne changent qu'à réception réelle (~6s par nœud).
 */

const API_URL = 'http://127.0.0.1:8000';

export const api = {

    async getAllSensors() {
        const res = await fetch(`${API_URL}/api/sensors`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    async getSensor(sensorId) {
        const res = await fetch(`${API_URL}/api/sensors/${sensorId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    async getHistory(sensorId, limit = 100) {
        const res = await fetch(`${API_URL}/api/history/${sensorId}?limit=${limit}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    async getStatus() {
        const res = await fetch(`${API_URL}/api/status`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    async getAverages() {
        const res = await fetch(`${API_URL}/api/averages`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },
};