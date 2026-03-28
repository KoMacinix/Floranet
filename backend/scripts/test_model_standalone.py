"""
Test du modèle LSTM indépendamment
Démontre que le modèle fonctionne sans API/Frontend
"""

import sys
from pathlib import Path
import numpy as np
import torch
import json

# Ajouter le chemin src au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from models.lstm_model import FireDetectionModel

def load_model_and_params():
    """Charge le modèle LSTM et les paramètres de normalisation"""
    
    model_path = Path(__file__).parent.parent / 'data' / 'models' / 'lstm_fire_detection.pth'
    norm_path = Path(__file__).parent.parent / 'data' / 'models' / 'normalization_params.json'
    
    print("="*70)
    print("CHARGEMENT DU MODÈLE LSTM")
    print("="*70)
    
    # Charger paramètres normalisation
    with open(norm_path, 'r') as f:
        norm_params = json.load(f)
    
    print(f"\n[OK] Normalisation chargée:")
    print(f"  Mean Temp: {norm_params['mean'][0]:.2f}°C")
    print(f"  Mean Hum:  {norm_params['mean'][1]:.2f}%")
    print(f"  Std Temp:  {norm_params['std'][0]:.2f}")
    print(f"  Std Hum:   {norm_params['std'][1]:.2f}")
    
    # Créer modèle
    config = {
        'input_dim': 2,
        'hidden_dim': 128,
        'num_layers': 3,
        'dropout': 0.3
    }
    
    model = FireDetectionModel(config)
    model.load_model(str(model_path))
    
    print(f"\n[OK] Modèle LSTM chargé:")
    print(f"  Paramètres: {sum(p.numel() for p in model.model.parameters()):,}")
    print(f"  Couches: {config['num_layers']} LSTM")
    print(f"  Neurones/couche: {config['hidden_dim']}")
    
    return model, norm_params

def normalize_sequence(sequence, norm_params):
    """Normalise une séquence avec les paramètres sauvegardés"""
    mean = np.array(norm_params['mean'])
    std = np.array(norm_params['std'])
    return (sequence - mean) / std

def generate_scenario(scenario_type):
    """Génère une séquence de test selon le scénario"""
    
    if scenario_type == "normal":
        # Conditions normales : 18-28°C, 40-70% humidité
        temps = np.random.uniform(18, 28, 30)
        hums = np.random.uniform(40, 70, 30)
        description = "Conditions NORMALES (18-28°C, 40-70% humidité)"
        
    elif scenario_type == "vigilance":
        # Vigilance : 28-40°C, 20-40% humidité
        temps = np.random.uniform(28, 40, 30)
        hums = np.random.uniform(20, 40, 30)
        description = "Conditions VIGILANCE (28-40°C, 20-40% humidité)"
        
    elif scenario_type == "alerte":
        # Alerte incendie : 50-90°C, 10-25% humidité
        temps = np.random.uniform(50, 90, 30)
        hums = np.random.uniform(10, 25, 30)
        description = "Conditions ALERTE INCENDIE (50-90°C, 10-25% humidité)"
        
    elif scenario_type == "feu_lent":
        # Feu qui démarre lentement
        temps = np.concatenate([
            np.random.uniform(20, 25, 10),  # Normal au début
            np.random.uniform(30, 45, 10),  # Augmente
            np.random.uniform(50, 70, 10)   # Feu confirmé
        ])
        hums = np.concatenate([
            np.random.uniform(50, 60, 10),
            np.random.uniform(35, 45, 10),
            np.random.uniform(15, 25, 10)
        ])
        description = "FEU LENT (montée progressive température)"
        
    elif scenario_type == "feu_rapide":
        # Feu qui démarre rapidement
        temps = np.concatenate([
            np.random.uniform(22, 26, 5),   # Normal
            np.random.uniform(55, 85, 25)   # Feu soudain
        ])
        hums = np.concatenate([
            np.random.uniform(45, 55, 5),
            np.random.uniform(12, 22, 25)
        ])
        description = "FEU RAPIDE (démarrage soudain)"
    
    else:
        raise ValueError(f"Scénario inconnu: {scenario_type}")
    
    sequence = np.stack([temps, hums], axis=1)
    return sequence, description

