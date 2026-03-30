"""
Configuration centralisée du système.
Charge les secrets depuis .env et la config depuis config.yaml.
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


def _load_yaml() -> dict:
    config_path = BASE_DIR / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


_yaml = _load_yaml()


# ─── Base de données ─────────────────────────────────────────────────────────

class DatabaseConfig:
    HOST: str     = os.getenv("DB_HOST", "localhost")
    PORT: int     = int(os.getenv("DB_PORT", "5432"))
    NAME: str     = os.getenv("DB_NAME", "fire_detection_db")
    USER: str     = os.getenv("DB_USER", "postgres")
    PASSWORD: str = os.getenv("DB_PASSWORD", "")


# ─── InfluxDB ────────────────────────────────────────────────────────────────

class InfluxDBConfig:
    URL: str    = os.getenv("INFLUXDB_URL", "http://localhost:8086")
    TOKEN: str  = os.getenv("INFLUXDB_TOKEN", "")
    ORG: str    = os.getenv("INFLUXDB_ORG", "")
    BUCKET: str = os.getenv("INFLUXDB_BUCKET", "fire-detection")


# ─── LoRa Serial ─────────────────────────────────────────────────────────────

class LoRaConfig:
    PORT: str      = os.getenv("LORA_PORT", "COM3")
    BAUDRATE: int  = int(os.getenv("LORA_BAUDRATE", "115200"))
    TIMEOUT: float = 1.0


# ─── API ─────────────────────────────────────────────────────────────────────

class APIConfig:
    HOST: str = os.getenv("API_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("API_PORT", "8000"))


# ─── Cycle TDMA ──────────────────────────────────────────────────────────────

class TDMAConfig:
    CYCLE_DURATION: int      = _yaml["tdma"]["cycle_duration"]   # 18s
    SLOT_DURATION: int       = _yaml["tdma"]["slot_duration"]    # 6s
    NUM_SLOTS: int           = _yaml["tdma"]["num_slots"]        # 3
    WATCHDOG_MULTIPLIER: int = _yaml["tdma"]["watchdog_multiplier"]  # 2 → seuil 36s


# ─── Modèle LSTM ─────────────────────────────────────────────────────────────

class LSTMConfig:
    INPUT_DIM: int   = _yaml["lstm"]["input_dim"]    # 3 (temp, hum, smoke)
    HIDDEN_DIM: int  = _yaml["lstm"]["hidden_dim"]
    NUM_LAYERS: int  = _yaml["lstm"]["num_layers"]
    DROPOUT: float   = _yaml["lstm"]["dropout"]
    WINDOW_SIZE: int = _yaml["lstm"]["window_size"]
    MODEL_PATH: Path = BASE_DIR / "data" / "models" / "lstm_fire_detection.pth"
    NORM_PATH: Path  = BASE_DIR / "data" / "models" / "normalization_params.json"


# ─── Capteurs ────────────────────────────────────────────────────────────────

SENSORS: list[dict] = _yaml["sensors"]
GATEWAY: dict       = _yaml.get("gateway", {})


# ─── Alertes + seuils physiques ──────────────────────────────────────────────

class AlertsConfig:
    RISK_THRESHOLD: float    = _yaml["alerts"]["risk_threshold"]
    WARNING_THRESHOLD: float = _yaml["alerts"]["warning_threshold"]
    CONFIRMATION_COUNT: int  = _yaml["alerts"]["confirmation_count"]
    CONFIRMATION_WINDOW: int = _yaml["alerts"]["confirmation_window"]
    COOLDOWN_PERIOD: int     = _yaml["alerts"]["cooldown_period"]

    # Seuils physiques (température)
    TEMP_WARNING: float  = _yaml["alerts"]["temperature_warning"]
    TEMP_CRITICAL: float = _yaml["alerts"]["temperature_critical"]

    # Seuils physiques (humidité — bas = danger)
    HUM_WARNING: float  = _yaml["alerts"]["humidity_warning"]
    HUM_CRITICAL: float = _yaml["alerts"]["humidity_critical"]

    # Seuils physiques (fumée MQ-2)
    SMOKE_WARNING: int  = _yaml["alerts"]["smoke_warning"]
    SMOKE_CRITICAL: int = _yaml["alerts"]["smoke_critical"]


# ─── Validation ──────────────────────────────────────────────────────────────

class ValidationConfig:
    TEMP_MIN: float    = _yaml["validation"]["temperature_min"]
    TEMP_MAX: float    = _yaml["validation"]["temperature_max"]
    HUM_MIN: float     = _yaml["validation"]["humidity_min"]
    HUM_MAX: float     = _yaml["validation"]["humidity_max"]
    SMOKE_MIN: int     = _yaml["validation"]["smoke_min"]
    SMOKE_MAX: int     = _yaml["validation"]["smoke_max"]
    ALLOW_MISSING: bool = _yaml["validation"]["allow_missing_fields"]
