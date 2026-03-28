"""
Service de gestion des alertes incendie.
Gère la confirmation, le cooldown et le déclenchement.
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class AlertService:
    """Gestion des alertes avec confirmation et cooldown."""

    def __init__(self, risk_threshold=0.7, confirmation_count=3,
                 confirmation_window=30, cooldown_period=300):
        self.risk_threshold = risk_threshold
        self.confirmation_count = confirmation_count
        self.confirmation_window = confirmation_window
        self.cooldown_period = cooldown_period

        self.high_risk_history: dict[str, list] = defaultdict(list)
        self.last_alert_time: dict[str, datetime] = {}
        self.alert_status: dict[str, bool] = defaultdict(bool)

    def _clean_old(self, sensor_id: str):
        cutoff = datetime.now() - timedelta(seconds=self.confirmation_window)
        self.high_risk_history[sensor_id] = [
            (ts, score) for ts, score in self.high_risk_history[sensor_id]
            if ts > cutoff
        ]

    def _in_cooldown(self, sensor_id: str) -> bool:
        if sensor_id not in self.last_alert_time:
            return False
        elapsed = (datetime.now() - self.last_alert_time[sensor_id]).total_seconds()
        return elapsed < self.cooldown_period

    @staticmethod
    def get_risk_level(score: float) -> str:
        if score < 0.3:
            return "low"
        elif score < 0.7:
            return "medium"
        elif score < 0.9:
            return "high"
        return "critical"

    async def process_risk(self, sensor_id: str, risk_score: float, sensor_data: dict):
        """Traiter un score de risque et déclencher une alerte si confirmé."""
        now = datetime.now()
        self._clean_old(sensor_id)
        level = self.get_risk_level(risk_score)

        logger.info(
            "%s: Risque %.1f%% (%s) — T=%s°C, H=%s%%",
            sensor_id, risk_score * 100, level,
            sensor_data.get("temperature"), sensor_data.get("humidity"),
        )

        if risk_score >= self.risk_threshold:
            self.high_risk_history[sensor_id].append((now, risk_score))
            count = len(self.high_risk_history[sensor_id])

            if (count >= self.confirmation_count
                    and not self._in_cooldown(sensor_id)
                    and not self.alert_status[sensor_id]):
                logger.critical(
                    "ALERTE INCENDIE — %s: %s (%.1f%%)",
                    sensor_id, level.upper(), risk_score * 100,
                )
                self.alert_status[sensor_id] = True
                self.last_alert_time[sensor_id] = now
        else:
            if self.alert_status[sensor_id]:
                logger.info("%s: Retour à la normale", sensor_id)
                self.alert_status[sensor_id] = False
                self.high_risk_history[sensor_id].clear()
