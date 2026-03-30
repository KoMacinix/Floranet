# Base de données — Fire Detection System

## PostgreSQL (Docker)

Le système utilise PostgreSQL comme base de données principale, déployé via Docker.

### Démarrage du conteneur

```bash
docker run -d \
  --name floranet-db \
  -e POSTGRES_DB=fire_detection_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=ton_mot_de_passe \
  -p 5432:5432 \
  postgres:15
```

### Commandes utiles

```bash
docker start floranet-db       # Démarrer
docker stop floranet-db        # Arrêter
docker ps                      # Vérifier le statut
docker logs floranet-db        # Voir les logs
```

### Schéma

Le fichier `init.sql` crée les tables suivantes :

| Table                | Description                                       |
|----------------------|---------------------------------------------------|
| `sensors`            | Capteurs enregistrés (id, zone, coordonnées GPS)  |
| `measurements`       | Mesures temps réel (temp, humidité, score risque)  |
| `alerts`             | Alertes déclenchées par le modèle LSTM             |
| `training_history`   | Métriques d'entraînement par époque                |
| `confusion_matrix`   | Résultats de la matrice de confusion               |

### Initialisation des tables

```bash
cd backend
python scripts/init_database.py
```

### Accès avec DBeaver

| Paramètre      | Valeur               |
|----------------|----------------------|
| Hôte           | `localhost`          |
| Port           | `5432`               |
| Base de données| `fire_detection_db`  |
| Utilisateur    | `postgres`           |
| Mot de passe   | `ton_mot_de_passe`   |

### Diagramme

Voir `schema.png` pour le diagramme entité-relation.
