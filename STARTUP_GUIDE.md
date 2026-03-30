# Guide de démarrage — Floranet (étape par étape)

## Architecture du flux de données

```
[Node 1] ──LoRa──┐
[Node 2] ──LoRa──┤──→ [Gateway ESP32] ──HTTP──→ [Bridge Python] ──POST──→ [Backend FastAPI]
[Node 3] ──LoRa──┘     (WiFi: KoNaw)            (sur le PC)               (port 8000)
                                                                                │
                                                                           [PostgreSQL]
                                                                           (Docker:5432)
                                                                                │
                                                                       [Frontend Dashboard]
                                                                         (port 3000)
```

---

## Prérequis (une seule fois)

### PostgreSQL (Docker)

```bash
docker run -d \
  --name floranet-db \
  -e POSTGRES_DB=fire_detection_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=ton_mot_de_passe \
  -p 5432:5432 \
  postgres:15
```

Vérifier que le conteneur tourne :
```bash
docker ps
```

**Connexion avec DBeaver :**
- Hôte : `localhost`
- Port : `5432`
- Base : `fire_detection_db`
- Utilisateur : `postgres`
- Mot de passe : `ton_mot_de_passe`

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/init_database.py
```

Après `init_database.py`, tu peux vérifier dans DBeaver que les 5 tables
ont été créées (sensors, measurements, alerts, training_history, confusion_matrix)
et que les 3 capteurs sont insérés dans `sensors`.

### Frontend

```bash
cd frontend
npm install
```

---

## Démarrage (à chaque session)

### Étape 0 — Démarrer PostgreSQL (si le conteneur est arrêté)

```bash
docker start floranet-db
```

Vérifier : `docker ps` doit montrer `floranet-db` avec le statut `Up`.

### Ouvrir 4 terminaux dans VSCode (Terminal > New Terminal)

### Terminal 1 — Backend API

```bash
cd backend
.venv\Scripts\activate
uvicorn src.api.main:app --reload --port 8000
```

Vérifier : ouvrir http://127.0.0.1:8000 dans le navigateur.
Tu dois voir le JSON de bienvenue avec les infos du modèle LSTM.

### Terminal 2 — Frontend Dashboard

```bash
cd frontend
npm run dev
```

Vérifier : ouvrir http://localhost:3000 dans le navigateur.
Le dashboard s'affiche (les données seront vides pour l'instant).

### Terminal 3 — Gateway Serial Monitor (trouver l'IP)

1. Brancher le gateway en USB
2. Dans le terminal :
   ```bash
   cd embedded/gateway
   pio device monitor --baud 115200
   ```
3. Chercher la ligne :
   ```
   ✅ WiFi OK
   📍 IP: 192.168.X.X      ← NOTER CETTE ADRESSE
   ```

### Terminal 4 — Bridge (le pont gateway → backend)

```bash
cd embedded/tools
python bridge.py --gateway http://192.168.X.X --backend http://127.0.0.1:8000 --interval 6
```

(Remplacer `192.168.X.X` par l'IP réelle du gateway)

### Allumer les nœuds

Brancher les 3 nœuds (batterie ou USB). Ils vont se synchroniser
automatiquement avec le gateway via TDMA.

---

## Vérification — tout fonctionne ?

| Vérification                        | Comment                                          |
|-------------------------------------|--------------------------------------------------|
| Docker tourne ?                     | `docker ps` → floranet-db Up                     |
| Backend tourne ?                    | http://127.0.0.1:8000 → JSON de bienvenue        |
| Gateway reçoit les nœuds ?          | Serial Monitor → messages "📦 Node X [TDMA 18s]" |
| Bridge tourne ?                     | Terminal 4 → "Node X: 23.5°C ..."                |
| Dashboard affiche les données ?     | http://localhost:3000 → marqueurs sur la carte    |
| DB reçoit les mesures ?             | http://127.0.0.1:8000/api/status → total > 0     |
| DBeaver voit les données ?          | SELECT * FROM measurements ORDER BY id DESC       |

---

## Commandes Docker utiles

```bash
docker start floranet-db       # Démarrer le conteneur
docker stop floranet-db        # Arrêter le conteneur
docker ps                      # Voir les conteneurs actifs
docker logs floranet-db        # Voir les logs PostgreSQL
```

---

## Dépannage

**"Connection refused" sur le backend**
→ Vérifier que Docker tourne : `docker ps`
→ Si le conteneur est arrêté : `docker start floranet-db`

**"Gateway inaccessible"**
→ Le PC et le gateway doivent être sur le même réseau WiFi (KoNaw)
→ Vérifier l'IP du gateway dans le Serial Monitor

**"Backend non disponible"**
→ Lancer le terminal 1 d'abord (uvicorn)

**"Capteur non trouvé: sensor_X"**
→ Le backend attend sensor_1, sensor_2, sensor_3
→ Le bridge fait la conversion automatiquement (Node 1 → sensor_1)

**Dashboard vide / pas de données**
→ Attendre ~30 secondes (le modèle LSTM a besoin de remplir sa fenêtre)
→ Vérifier que le bridge tourne ET que les nœuds sont allumés

**Le modèle donne toujours 0% de risque**
→ C'est normal en conditions normales (temp < 40°C, humidité > 30%)
→ Le risque augmente quand la température monte ou l'humidité descend

**DBeaver ne se connecte pas**
→ Vérifier que Docker tourne (`docker ps`)
→ Vérifier les identifiants (host: localhost, port: 5432, db: fire_detection_db)
