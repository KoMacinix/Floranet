"""
Service InfluxDB — stockage de séries temporelles.
"""

import logging
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger(__name__)


class InfluxDBService:
    """Écriture des données capteurs dans InfluxDB."""

    def __init__(self, url: str, token: str, org: str, bucket: str):
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.client = None
        self.write_api = None

    async def connect(self):
        try:
            self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            health = self.client.health()
            if health.status == "pass":
                logger.info("InfluxDB connecté: %s", self.url)
        except Exception as e:
            logger.warning("InfluxDB non disponible: %s", e)

    async def write_sensor_data(self, data: dict):
        if not self.write_api:
            return
        try:
            point = Point("sensor_data").tag("sensor_id", data["sensor_id"])
            for key, value in data.items():
                if key not in ("sensor_id", "timestamp", "reception_time") and isinstance(value, (int, float)):
                    point = point.field(key, float(value))
            if "timestamp" in data:
                ts = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
                point = point.time(ts)
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
        except Exception as e:
            logger.error("Erreur écriture InfluxDB: %s", e)

    async def close(self):
        if self.client:
            self.client.close()
