# 🔥 Système de Détection d'Incendies Forestiers

Système intelligent de surveillance d'incendies forestiers en temps réel, utilisant des capteurs **LoRa/ESP32** et un modèle de deep learning **LSTM** pour la prédiction de risques.

**Institution :** Collège La Cité, Ottawa  
**Date :** Mars 2026

## Vue d'ensemble

```
Capteurs BME280/ESP32  →  Passerelle LoRa  →  API FastAPI (LSTM)  →  Dashboard Web
    (3 nœuds)              (Heltec V2)         + PostgreSQL           (Leaflet.js)
```

- **3 capteurs** distribués en forêt (température, humidité, pression)
- **Communication LoRa** P2P avec TDMA synchronisé
- **Modèle LSTM** (3 couches, 331K paramètres) pour la prédiction de risque
- **Dashboard web** temps réel avec carte interactive

## Structure du projet

```
├── backend/                 # API FastAPI + modèle LSTM + PostgreSQL
│   ├── src/                 # Code source (api, routes, services, models)
│   ├── db/                  # Schéma SQL + documentation DB
│   ├── scripts/             # Init DB, entraînement, génération de données
│   ├── data/                # Datasets, modèle entraîné, logs
│   ├── tests/               # Tests unitaires
│   ├── config.yaml          # Configuration non-secrète
│   ├── .env                 # Secrets (à ne pas commiter)
│   ├── requirements.txt     # Dépendances Python
│   └── README.md
│
├── frontend/                # Dashboard web
│   ├── src/                 # HTML, CSS, JS (modules ES6)
│   │   ├── index.html
│   │   ├── css/style.css
│   │   └── js/              # app.js, services/, components/
│   ├── .env                 # Configuration frontend
│   ├── package.json         # Scripts npm
│   └── README.md
│
└── embedded/                # Firmware LoRa/ESP32 (PlatformIO)
    ├── gateway/             # Passerelle LoRa (réception + forwarding)
    │   ├── src/             # LoraWebServer_Gateway.cpp
    │   └── platformio.ini
    ├── node/                # Capteur LoRa (envoi mesures BME280)
    │   ├── src/             # LoraTempSensor_Node.cpp
    │   ├── lib/Temperature/ # Bibliothèque capteur
    │   └── platformio.ini
    ├── tools/               # Logger série, analyse matplotlib
    └── README.md
```

## Démarrage rapide

### 1. Backend

```bash
cd backend

# Environnement Python
python -m venv .venv
source .venv/bin/activate     # Linux/Mac
# .venv\Scripts\activate      # Windows
pip install -r requirements.txt

# Base de données
psql -U postgres -c "CREATE DATABASE fire_detection_db;"
python scripts/init_database.py

# Lancer l'API
uvicorn src.api.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

### Accès

| Service        | URL                            |
|----------------|--------------------------------|
| API Backend    | http://localhost:8000           |
| Swagger (docs) | http://localhost:8000/docs      |
| Dashboard      | http://localhost:3000            |

## Endpoints API

| Méthode | Route                 | Description                               |
|---------|-----------------------|-------------------------------------------|
| GET     | `/api/sensors`        | Données de tous les capteurs + risque IA  |
| GET     | `/api/sensors/{id}`   | Données d'un capteur spécifique           |
| POST    | `/api/sensors/data`   | Recevoir des données du gateway LoRa      |
| GET     | `/api/history/{id}`   | Historique d'un capteur                   |
| GET     | `/api/status`         | Statut global du système                  |

## Technologies

| Couche       | Technologies                                       |
|--------------|-----------------------------------------------------|
| Embarqué     | ESP32 (Heltec WiFi LoRa 32 V2), BME280, LoRa P2P  |
| Backend      | Python, FastAPI, PyTorch (LSTM), PostgreSQL          |
| Frontend     | HTML/CSS/JS, Leaflet.js                              |
| DevOps       | Docker (optionnel), pytest                           |
