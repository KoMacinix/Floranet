"""
Service PostgreSQL — connexion et opérations CRUD.
"""

import psycopg2
import logging
from contextlib import contextmanager
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


def save_measurement(sensor_id: str, temperature: float, humidity: float, risk_score: float) -> bool:
    """Sauvegarder une mesure dans PostgreSQL."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()

            cur.execute(
                """INSERT INTO measurements (sensor_id, temperature, humidity, risk_score)
                   VALUES (%s, %s, %s, %s)""",
                (sensor_id, temperature, humidity, risk_score),
            )

            # Insérer une alerte si le seuil est atteint
            from src.core.config import AlertsConfig

            if risk_score >= AlertsConfig.RISK_THRESHOLD:
                alert_type = "alert"
            elif risk_score >= AlertsConfig.WARNING_THRESHOLD:
                alert_type = "warning"
            else:
                alert_type = None

            if alert_type:
                cur.execute(
                    """INSERT INTO alerts (sensor_id, risk_score, temperature, humidity, alert_type)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (sensor_id, risk_score, temperature, humidity, alert_type),
                )

            cur.close()
        return True
    except Exception as e:
        logger.error("Erreur sauvegarde DB: %s", e)
        return False


def get_sensor_history(sensor_id: str, limit: int = 100) -> list[dict]:
    """Récupérer l'historique d'un capteur."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT temperature, humidity, risk_score, timestamp
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
            "risk": row[2],
            "timestamp": row[3].isoformat(),
        }
        for row in rows
    ]


def get_system_stats() -> dict:
    """Statistiques globales du système."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM sensors")
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
        return {
            "connected": False,
            "sensor_count": 0,
            "active_alerts": 0,
            "total_measurements": 0,
        }
