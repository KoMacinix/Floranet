# Backend — Système de Détection d'Incendies Forestiers

API REST construite avec **FastAPI** (Python) intégrant un modèle **LSTM** (PyTorch) pour la prédiction de risques d'incendie en temps réel.

## Architecture

```
backend/
├── config.yaml              # Configuration (capteurs, seuils, modèle)
├── .env                     # Secrets (DB, tokens) — NE PAS COMMITER
├── .env.example             # Template pour .env
├── requirements.txt         # Dépendances Python
├── package.json             # Raccourcis npm (optionnel)
│
├── db/
│   ├── init.sql             # Schéma SQL complet
│   └── README.md            # Documentation de la base
│
├── src/
│   ├── api/
│   │   └── main.py          # Point d'entrée FastAPI
│   ├── routes/
│   │   ├── sensors.py       # /api/sensors, /api/sensors/data, /api/history
│   │   └── status.py        # /api/status
│   ├── services/
│   │   ├── database_service.py    # PostgreSQL CRUD
│   │   ├── alert_service.py       # Gestion des alertes
│   │   ├── influxdb_service.py    # Séries temporelles
│   │   └── lora_service.py        # Communication série LoRa
│   ├── models/
│   │   ├── lstm_model.py    # Modèle LSTM + FirePredictor
│   │   └── trainer.py       # Entraînement du modèle
│   ├── core/
│   │   └── config.py        # Configuration centralisée
│   └── utils/
│       ├── logger.py        # Logging fichier + console
│       └── validators.py    # Validation des données capteurs
│
├── scripts/
│   ├── init_database.py     # Initialiser PostgreSQL
│   ├── generate_data.py     # Générer des données d'entraînement
│   └── train_model.py       # Entraîner le modèle LSTM
│
├── data/
│   ├── datasets/            # Données d'entraînement (.npy)
│   ├── models/              # Modèle entraîné (.pth) + normalisation
│   └── logs/                # Logs d'exécution
│
└── tests/                   # Tests unitaires (pytest)
```

## Prérequis

- **Python 3.11+**
- **PostgreSQL 15+**
- **InfluxDB 2.x** (optionnel — pour le monitoring avancé)

## Installation

### 1. Environnement Python

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Linux/Mac
# .venv\Scripts\activate        # Windows

pip install -r requirements.txt
```

### 2. Configuration

Copier le template et remplir les valeurs :
```bash
cp .env.example .env
```

Éditer `.env` avec vos identifiants PostgreSQL et InfluxDB.

### 3. Base de données

```bash
# Créer la base PostgreSQL
psql -U postgres -c "CREATE DATABASE fire_detection_db;"

# Initialiser les tables
python scripts/init_database.py
```

## Lancement

```bash
# Mode développement (rechargement automatique)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Ou via npm (raccourci)
npm run dev
```

L'API sera disponible sur `http://localhost:8000`.
La documentation Swagger est sur `http://localhost:8000/docs`.

## Endpoints API

| Méthode | Route                    | Description                                         |
|---------|--------------------------|-----------------------------------------------------|
| GET     | `/`                      | Info du système et du modèle                        |
| GET     | `/api/sensors`           | Données de tous les capteurs + prédiction IA        |
| GET     | `/api/sensors/{id}`      | Données d'un capteur spécifique                     |
| POST    | `/api/sensors/data`      | **Recevoir des données du gateway LoRa**            |
| GET     | `/api/history/{id}`      | Historique d'un capteur (PostgreSQL)                |
| GET     | `/api/status`            | Statut global (DB, modèle, alertes)                 |

### POST /api/sensors/data

C'est l'endpoint que le **gateway LoRa** utilise pour envoyer les données :

```json
{
    "sensor_id": "sensor_1",
    "temperature": 23.5,
    "humidity": 65.2
}
```

Réponse :
```json
{
    "sensor_id": "sensor_1",
    "risk": 0.042,
    "status": "normal",
    "window_size": 15,
    "timestamp": "2026-03-28T16:30:00"
}
```

## Modèle LSTM

- **Architecture** : 3 couches LSTM (128 neurones) → Dropout → Dense → Sigmoid
- **Entrées** : Séquences de 30 mesures (température, humidité)
- **Sortie** : Score de risque [0, 1]
- **Seuils** : ≥ 0.3 = vigilance, ≥ 0.7 = alerte

Pour ré-entraîner :
```bash
python scripts/train_model.py
```

## Tests

```bash
pytest tests/ -v
```
