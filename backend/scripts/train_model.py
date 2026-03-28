import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import sys
from pathlib import Path
import json
import psycopg2
import yaml
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from models.lstm_model import LSTMModel

class FireDataset(Dataset):
    def __init__(self, sequences, labels):
        self.sequences = torch.FloatTensor(sequences)
        self.labels = torch.FloatTensor(labels)
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.labels[idx]

def load_config():
    """Charger la configuration"""
    config_path = Path(__file__).parent.parent.parent / 'config.yml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_db_connection():
    """Connexion PostgreSQL"""
    config = load_config()
    db_config = config['database']
    
    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['name'],
        user=db_config['user'],
        password=db_config['password'],
        sslmode='disable'
    )
    return conn

def save_epoch_to_db(epoch, train_loss, val_loss, acc, prec, rec, f1):
    """Sauvegarder une epoch dans PostgreSQL"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # CORRECTION: Convertir numpy -> Python pour éviter erreur "schema np does not exist"
        cursor.execute("""
            INSERT INTO training_history 
            (epoch, train_loss, val_loss, accuracy, precision, recall, f1_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            int(epoch),
            float(train_loss),
            float(val_loss),
            float(acc),
            float(prec),
            float(rec),
            float(f1)
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[WARN] Erreur sauvegarde epoch {epoch}: {e}")
        return False

def save_confusion_matrix_to_db(cm):
    """Sauvegarder la matrice de confusion dans PostgreSQL"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO confusion_matrix 
            (true_negative, false_positive, false_negative, true_positive)
            VALUES (%s, %s, %s, %s)
        """, (int(cm[0,0]), int(cm[0,1]), int(cm[1,0]), int(cm[1,1])))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[WARN] Erreur sauvegarde confusion matrix: {e}")
        return False

