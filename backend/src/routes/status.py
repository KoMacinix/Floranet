"""
Routes API pour le statut du système.
"""

from fastapi import APIRouter
from src.services.database_service import get_system_stats

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status")
def get_status():
    """Statut global du système (DB, modèle, capteurs)."""
    from src.api.main import predictor

    db_stats = get_system_stats()
    total_params = sum(p.numel() for p in predictor.model.parameters())

    return {
        "system": "operational",
        "model_loaded": True,
        "model_type": "LSTM",
        "model_parameters": total_params,
        "database_connected": db_stats["connected"],
        "active_sensors": db_stats["sensor_count"],
        "active_alerts": db_stats["active_alerts"],
        "total_measurements": db_stats["total_measurements"],
    }
