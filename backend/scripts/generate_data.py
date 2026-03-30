"""
Génération de données synthétiques pour l'entraînement LSTM.
3 features : température, humidité, fumée (MQ-2).
Simule les 3 nœuds avec cycles TDMA réalistes.
"""

import numpy as np
import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WINDOW_SIZE = 30
N_SAMPLES   = 5000
FIRE_RATIO  = 0.35  # 35% scénarios feu

rng = np.random.default_rng(42)


def _normal_scenario():
    """Scénario normal : temp basse, humidité élevée, fumée faible."""
    temp  = rng.uniform(15, 30, WINDOW_SIZE)
    hum   = rng.uniform(50, 90, WINDOW_SIZE)
    smoke = rng.uniform(0, 200, WINDOW_SIZE)
    # Bruit léger
    temp  += rng.normal(0, 0.5, WINDOW_SIZE)
    hum   += rng.normal(0, 1.0, WINDOW_SIZE)
    smoke += rng.normal(0, 20, WINDOW_SIZE)
    return np.stack([temp, hum, np.clip(smoke, 0, 1023)], axis=1)


def _fire_scenario():
    """Scénario incendie : temp croissante, humidité chutante, fumée explosive."""
    t     = np.linspace(0, 1, WINDOW_SIZE)
    temp  = 25 + 30 * t + rng.normal(0, 1.5, WINDOW_SIZE)
    hum   = 70 - 50 * t + rng.normal(0, 2.0, WINDOW_SIZE)
    smoke = 100 + 700 * t**1.5 + rng.normal(0, 30, WINDOW_SIZE)
    return np.stack([
        np.clip(temp,  -10, 100),
        np.clip(hum,     0, 100),
        np.clip(smoke,   0, 1023),
    ], axis=1)


def _pre_fire_scenario():
    """Scénario pré-feu : légère dérive avant le pic."""
    t     = np.linspace(0, 0.6, WINDOW_SIZE)
    temp  = 22 + 15 * t + rng.normal(0, 1.0, WINDOW_SIZE)
    hum   = 65 - 25 * t + rng.normal(0, 1.5, WINDOW_SIZE)
    smoke = 80 + 300 * t**2 + rng.normal(0, 25, WINDOW_SIZE)
    return np.stack([
        np.clip(temp, -10, 100),
        np.clip(hum,    0, 100),
        np.clip(smoke,  0, 1023),
    ], axis=1)


sequences, labels = [], []

for i in range(N_SAMPLES):
    r = rng.random()
    if r < (1 - FIRE_RATIO):
        sequences.append(_normal_scenario())
        labels.append(0)
    elif r < (1 - FIRE_RATIO) + FIRE_RATIO * 0.6:
        sequences.append(_fire_scenario())
        labels.append(1)
    else:
        sequences.append(_pre_fire_scenario())
        labels.append(1)

sequences = np.array(sequences)  # (N, 30, 3)
labels    = np.array(labels)

# Paramètres de normalisation sur les 3 features
all_data = sequences.reshape(-1, 3)
mean = all_data.mean(axis=0)
std  = all_data.std(axis=0)

norm_params = {
    "mean": mean.tolist(),
    "std":  std.tolist(),
    "features": ["temperature", "humidity", "smoke_level"],
    "version": "2.0",
    "n_samples": N_SAMPLES,
}

with open(OUTPUT_DIR / "normalization_params.json", "w") as f:
    json.dump(norm_params, f, indent=2)

np.save(OUTPUT_DIR / "sequences.npy", sequences)
np.save(OUTPUT_DIR / "labels.npy", labels)

print(f"[OK] {N_SAMPLES} séquences générées (3 features : temp, hum, fumée)")
print(f"     Ratio feu: {labels.mean():.1%}")
print(f"     mean={mean.round(2)}, std={std.round(2)}")
print(f"     Sauvegardé dans: {OUTPUT_DIR}")
