"""
Configuration du logging pour le projet.
"""

import logging
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = "fire_detection", log_dir: str = None) -> logging.Logger:
    """Créer un logger avec sortie fichier + console."""
    from src.core.config import BASE_DIR

    if log_dir is None:
        log_dir = BASE_DIR / "data" / "logs"
    else:
        log_dir = Path(log_dir)

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{name}_{datetime.now():%Y%m%d}.log"

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # Éviter les doublons

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    fh = logging.FileHandler(log_file)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger
