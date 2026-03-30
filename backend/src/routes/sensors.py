"""
Routes API pour les capteurs et les prédictions.
Synchronisation stricte TDMA : insertion BDD + push UI uniquement à réception réelle.
Watchdog : déconnexion si timestamp_actuel - dernier_timestamp > 36s (2 cycles TDMA).
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
import asyncio
import logging

from src.core.config import SENSORS, AlertsConfig, LSTMConfig, TDMAConfig
from src.services.database_service import (
    save_measurement,
    get_sensor_history,
    mark_node_disconnected,
    get_node_status,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["sensors"])

# ─── État en mémoire ─────────────────────────────────────────────────────────
# Fenêtres de données LSTM pour chaque capteur (temperature, humidity, smoke)
sensor_windows: dict[str, list] = {s["id"]: [] for s in SENSORS}

# Dernier paquet reçu (pour Watchdog TDMA)
last_packet_time: dict[str, datetime | None] = {s["id"]: None for s in SENSORS}

# Cache des données capteurs (mis à jour uniquement à réception réelle)
sensor_cache: dict[str, dict] = {}


def _get_predictor():
    from src.api.main import predictor
    return predictor


def _determine_status(
    risk: float,
    temperature: float | None = None,
    humidity: float | None = None,
    smoke_level: int | None = None,
    smoke_trigger: bool = False,
    is_connected: bool = True,
) -> str:
    """
    Déterminer le statut en combinant :
    - Score IA LSTM
    - Seuils physiques (température, humidité, fumée)
    - État de connexion (Watchdog)
    """
    if not is_connected:
        return "disconnected"

    # Vérification fumée immédiate
    if smoke_trigger:
        return "alert"

    # Seuils critiques physiques
    if temperature is not None and temperature >= AlertsConfig.TEMP_CRITICAL:
        return "alert"
    if humidity is not None and humidity <= AlertsConfig.HUM_CRITICAL:
        return "alert"
    if smoke_level is not None and smoke_level >= AlertsConfig.SMOKE_CRITICAL:
        return "alert"

    # Score IA
    if risk >= AlertsConfig.RISK_THRESHOLD:
        return "alert"

    # Seuils d'avertissement
    if temperature is not None and temperature >= AlertsConfig.TEMP_WARNING:
        return "warning"
    if humidity is not None and humidity <= AlertsConfig.HUM_WARNING:
        return "warning"
    if smoke_level is not None and smoke_level >= AlertsConfig.SMOKE_WARNING:
        return "warning"
    if risk >= AlertsConfig.WARNING_THRESHOLD:
        return "warning"

    return "normal"


def _watchdog_check(sensor_id: str) -> bool:
    """
    Vérifier si un nœud est déconnecté.
    Seuil : 2 cycles TDMA = 2 × 18s = 36s sans paquet.
    """
    last = last_packet_time.get(sensor_id)
    if last is None:
        return False  # Jamais reçu — pas encore déconnecté, juste en attente

    now = datetime.now(timezone.utc)
    # Assurer que last est offset-aware
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)

    elapsed = (now - last).total_seconds()
    threshold = TDMAConfig.CYCLE_DURATION * TDMAConfig.WATCHDOG_MULTIPLIER  # 36s

    if elapsed > threshold:
        mark_node_disconnected(sensor_id)
        return True
    return False


# ─── GET /api/sensors ────────────────────────────────────────────────────────

@router.get("/sensors")
def get_all_sensors():
    """
    Récupérer les données de tous les capteurs avec prédictions IA.
    Inclut statut de connexion (Watchdog TDMA).
    """
    pred = _get_predictor()
    sensors_data = {}

    for sensor_cfg in SENSORS:
        sid = sensor_cfg["id"]
        window = sensor_windows[sid]

        # Vérification Watchdog
        is_disconnected = _watchdog_check(sid)

        if not window:
            sensors_data[sid] = {
                "name": sensor_cfg["name"],
                "zone": sensor_cfg["zone"],
                "temperature": None,
                "humidity": None,
                "smoke_level": None,
                "smoke_trigger": False,
                "rssi": None,
                "risk": 0.0,
                "status": "disconnected" if is_disconnected else "waiting",
                "latitude": sensor_cfg["latitude"],
                "longitude": sensor_cfg["longitude"],
                "last_seen": None,
            }
            continue

        last = window[-1]
        temp = last[0]
        hum = last[1]
        smoke = last[2] if len(last) > 2 else None
        rssi_val = last[3] if len(last) > 3 else None
        smoke_trig = bool(smoke is not None and smoke >= AlertsConfig.SMOKE_CRITICAL)

        # Prédiction LSTM si fenêtre pleine (3 features)
        risk = 0.0
        if len(window) >= LSTMConfig.WINDOW_SIZE:
            import numpy as np
            seq_data = [[r[0], r[1], r[2] if len(r) > 2 and r[2] is not None else 0]
                        for r in window[-LSTMConfig.WINDOW_SIZE:]]
            sequence = np.array(seq_data)
            risk = pred.predict(sequence)

        status = _determine_status(
            risk, temp, hum, smoke, smoke_trig, not is_disconnected
        )

        last_seen = last_packet_time.get(sid)

        sensors_data[sid] = {
            "name": sensor_cfg["name"],
            "zone": sensor_cfg["zone"],
            "temperature": round(temp, 1),
            "humidity": round(hum, 1),
            "smoke_level": int(smoke) if smoke is not None else None,
            "smoke_trigger": smoke_trig,
            "rssi": rssi_val,
            "risk": round(risk, 3),
            "status": status,
            "latitude": sensor_cfg["latitude"],
            "longitude": sensor_cfg["longitude"],
            "last_seen": last_seen.isoformat() if last_seen else None,
        }

    return {
        "timestamp": datetime.now().isoformat(),
        "sensors": sensors_data,
    }


# ─── GET /api/sensors/{sensor_id} ───────────────────────────────────────────

@router.get("/sensors/{sensor_id}")
def get_sensor(sensor_id: str):
    sensor_cfg = next((s for s in SENSORS if s["id"] == sensor_id), None)
    if not sensor_cfg:
        raise HTTPException(status_code=404, detail="Capteur non trouvé")

    window = sensor_windows.get(sensor_id, [])
    is_disconnected = _watchdog_check(sensor_id)

    if not window:
        return {
            "id": sensor_id,
            "name": sensor_cfg["name"],
            "zone": sensor_cfg["zone"],
            "temperature": None,
            "humidity": None,
            "smoke_level": None,
            "smoke_trigger": False,
            "rssi": None,
            "risk": 0.0,
            "status": "disconnected" if is_disconnected else "waiting",
            "latitude": sensor_cfg["latitude"],
            "longitude": sensor_cfg["longitude"],
            "last_seen": None,
        }

    last = window[-1]
    temp = last[0]
    hum = last[1]
    smoke = last[2] if len(last) > 2 else None
    rssi_val = last[3] if len(last) > 3 else None
    smoke_trig = bool(smoke is not None and smoke >= AlertsConfig.SMOKE_CRITICAL)

    risk = 0.0
    if len(window) >= LSTMConfig.WINDOW_SIZE:
        import numpy as np
        seq_data = [[r[0], r[1], r[2] if len(r) > 2 and r[2] is not None else 0]
                    for r in window[-LSTMConfig.WINDOW_SIZE:]]
        sequence = np.array(seq_data)
        risk = _get_predictor().predict(sequence)

    status = _determine_status(risk, temp, hum, smoke, smoke_trig, not is_disconnected)
    last_seen = last_packet_time.get(sensor_id)

    return {
        "id": sensor_id,
        "name": sensor_cfg["name"],
        "zone": sensor_cfg["zone"],
        "temperature": round(temp, 1),
        "humidity": round(hum, 1),
        "smoke_level": int(smoke) if smoke is not None else None,
        "smoke_trigger": smoke_trig,
        "rssi": rssi_val,
        "risk": round(risk, 3),
        "status": status,
        "latitude": sensor_cfg["latitude"],
        "longitude": sensor_cfg["longitude"],
        "last_seen": last_seen.isoformat() if last_seen else None,
        "window_size": len(window),
    }


# ─── GET /api/history/{sensor_id} ───────────────────────────────────────────

@router.get("/history/{sensor_id}")
def get_history(sensor_id: str, limit: int = 100):
    try:
        history = get_sensor_history(sensor_id, limit)
        return {"sensor_id": sensor_id, "count": len(history), "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── POST /api/sensors/data ─────────────────────────────────────────────────

@router.post("/sensors/data")
def receive_sensor_data(payload: dict):
    """
    Recevoir des données d'un capteur (depuis le gateway LoRa via HTTP).
    Insertion BDD et mise à jour cache uniquement ici (réception réelle).

    Payload:
    {
        "sensor_id": "sensor_1",
        "temperature": 23.5,
        "humidity": 65.2,
        "smoke_level": 150,      # optionnel (nœud 3 MQ-2)
        "smoke_trigger": false,  # optionnel
        "rssi": -78,             # optionnel
        "tdma_slot": 1           # optionnel
    }
    """
    sid = payload.get("sensor_id")
    temp = payload.get("temperature")
    hum = payload.get("humidity")

    if not sid or temp is None or hum is None:
        raise HTTPException(status_code=400,
                            detail="Champs requis: sensor_id, temperature, humidity")

    if sid not in sensor_windows:
        raise HTTPException(status_code=404, detail=f"Capteur inconnu: {sid}")

    smoke = payload.get("smoke_level")
    smoke_trigger = bool(payload.get("smoke_trigger", False))
    rssi = payload.get("rssi")
    tdma_slot = payload.get("tdma_slot")

    # Enregistrer le timestamp de réception (Watchdog)
    last_packet_time[sid] = datetime.now(timezone.utc)

    # Ajouter à la fenêtre LSTM [temp, hum, smoke, rssi]
    smoke_val = float(smoke) if smoke is not None else 0.0
    sensor_windows[sid].append([float(temp), float(hum), smoke_val, rssi or 0])
    if len(sensor_windows[sid]) > LSTMConfig.WINDOW_SIZE:
        sensor_windows[sid].pop(0)

    # Prédiction LSTM (3 features : temp, hum, smoke)
    risk = 0.0
    if len(sensor_windows[sid]) >= LSTMConfig.WINDOW_SIZE:
        import numpy as np
        seq_data = [[r[0], r[1], r[2]] for r in sensor_windows[sid][-LSTMConfig.WINDOW_SIZE:]]
        sequence = np.array(seq_data)
        risk = _get_predictor().predict(sequence)

    smoke_trig = smoke_trigger or (smoke is not None and smoke >= AlertsConfig.SMOKE_CRITICAL)
    status = _determine_status(risk, float(temp), float(hum), smoke, smoke_trig, True)

    # Sauvegarder en BDD (uniquement à réception réelle — synchronisation TDMA)
    save_measurement(
        sid, float(temp), float(hum), risk,
        smoke_level=smoke, smoke_trigger=smoke_trig,
        rssi=rssi, tdma_slot=tdma_slot,
    )

    return {
        "sensor_id": sid,
        "risk": round(risk, 3),
        "status": status,
        "smoke_level": smoke,
        "smoke_trigger": smoke_trig,
        "rssi": rssi,
        "window_size": len(sensor_windows[sid]),
        "timestamp": datetime.now().isoformat(),
    }


# ─── GET /api/averages ───────────────────────────────────────────────────────

@router.get("/averages")
def get_averages():
    """Moyennes globales pour le panneau Drawer UI."""
    temps, hums, smokes = [], [], []

    for sid in sensor_windows:
        w = sensor_windows[sid]
        if not w:
            continue
        temps.extend(r[0] for r in w)
        hums.extend(r[1] for r in w)
        smokes.extend(r[2] for r in w if len(r) > 2)

    return {
        "temp_moyenne": round(sum(temps) / len(temps), 1) if temps else None,
        "humidite_moyenne": round(sum(hums) / len(hums), 1) if hums else None,
        "fumee_max": int(max(smokes)) if smokes else None,
    }
