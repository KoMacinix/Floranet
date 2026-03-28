# Base de données — Fire Detection System

## PostgreSQL

Le système utilise PostgreSQL comme base de données principale pour stocker les mesures des capteurs, les alertes et l'historique d'entraînement du modèle.

### Schéma

Le fichier `init.sql` crée les tables suivantes :

| Table                | Description                                       |
|----------------------|---------------------------------------------------|
| `sensors`            | Capteurs enregistrés (id, zone, coordonnées GPS)  |
| `measurements`       | Mesures temps réel (temp, humidité, score risque)  |
| `alerts`             | Alertes déclenchées par le modèle LSTM             |
| `training_history`   | Métriques d'entraînement par époque                |
| `confusion_matrix`   | Résultats de la matrice de confusion               |

### Installation

1. Installer PostgreSQL 15+
2. Créer la base de données :
   ```sql
   psql -U postgres
   CREATE DATABASE fire_detection_db;
   ```
3. Exécuter le script d'initialisation :
   ```bash
   psql -U postgres -d fire_detection_db -f db/init.sql
   ```

Ou utiliser le script Python :
```bash
python scripts/init_database.py
```

### Diagramme

Voir `schema.png` pour le diagramme entité-relation.
