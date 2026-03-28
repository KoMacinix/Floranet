# Frontend — Surveillance Incendies Forestiers

Dashboard web en temps réel pour visualiser les données des capteurs LoRa et les prédictions du modèle LSTM.

## Architecture

```
frontend/
├── .env                     # Configuration (URL backend)
├── .env.example             # Template
├── .gitignore
├── package.json             # Scripts npm
├── README.md
│
└── src/
    ├── index.html           # Page principale
    ├── css/
    │   └── style.css        # Styles du dashboard
    └── js/
        ├── app.js           # Point d'entrée — orchestre les composants
        ├── services/
        │   └── api.js       # Appels HTTP vers le backend FastAPI
        └── components/
            ├── map.js         # Carte Leaflet + marqueurs
            ├── sensorList.js  # Liste des capteurs (sidebar gauche)
            └── detailPanel.js # Détails d'un capteur (sidebar droite)
```

## Technologies

- **HTML / CSS / JavaScript** (ES Modules, pas de framework)
- **Leaflet.js** — Carte interactive OpenStreetMap
- **API REST** — Communication avec le backend FastAPI

## Prérequis

- **Node.js 18+** (pour le serveur de développement)
- **Backend** lancé sur `http://127.0.0.1:8000`

## Installation

```bash
cd frontend
npm install
```

## Lancement

```bash
npm run dev
```

Le dashboard sera accessible sur `http://localhost:3000`.

## Fonctionnalités

- **Carte interactive** — Marqueurs colorés par statut (vert/orange/rouge)
- **Liste des capteurs** — Sidebar gauche avec température, humidité et score de risque
- **Panneau de détails** — Sidebar droite avec métriques détaillées et barres de progression
- **Bannière d'alerte** — S'affiche automatiquement quand un capteur est en alerte
- **Rafraîchissement automatique** — Toutes les 5 secondes via l'API

## Connexion avec le backend

Le frontend appelle l'API backend sur les endpoints suivants :

| Endpoint              | Usage                                    |
|-----------------------|------------------------------------------|
| `GET /api/sensors`    | Données de tous les capteurs + risque IA |
| `GET /api/sensors/X`  | Données d'un capteur spécifique          |
| `GET /api/history/X`  | Historique d'un capteur                  |
| `GET /api/status`     | Statut global du système                 |

L'URL du backend est configurée dans `src/js/services/api.js` et dans `.env`.
