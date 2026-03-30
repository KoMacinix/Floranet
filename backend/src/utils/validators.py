"""
Validation des données reçues des capteurs.
"""

import logging

logger = logging.getLogger(__name__)


class DataValidator:
    """Valide les données brutes des capteurs avant traitement."""

    def __init__(self, temp_min=-40, temp_max=100, hum_min=0, hum_max=100,
                 allow_missing=False):
        self.temp_min = temp_min
        self.temp_max = temp_max
        self.hum_min = hum_min
        self.hum_max = hum_max
        self.allow_missing = allow_missing
        self.stats = {"total": 0, "valid": 0, "invalid": 0}

    def validate(self, data: dict) -> bool:
        """Valider un dictionnaire de données capteur."""
        self.stats["total"] += 1

        # Champ obligatoire
        if "sensor_id" not in data or not isinstance(data["sensor_id"], str):
            self.stats["invalid"] += 1
            return False

        # Vérifier la présence des mesures
        if not self.allow_missing:
            if "temperature" not in data and "humidity" not in data:
                self.stats["invalid"] += 1
                return False

        # Plages de valeurs
        if "temperature" in data:
            temp = data["temperature"]
            if not isinstance(temp, (int, float)) or not (self.temp_min <= temp <= self.temp_max):
                self.stats["invalid"] += 1
                return False

        if "humidity" in data:
            hum = data["humidity"]
            if not isinstance(hum, (int, float)) or not (self.hum_min <= hum <= self.hum_max):
                self.stats["invalid"] += 1
                return False

        self.stats["valid"] += 1
        return True

    def get_stats(self) -> dict:
        return self.stats.copy()
