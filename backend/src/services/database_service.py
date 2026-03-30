"""
Service PostgreSQL — connexion et opérations CRUD.
Synchronisé avec le cycle TDMA (insertions uniquement à la réception réelle).
"""

import psycopg2
import logging
from contextlib import contextmanager
from datetime import datetime
from src.core.config import DatabaseConfig

logger = logging.getLogger(__name__)


@contextmanager
def get_connection():
    """Context manager pour une connexion PostgreSQL."""
    conn = psycopg2.connect(
        host=DatabaseConfig.HOST,
        port=DatabaseConfig.PORT,
        dbname=DatabaseConfig.NAME,
        user=DatabaseConfig.USER,
        password=DatabaseConfig.PASSWORD,
        sslmode="disable",
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def save_measurement(
    sensor_id: str,
    temperature: float,
    humidity: float,
    risk_score: float,
    smoke_level: int | None = None,
    smoke_trigger: bool = False,
    rssi: int | None = None,
    tdma_slot: int | None = None,
) -> bool:
    """
    Sauvegarder une mesure dans PostgreSQL.
    Appelé UNIQUEMENT à la réception réelle d'un paquet (logique TDMA).
    Inclut smoke_level, smoke_trigger (nœud 3 MQ-2) et rssi.
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()

            cur.execute(
                """INSERT INTO measurements
                   (sensor_id, temperature, humidity, smoke_level, smoke_trigger,
                    rssi, risk_score, tdma_slot, packet_received, timestamp)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE, NOW())""",
                (sensor_id, temperature, humidity, smoke_level,
                 smoke_trigger, rssi, risk_score, tdma_slot),
            )

            # Mettre à jour le statut du nœud (Watchdog)
            cur.execute(
                """INSERT INTO node_status (sensor_id, last_seen, is_connected, consecutive_missed, updated_at)
                   VALUES (%s, NOW(), TRUE, 0, NOW())
                   ON CONFLICT (sensor_id)
                   DO UPDATE SET last_seen = NOW(), is_connected = TRUE,
                                 consecutive_missed = 0, updated_at = NOW()""",
                (sensor_id,),
            )

            # Insérer une alerte si seuil atteint
            from src.core.config import AlertsConfig
            if risk_score >= AlertsConfig.RISK_THRESHOLD:
                alert_type = "alert"
            elif risk_score >= AlertsConfig.WARNING_THRESHOLD:
                alert_type = "warning"
            else:
                alert_type = None

            if alert_type or smoke_trigger:
                cur.execute(
                    """INSERT INTO alerts
                       (sensor_id, risk_score, temperature, humidity,
                        smoke_level, smoke_trigger, alert_type)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (sensor_id, risk_score, temperature, humidity,
                     smoke_level, smoke_trigger,
                     alert_type if alert_type else "smoke"),
                )

            cur.close()
        return True
    except Exception as e:
        logger.error("Erreur sauvegarde DB: %s", e)
        return False


def mark_node_disconnected(sensor_id: str) -> bool:
    """
    Watchdog : marquer un nœud comme Déconnecté.
    Appelé si timestamp_actuel - dernier_timestamp > 36s (2 cycles TDMA).
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """UPDATE node_status
                   SET is_connected = FALSE,
                       consecutive_missed = consecutive_missed + 1,
                       updated_at = NOW()
                   WHERE sensor_id = %s""",
                (sensor_id,),
            )
            cur.close()
        logger.warning("Nœud %s marqué Déconnecté (watchdog)", sensor_id)
        return True
    except Exception as e:
        logger.error("Erreur watchdog DB: %s", e)
        return False


def get_node_status(sensor_id: str) -> dict:
    """Récupérer le statut de connexion d'un nœud."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT last_seen, is_connected, consecutive_missed FROM node_status WHERE sensor_id = %s",
                (sensor_id,),
            )
            row = cur.fetchone()
            cur.close()
        if row:
            return {
                "last_seen": row[0].isoformat() if row[0] else None,
                "is_connected": row[1],
                "consecutive_missed": row[2],
            }
        return {"last_seen": None, "is_connected": False, "consecutive_missed": 0}
    except Exception as e:
        logger.error("Erreur statut nœud: %s", e)
        return {"last_seen": None, "is_connected": False, "consecutive_missed": 0}


def get_sensor_history(sensor_id: str, limit: int = 100) -> list[dict]:
    """Récupérer l'historique d'un capteur."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT temperature, humidity, smoke_level, smoke_trigger,
                      rssi, risk_score, timestamp
               FROM measurements
               WHERE sensor_id = %s
               ORDER BY timestamp DESC
               LIMIT %s""",
            (sensor_id, limit),
        )
        rows = cur.fetchall()
        cur.close()

    return [
        {
            "temperature": row[0],
            "humidity": row[1],
            "smoke_level": row[2],
            "smoke_trigger": row[3],
            "rssi": row[4],
            "risk": row[5],
            "timestamp": row[6].isoformat(),
        }
        for row in rows
    ]


def get_system_stats() -> dict:
    """Statistiques globales du système."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sensors WHERE sensor_id != 'gateway'")
            sensor_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM alerts WHERE acknowledged = FALSE")
            active_alerts = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM measurements")
            total_measurements = cur.fetchone()[0]
            cur.close()
        return {
            "connected": True,
            "sensor_count": sensor_count,
            "active_alerts": active_alerts,
            "total_measurements": total_measurements,
        }
    except Exception as e:
        logger.error("Erreur stats DB: %s", e)
        return {"connected": False, "sensor_count": 0, "active_alerts": 0, "total_measurements": 0}
