"""
Routes API pour les capteurs et les prédictions.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime

from src.core.config import SENSORS, AlertsConfig, LSTMConfig
from src.services.database_service import save_measurement, get_sensor_history

router = APIRouter(prefix="/api", tags=["sensors"])

# ─── État en mémoire ─────────────────────────────────────────────────────────
# Les fenêtres de données pour chaque capteur (pour le modèle LSTM)
sensor_windows: dict[str, list] = {s["id"]: [] for s in SENSORS}


def _get_predictor():
    """Récupérer le FirePredictor chargé au démarrage (via app.state)."""
    from src.api.main import predictor
    return predictor


def _determine_status(risk: float) -> str:
    if risk >= AlertsConfig.RISK_THRESHOLD:
        return "alert"
    elif risk >= AlertsConfig.WARNING_THRESHOLD:
        return "warning"
    return "normal"


# ─── GET /api/sensors ────────────────────────────────────────────────────────

@router.get("/sensors")
def get_all_sensors():
    """Récupérer les données de tous les capteurs avec prédictions IA."""
    pred = _get_predictor()
    sensors_data = {}

    for sensor_cfg in SENSORS:
        sid = sensor_cfg["id"]
        window = sensor_windows[sid]

        # Si aucune donnée n'a encore été reçue, renvoyer un état vide
        if not window:
            sensors_data[sid] = {
                "name": sensor_cfg["name"],
                "zone": sensor_cfg["zone"],
                "temperature": None,
                "humidity": None,
                "risk": 0.0,
                "status": "normal",
                "latitude": sensor_cfg["latitude"],
                "longitude": sensor_cfg["longitude"],
            }
            continue

        # Dernière mesure
        last = window[-1]
        temp, hum = last[0], last[1]

        # Prédiction LSTM si fenêtre pleine
        risk = 0.0
        if len(window) >= LSTMConfig.WINDOW_SIZE:
            import numpy as np
            sequence = np.array(window[-LSTMConfig.WINDOW_SIZE:])
            risk = pred.predict(sequence)

        status = _determine_status(risk)

        # Sauvegarder en DB
        save_measurement(sid, temp, hum, risk)

        sensors_data[sid] = {
            "name": sensor_cfg["name"],
            "zone": sensor_cfg["zone"],
            "temperature": round(temp, 1),
            "humidity": round(hum, 1),
            "risk": round(risk, 3),
            "status": status,
            "latitude": sensor_cfg["latitude"],
            "longitude": sensor_cfg["longitude"],
        }

    return {
        "timestamp": datetime.now().isoformat(),
        "sensors": sensors_data,
    }


# ─── GET /api/sensors/{sensor_id} ───────────────────────────────────────────

@router.get("/sensors/{sensor_id}")
def get_sensor(sensor_id: str):
    """Récupérer les données d'un capteur spécifique."""
    sensor_cfg = next((s for s in SENSORS if s["id"] == sensor_id), None)
    if not sensor_cfg:
        raise HTTPException(status_code=404, detail="Capteur non trouvé")

    window = sensor_windows.get(sensor_id, [])

    if not window:
        return {
            "id": sensor_id,
            "name": sensor_cfg["name"],
            "zone": sensor_cfg["zone"],
            "temperature": None,
            "humidity": None,
            "risk": 0.0,
            "status": "normal",
            "latitude": sensor_cfg["latitude"],
            "longitude": sensor_cfg["longitude"],
            "window_size": 0,
        }

    last = window[-1]
    temp, hum = last[0], last[1]

    risk = 0.0
    if len(window) >= LSTMConfig.WINDOW_SIZE:
        import numpy as np
        sequence = np.array(window[-LSTMConfig.WINDOW_SIZE:])
        risk = _get_predictor().predict(sequence)

    status = _determine_status(risk)
    save_measurement(sensor_id, temp, hum, risk)

    return {
        "id": sensor_id,
        "name": sensor_cfg["name"],
        "zone": sensor_cfg["zone"],
        "temperature": round(temp, 1),
        "humidity": round(hum, 1),
        "risk": round(risk, 3),
        "status": status,
        "latitude": sensor_cfg["latitude"],
        "longitude": sensor_cfg["longitude"],
        "window_size": len(window),
    }


# ─── GET /api/history/{sensor_id} ───────────────────────────────────────────

@router.get("/history/{sensor_id}")
def get_history(sensor_id: str, limit: int = 100):
    """Récupérer l'historique d'un capteur depuis PostgreSQL."""
    try:
        history = get_sensor_history(sensor_id, limit)
        return {
            "sensor_id": sensor_id,
            "count": len(history),
            "history": history,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── POST /api/sensors/data ─────────────────────────────────────────────────

@router.post("/sensors/data")
def receive_sensor_data(payload: dict):
    """
    Recevoir des données d'un capteur (depuis le gateway LoRa via HTTP).

    Payload attendu:
    {
        "sensor_id": "sensor_1",
        "temperature": 23.5,
        "humidity": 65.2
    }
    """
    sid = payload.get("sensor_id")
    temp = payload.get("temperature")
    hum = payload.get("humidity")

    if not sid or temp is None or hum is None:
        raise HTTPException(status_code=400, detail="Champs requis: sensor_id, temperature, humidity")

    # Vérifier que le capteur existe
    if sid not in sensor_windows:
        raise HTTPException(status_code=404, detail=f"Capteur inconnu: {sid}")

    # Ajouter à la fenêtre
    sensor_windows[sid].append([float(temp), float(hum)])
    if len(sensor_windows[sid]) > LSTMConfig.WINDOW_SIZE:
        sensor_windows[sid].pop(0)

    # Prédiction
    risk = 0.0
    if len(sensor_windows[sid]) >= LSTMConfig.WINDOW_SIZE:
        import numpy as np
        sequence = np.array(sensor_windows[sid][-LSTMConfig.WINDOW_SIZE:])
        risk = _get_predictor().predict(sequence)

    status = _determine_status(risk)

    # Sauvegarder
    save_measurement(sid, temp, hum, risk)

    return {
        "sensor_id": sid,
        "risk": round(risk, 3),
        "status": status,
        "window_size": len(sensor_windows[sid]),
        "timestamp": datetime.now().isoformat(),
    }
