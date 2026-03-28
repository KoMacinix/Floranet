-- =============================================================================
-- Schéma de la base de données — Système de Détection d'Incendies
-- PostgreSQL 15+
-- =============================================================================

-- Créer la base de données (exécuter séparément avec psql -U postgres)
-- CREATE DATABASE fire_detection_db;

-- =============================================================================
-- TABLE: sensors — Capteurs enregistrés
-- =============================================================================
CREATE TABLE IF NOT EXISTS sensors (
    id              SERIAL PRIMARY KEY,
    sensor_id       VARCHAR(50) UNIQUE NOT NULL,
    name            VARCHAR(50),
    zone            VARCHAR(100),
    latitude        FLOAT,
    longitude       FLOAT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- TABLE: measurements — Mesures temps réel
-- =============================================================================
CREATE TABLE IF NOT EXISTS measurements (
    id              SERIAL PRIMARY KEY,
    sensor_id       VARCHAR(50) REFERENCES sensors(sensor_id),
    temperature     FLOAT,
    humidity        FLOAT,
    risk_score      FLOAT,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_measurements_sensor_id
    ON measurements(sensor_id);
CREATE INDEX IF NOT EXISTS idx_measurements_timestamp
    ON measurements(timestamp DESC);

-- =============================================================================
-- TABLE: alerts — Alertes déclenchées
-- =============================================================================
CREATE TABLE IF NOT EXISTS alerts (
    id              SERIAL PRIMARY KEY,
    sensor_id       VARCHAR(50) REFERENCES sensors(sensor_id),
    risk_score      FLOAT,
    temperature     FLOAT,
    humidity        FLOAT,
    alert_type      VARCHAR(20),        -- 'warning' | 'alert'
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged    BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_alerts_sensor_id
    ON alerts(sensor_id);
CREATE INDEX IF NOT EXISTS idx_alerts_unacknowledged
    ON alerts(acknowledged) WHERE acknowledged = FALSE;

-- =============================================================================
-- TABLE: training_history — Historique d'entraînement du modèle LSTM
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
-- TABLE: confusion_matrix — Résultats de la matrice de confusion
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
-- DONNÉES INITIALES — Capteurs
-- =============================================================================
INSERT INTO sensors (sensor_id, name, zone, latitude, longitude) VALUES
    ('sensor_1', 'S-001', 'Sud-Ouest', 45.52, -73.60),
    ('sensor_2', 'S-002', 'Centre',    45.51, -73.55),
    ('sensor_3', 'S-003', 'Nord',      45.53, -73.56)
ON CONFLICT (sensor_id) DO NOTHING;