def test_scenario(model, norm_params, scenario_type):
    """Teste un scénario et affiche le résultat"""
    
    # Générer séquence
    sequence, description = generate_scenario(scenario_type)
    
    # Normaliser
    normalized = normalize_sequence(sequence, norm_params)
    
    # Prédire
    risk_score = model.predict(normalized)
    
    # Déterminer statut
    if risk_score < 0.3:
        status = "NORMAL"
        emoji = "🟢"
    elif risk_score < 0.7:
        status = "VIGILANCE"
        emoji = "🟠"
    else:
        status = "ALERTE INCENDIE"
        emoji = "🔴"
    
    # Afficher résultats
    print(f"\n{'-'*70}")
    print(f"SCÉNARIO: {description}")
    print(f"{'-'*70}")
    print(f"Température moyenne: {sequence[:, 0].mean():.1f}°C (min: {sequence[:, 0].min():.1f}, max: {sequence[:, 0].max():.1f})")
    print(f"Humidité moyenne:    {sequence[:, 1].mean():.1f}% (min: {sequence[:, 1].min():.1f}, max: {sequence[:, 1].max():.1f})")
    print(f"\n{emoji} PRÉDICTION IA: {risk_score*100:.2f}% risque d'incendie")
    print(f"{emoji} STATUT: {status}")
    
    return risk_score

def interactive_test(model, norm_params):
    """Mode interactif pour tester des valeurs personnalisées"""
    
    print("\n" + "="*70)
    print("MODE INTERACTIF - TEST PERSONNALISÉ")
    print("="*70)
    
    print("\nEntrez les conditions (30 mesures identiques seront générées):")
    
    try:
        temp = float(input("Température (°C): "))
        hum = float(input("Humidité (%): "))
        
        # Créer séquence avec valeurs constantes
        sequence = np.array([[temp, hum]] * 30)
        
        # Normaliser et prédire
        normalized = normalize_sequence(sequence, norm_params)
        risk_score = model.predict(normalized)
        
        # Afficher résultat
        if risk_score < 0.3:
            status = "NORMAL"
            emoji = "🟢"
        elif risk_score < 0.7:
            status = "VIGILANCE"
            emoji = "🟠"
        else:
            status = "ALERTE INCENDIE"
            emoji = "🔴"
        
        print(f"\n{emoji} PRÉDICTION IA: {risk_score*100:.2f}% risque")
        print(f"{emoji} STATUT: {status}")
        
    except ValueError:
        print("\n[ERREUR] Valeurs invalides")

def main():
    """Fonction principale"""
    
    print("\n")
    print("█" * 70)
    print("  TEST INDÉPENDANT DU MODÈLE LSTM - DÉTECTION D'INCENDIES")
    print("█" * 70)
    print("\n")
    
    # Charger modèle
    model, norm_params = load_model_and_params()
    
    # Tester différents scénarios
    print("\n" + "="*70)
    print("TESTS AUTOMATIQUES - DIFFÉRENTS SCÉNARIOS")
    print("="*70)
    
    scenarios = [
        "normal",
        "vigilance", 
        "alerte",
        "feu_lent",
        "feu_rapide"
    ]
    
    results = {}
    for scenario in scenarios:
        risk = test_scenario(model, norm_params, scenario)
        results[scenario] = risk
    
    # Résumé
    print("\n" + "="*70)
    print("RÉSUMÉ DES TESTS")
    print("="*70)
    for scenario, risk in results.items():
        print(f"{scenario:15s} : {risk*100:6.2f}% risque")
    
    # Mode interactif (optionnel)
    print("\n")
    choice = input("Voulez-vous tester des valeurs personnalisées? (o/n): ")
    if choice.lower() == 'o':
        interactive_test(model, norm_params)
    
    print("\n" + "="*70)
    print("[TERMINÉ] Tests du modèle IA complétés avec succès!")
    print("="*70)
    print("\n")

if __name__ == "__main__":
    main()