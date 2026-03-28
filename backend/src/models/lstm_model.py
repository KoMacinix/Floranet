"""
Modèle LSTM pour la détection d'incendies forestiers.
Architecture : 3 couches LSTM → Dropout → Dense → Sigmoid
"""

import torch
import torch.nn as nn
import numpy as np
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LSTMModel(nn.Module):
    """Réseau LSTM pour classification binaire (feu / pas feu)."""

    def __init__(self, input_dim=2, hidden_dim=128, num_layers=3, dropout=0.3):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        lstm_out, _ = self.lstm(x)
        last_output = lstm_out[:, -1, :]
        return self.sigmoid(self.fc(self.dropout(last_output)))


class FirePredictor:
    """Wrapper de haut niveau : charge le modèle et expose predict()."""

    def __init__(self, model_path: Path, norm_path: Path, config: dict):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Créer et charger le modèle
        self.model = LSTMModel(
            input_dim=config["input_dim"],
            hidden_dim=config["hidden_dim"],
            num_layers=config["num_layers"],
            dropout=config["dropout"],
        ).to(self.device)

        if model_path.exists():
            state = torch.load(model_path, map_location=self.device, weights_only=True)
            self.model.load_state_dict(state)
            logger.info("Modèle LSTM chargé: %s", model_path.name)
        else:
            logger.warning("Modèle non trouvé: %s — utilisation des poids aléatoires", model_path)

        self.model.eval()

        # Charger les paramètres de normalisation
        if norm_path.exists():
            with open(norm_path, "r") as f:
                params = json.load(f)
            self.mean = np.array(params["mean"])
            self.std = np.array(params["std"])
            logger.info("Normalisation chargée: mean=%s, std=%s", self.mean, self.std)
        else:
            self.mean = np.zeros(config["input_dim"])
            self.std = np.ones(config["input_dim"])
            logger.warning("Paramètres de normalisation non trouvés — pas de normalisation")

        total_params = sum(p.numel() for p in self.model.parameters())
        logger.info("Modèle prêt: %s paramètres sur %s", f"{total_params:,}", self.device)

    def predict(self, sequence: np.ndarray) -> float:
        """
        Prédire le score de risque d'incendie.

        Args:
            sequence: array (window_size, input_dim) — ex: (30, 2)

        Returns:
            Score de risque entre 0.0 et 1.0
        """
        normalized = (sequence - self.mean) / (self.std + 1e-8)
        tensor = torch.FloatTensor(normalized).unsqueeze(0).to(self.device)

        with torch.no_grad():
            risk = self.model(tensor).squeeze().item()

        return risk
