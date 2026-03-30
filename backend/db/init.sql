-- =============================================================================
-- Schéma de la base de données — Floranet
-- PostgreSQL 15+
-- =============================================================================

-- =============================================================================
-- TABLE: sensors
-- =============================================================================
CREATE TABLE IF NOT EXISTS sensors (
    id              SERIAL PRIMARY KEY,
    sensor_id       VARCHAR(50) UNIQUE NOT NULL,
    name            VARCHAR(50),
    zone            VARCHAR(100),
    latitude        FLOAT,
    longitude       FLOAT,
    sensor_type     VARCHAR(20) DEFAULT 'dht22',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- TABLE: measurements — Mesures temps réel (synchronisées TDMA)
-- =============================================================================
CREATE TABLE IF NOT EXISTS measurements (
    id              SERIAL PRIMARY KEY,
    sensor_id       VARCHAR(50) REFERENCES sensors(sensor_id),
    temperature     FLOAT,
    humidity        FLOAT,
    pressure        FLOAT,
    -- Nœud 3 (MQ-2) — Capteur fumée
    smoke_level     INTEGER,                  -- Valeur analogique brute (0-1023)
    smoke_trigger   BOOLEAN DEFAULT FALSE,    -- Déclenchement seuil numérique
    -- Connectivité réseau
    rssi            INTEGER,                  -- Signal radio (dBm)
    -- IA
    risk_score      FLOAT,
    -- Métadonnées TDMA
    tdma_slot       INTEGER,                  -- Créneau TDMA (1,2,3)
    packet_received BOOLEAN DEFAULT TRUE,     -- Paquet réellement reçu
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_measurements_sensor_id
    ON measurements(sensor_id);
CREATE INDEX IF NOT EXISTS idx_measurements_timestamp
    ON measurements(timestamp DESC);

-- =============================================================================
-- TABLE: node_status — État de connexion des nœuds (Watchdog)
-- =============================================================================
CREATE TABLE IF NOT EXISTS node_status (
    sensor_id           VARCHAR(50) PRIMARY KEY REFERENCES sensors(sensor_id),
    last_seen           TIMESTAMP,
    is_connected        BOOLEAN DEFAULT FALSE,
    consecutive_missed  INTEGER DEFAULT 0,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- TABLE: alerts
-- =============================================================================
CREATE TABLE IF NOT EXISTS alerts (
    id              SERIAL PRIMARY KEY,
    sensor_id       VARCHAR(50) REFERENCES sensors(sensor_id),
    risk_score      FLOAT,
    temperature     FLOAT,
    humidity        FLOAT,
    smoke_level     INTEGER,
    smoke_trigger   BOOLEAN DEFAULT FALSE,
    alert_type      VARCHAR(20),
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged    BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_alerts_sensor_id
    ON alerts(sensor_id);
CREATE INDEX IF NOT EXISTS idx_alerts_unacknowledged
    ON alerts(acknowledged) WHERE acknowledged = FALSE;

-- =============================================================================
-- TABLE: training_history
-- =============================================================================
CREATE TABLE IF NOT EXISTS training_history (
    id              SERIAL PRIMARY KEY,
    epoch           INTEGER NOT NULL,
    train_loss      FLOAT,
    val_loss        FLOAT,
    accuracy        FLOAT,
    precision_score FLOAT,
    recall          FLOAT,
    f1_score        FLOAT,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- TABLE: confusion_matrix
-- =============================================================================
CREATE TABLE IF NOT EXISTS confusion_matrix (
    id              SERIAL PRIMARY KEY,
    true_negative   INTEGER,
    false_positive  INTEGER,
    false_negative  INTEGER,
    true_positive   INTEGER,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- DONNÉES INITIALES
-- =============================================================================
INSERT INTO sensors (sensor_id, name, zone, latitude, longitude, sensor_type) VALUES
    ('sensor_1', 'LoRa nœud 1', 'Sud-Ouest', 45.52, -73.60, 'dht22'),
    ('sensor_2', 'LoRa nœud 2', 'Centre',    45.51, -73.55, 'dht22'),
    ('sensor_3', 'LoRa nœud 3', 'Nord',      45.53, -73.56, 'mq2'),
    ('gateway',  'Passerelle LoRa', 'Base',   45.515, -73.575, 'gateway')
ON CONFLICT (sensor_id) DO NOTHING;

-- Initialiser les statuts des nœuds
INSERT INTO node_status (sensor_id, last_seen, is_connected, consecutive_missed)
    SELECT sensor_id, NULL, FALSE, 0 FROM sensors WHERE sensor_id != 'gateway'
ON CONFLICT (sensor_id) DO NOTHING;
