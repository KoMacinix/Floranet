"""
Point d'entrée de l'API FastAPI — Système de Détection d'Incendies.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import APIConfig, LSTMConfig
from src.models.lstm_model import FirePredictor
from src.routes.sensors import router as sensors_router
from src.routes.status import router as status_router

# ─── Chargement du modèle LSTM ──────────────────────────────────────────────

predictor = FirePredictor(
    model_path=LSTMConfig.MODEL_PATH,
    norm_path=LSTMConfig.NORM_PATH,
    config={
        "input_dim": LSTMConfig.INPUT_DIM,
        "hidden_dim": LSTMConfig.HIDDEN_DIM,
        "num_layers": LSTMConfig.NUM_LAYERS,
        "dropout": LSTMConfig.DROPOUT,
    },
)

# ─── Application FastAPI ─────────────────────────────────────────────────────

app = FastAPI(
    title="Fire Detection AI API",
    description="Système de détection d'incendies forestiers avec Deep Learning LSTM",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ──────────────────────────────────────────────────────────────────

app.include_router(sensors_router)
app.include_router(status_router)


@app.get("/")
def root():
    """Message de bienvenue."""
    total_params = sum(p.numel() for p in predictor.model.parameters())
    return {
        "message": "Fire Detection AI API — LSTM Deep Learning",
        "version": "1.0.0",
        "model": f"LSTM ({LSTMConfig.NUM_LAYERS} layers, {LSTMConfig.HIDDEN_DIM} neurons)",
        "parameters": total_params,
    }


# ─── Lancement ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=APIConfig.HOST, port=APIConfig.PORT)