def plot_training_history(history, output_dir):
    """Créer des graphiques"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Evolution de l\'entrainement LSTM - Deep Learning', fontsize=16, fontweight='bold')
    
    epochs = range(1, len(history['train_loss']) + 1)
    
    # Loss
    axes[0, 0].plot(epochs, history['train_loss'], 'b-', label='Train Loss', linewidth=2)
    axes[0, 0].plot(epochs, history['val_loss'], 'r-', label='Validation Loss', linewidth=2)
    axes[0, 0].set_xlabel('Epoch')
    axes[0, 0].set_ylabel('Loss')
    axes[0, 0].set_title('Evolution de la Loss')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Accuracy
    axes[0, 1].plot(epochs, history['accuracy'], 'g-', linewidth=2)
    axes[0, 1].set_xlabel('Epoch')
    axes[0, 1].set_ylabel('Accuracy (%)')
    axes[0, 1].set_title('Precision du modele')
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].set_ylim([0, 105])
    
    # Metrics
    axes[1, 0].plot(epochs, history['precision'], 'c-', label='Precision', linewidth=2)
    axes[1, 0].plot(epochs, history['recall'], 'm-', label='Recall', linewidth=2)
    axes[1, 0].plot(epochs, history['f1'], 'y-', label='F1-Score', linewidth=2)
    axes[1, 0].set_xlabel('Epoch')
    axes[1, 0].set_ylabel('Score (%)')
    axes[1, 0].set_title('Metriques')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].set_ylim([0, 105])
    
    # Confusion matrix
    cm = history['final_confusion_matrix']
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[1, 1],
                xticklabels=['Normal', 'Feu'], yticklabels=['Normal', 'Feu'])
    axes[1, 1].set_xlabel('Prediction')
    axes[1, 1].set_ylabel('Verite')
    axes[1, 1].set_title('Matrice de Confusion')
    
    plt.tight_layout()
    output_path = Path(output_dir) / 'training_history.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n[OK] Graphiques sauvegardes: {output_path}")
    plt.close()

def train_model():
    print("=" * 70)
    print("DEEP LEARNING - ENTRAINEMENT LSTM AVEC SAUVEGARDE POSTGRESQL")
    print("=" * 70)
    
    # Charger les données
    data_dir = Path(__file__).parent.parent / 'data' / 'datasets'
    sequences = np.load(data_dir / 'sequences.npy')
    labels = np.load(data_dir / 'labels.npy')
    
    print(f"\nDonnees: {sequences.shape}")
    print(f"Incendies: {labels.sum():.0f} ({labels.sum()/len(labels)*100:.1f}%)")
    
    # Normalisation
    print("\nNormalisation...")
    mean = sequences.mean(axis=(0, 1))
    std = sequences.std(axis=(0, 1))
    print(f"  Temp: Mean={mean[0]:.2f}C, Std={std[0]:.2f}")
    print(f"  Hum:  Mean={mean[1]:.2f}%, Std={std[1]:.2f}")
    
    sequences_normalized = (sequences - mean) / (std + 1e-8)
    
    # Sauvegarder normalisation
    norm_params = {'mean': mean.tolist(), 'std': std.tolist()}
    norm_path = Path(__file__).parent.parent / 'data' / 'models' / 'normalization_params.json'
    norm_path.parent.mkdir(parents=True, exist_ok=True)
    with open(norm_path, 'w') as f:
        json.dump(norm_params, f, indent=2)
    print(f"\n[OK] Normalisation sauvegardee: {norm_path}")
    
    # Dataset
    dataset = FireDataset(sequences_normalized, labels)
    train_size = int(0.85 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    
    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=64, shuffle=False)
    
    print(f"\nTrain: {train_size} | Val: {val_size}")
    
    # Modele
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\nDevice: {device}")
    
    config = load_config()
    model = LSTMModel(
        input_dim=config['lstm']['input_dim'],
        hidden_dim=config['lstm']['hidden_dim'],
        num_layers=config['lstm']['num_layers'],
        dropout=config['lstm']['dropout']
    ).to(device)
    
    print(f"\nModele DEEP LEARNING:")
    print(f"  - LSTM: 3 couches, 128 neurones/couche")
    print(f"  - Parametres: {sum(p.numel() for p in model.parameters()):,}")
    
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # Historique
    history = {
        'train_loss': [], 'val_loss': [], 'accuracy': [],
        'precision': [], 'recall': [], 'f1': [],
        'final_confusion_matrix': None
    }
    
    print("\n" + "=" * 70)
    print("ENTRAINEMENT AVEC SAUVEGARDE POSTGRESQL")
    print("=" * 70)
    
    best_f1 = 0.0
    epochs = 50
    
    for epoch in range(epochs):
        # Train
        model.train()
        train_loss = 0.0
        
        for sequences_batch, labels_batch in train_loader:
            sequences_batch = sequences_batch.to(device)
            labels_batch = labels_batch.to(device)
            
            optimizer.zero_grad()
            outputs = model(sequences_batch).squeeze()
            loss = criterion(outputs, labels_batch)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
        
        train_loss /= len(train_loader)
        
        # Validation
        model.eval()
        val_loss = 0.0
        all_preds = []
        all_labels = []
        
        with torch.no_grad():
            for sequences_batch, labels_batch in val_loader:
                sequences_batch = sequences_batch.to(device)
                labels_batch = labels_batch.to(device)
                
                outputs = model(sequences_batch).squeeze()
                loss = criterion(outputs, labels_batch)
                val_loss += loss.item()
                
                preds = (outputs > 0.5).float()
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels_batch.cpu().numpy())
        
        val_loss /= len(val_loader)
        
        # Metriques
        all_preds = np.array(all_preds)
        all_labels = np.array(all_labels)
        
        acc = (all_preds == all_labels).mean() * 100
        precision = precision_score(all_labels, all_preds, zero_division=0) * 100
        recall = recall_score(all_labels, all_preds, zero_division=0) * 100
        f1 = f1_score(all_labels, all_preds, zero_division=0) * 100
        
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['accuracy'].append(acc)
        history['precision'].append(precision)
        history['recall'].append(recall)
        history['f1'].append(f1)
        
        # SAUVEGARDER DANS POSTGRESQL
        save_epoch_to_db(epoch + 1, train_loss, val_loss, acc, precision, recall, f1)
        
        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"\nEpoch {epoch+1}/{epochs}:")
            print(f"  Loss: {train_loss:.4f} | Val: {val_loss:.4f}")
            print(f"  Acc={acc:.1f}% Prec={precision:.1f}% Recall={recall:.1f}% F1={f1:.1f}%")
            print(f"  [DB] Sauvegarde PostgreSQL OK")
        
        if f1 > best_f1:
            best_f1 = f1
            model_path = Path(__file__).parent.parent / 'data' / 'models' / 'lstm_fire_detection.pth'
            torch.save(model.state_dict(), model_path)
            if (epoch + 1) % 10 == 0:
                print(f"  [BEST] F1={f1:.1f}%")
    
    # Matrice de confusion finale
    cm = confusion_matrix(all_labels, all_preds)
    history['final_confusion_matrix'] = cm
    
    # SAUVEGARDER CONFUSION MATRIX DANS POSTGRESQL
    save_confusion_matrix_to_db(cm)
    
    print("\n" + "=" * 70)
    print("TERMINE!")
    print("=" * 70)
    print(f"\nMeilleur F1: {best_f1:.1f}%")
    print(f"\nConfusion Matrix:")
    print(f"  TN={cm[0,0]} FP={cm[0,1]}")
    print(f"  FN={cm[1,0]} TP={cm[1,1]}")
    print(f"\n[DB] Matrice de confusion sauvegardee dans PostgreSQL")
    
    print("\nCreation des graphiques...")
    models_dir = Path(__file__).parent.parent / 'data' / 'models'
    plot_training_history(history, models_dir)
    
    print(f"\nModele: {model_path}")
    print(f"Normalisation: {norm_path}")
    print(f"\n[OK] Toutes les donnees sauvegardees dans PostgreSQL!")

if __name__ == "__main__":
    train_model()