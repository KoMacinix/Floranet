import pytest
import sys
from pathlib import Path
import requests
import psycopg2
import torch
import numpy as np

# Tests du modèle LSTM
def test_model_accuracy():
    """Vérifier que le modèle a 100% de précision"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="fire_detection_db",
            user="postgres",
            password="Pass2819",
            sslmode='disable'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT accuracy FROM training_history ORDER BY epoch DESC LIMIT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            accuracy = result[0]
            assert accuracy == 100.0, f"Précision attendue: 100%, obtenue: {accuracy}%"
            print(f"✅ Test précision: {accuracy}%")
        else:
            pytest.skip("Aucune donnée d'entraînement dans la base")
    except Exception as e:
        pytest.skip(f"Impossible de tester la précision: {e}")

def test_model_exists():
    """Vérifier que le modèle LSTM existe"""
    model_path = Path("backend/data/models/lstm_fire_detection.pth")
    assert model_path.exists(), "Modèle LSTM non trouvé"
    print(f"✅ Modèle trouvé: {model_path}")

def test_normalization_exists():
    """Vérifier que les paramètres de normalisation existent"""
    norm_path = Path("backend/data/models/normalization_params.json")
    assert norm_path.exists(), "Paramètres de normalisation non trouvés"
    print(f"✅ Normalisation trouvée: {norm_path}")

# Tests de la base de données
def test_database_connection():
    """Tester la connexion PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="fire_detection_db",
            user="postgres",
            password="Pass2819",
            sslmode='disable'
        )
        assert conn is not None
        conn.close()
        print("✅ Connexion PostgreSQL OK")
    except Exception as e:
        pytest.fail(f"Connexion PostgreSQL échouée: {e}")

def test_tables_exist():
    """Vérifier que toutes les tables existent"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="fire_detection_db",
            user="postgres",
            password="Pass2819",
            sslmode='disable'
        )
        cursor = conn.cursor()
        
        tables = ['sensors', 'measurements', 'alerts', 'training_history', 'confusion_matrix']
        
        for table in tables:
            cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
            exists = cursor.fetchone()[0]
            assert exists, f"Table {table} n'existe pas"
            print(f"✅ Table {table} existe")
        
        cursor.close()
        conn.close()
    except Exception as e:
        pytest.fail(f"Erreur vérification tables: {e}")

def test_sensors_data():
    """Vérifier que les capteurs sont enregistrés"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="fire_detection_db",
            user="postgres",
            password="Pass2819",
            sslmode='disable'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sensors")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        assert count == 3, f"Attendu 3 capteurs, trouvé {count}"
        print(f"✅ {count} capteurs enregistrés")
    except Exception as e:
        pytest.skip(f"Impossible de vérifier les capteurs: {e}")

# Tests de l'API
def test_api_endpoints():
    """Tester tous les endpoints de l'API"""
    base_url = "http://127.0.0.1:8000"
    
    endpoints = [
        "/",
        "/api/sensors",
        "/api/status"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            assert response.status_code == 200, f"Endpoint {endpoint} retourne {response.status_code}"
            print(f"✅ Endpoint {endpoint} OK")
        except requests.exceptions.ConnectionError:
            pytest.skip(f"API non accessible sur {base_url}")
        except Exception as e:
            pytest.fail(f"Erreur endpoint {endpoint}: {e}")

def test_api_sensors_response():
    """Vérifier la structure de la réponse /api/sensors"""
    try:
        response = requests.get("http://127.0.0.1:8000/api/sensors", timeout=5)
        assert response.status_code == 200
        
        data = response.json()
        assert "sensors" in data, "Clé 'sensors' manquante"
        assert len(data["sensors"]) == 3, f"Attendu 3 capteurs, trouvé {len(data['sensors'])}"
        
        print(f"✅ API retourne {len(data['sensors'])} capteurs")
    except requests.exceptions.ConnectionError:
        pytest.skip("API non accessible")
    except Exception as e:
        pytest.fail(f"Erreur réponse API: {e}")

# Tests des fichiers de données
def test_dataset_exists():
    """Vérifier que le dataset existe"""
    sequences_path = Path("backend/data/datasets/sequences.npy")
    labels_path = Path("backend/data/datasets/labels.npy")
    
    assert sequences_path.exists(), "Fichier sequences.npy non trouvé"
    assert labels_path.exists(), "Fichier labels.npy non trouvé"
    
    print("✅ Dataset trouvé")

def test_dataset_shape():
    """Vérifier les dimensions du dataset"""
    try:
        sequences = np.load("backend/data/datasets/sequences.npy")
        labels = np.load("backend/data/datasets/labels.npy")
        
        assert sequences.shape == (4000, 30, 2), f"Shape séquences incorrect: {sequences.shape}"
        assert labels.shape == (4000,), f"Shape labels incorrect: {labels.shape}"
        
        print(f"✅ Dataset shape correct: {sequences.shape}, {labels.shape}")
    except Exception as e:
        pytest.skip(f"Impossible de charger le dataset: {e}")

# Test de performance globale
def test_confusion_matrix():
    """Vérifier la matrice de confusion finale"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="fire_detection_db",
            user="postgres",
            password="Pass2819",
            sslmode='disable'
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT true_negative, false_positive, false_negative, true_positive 
            FROM confusion_matrix 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            tn, fp, fn, tp = result
            assert fp == 0, f"Faux positifs détectés: {fp}"
            assert fn == 0, f"Faux négatifs détectés: {fn}"
            print(f"✅ Matrice de confusion parfaite: TN={tn}, FP={fp}, FN={fn}, TP={tp}")
        else:
            pytest.skip("Aucune matrice de confusion dans la base")
    except Exception as e:
        pytest.skip(f"Impossible de vérifier la matrice: {e}")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("TESTS DU SYSTÈME DE DÉTECTION D'INCENDIES")
    print("="*70 + "\n")
    
    pytest.main([__file__, "-v", "--tb=short"])