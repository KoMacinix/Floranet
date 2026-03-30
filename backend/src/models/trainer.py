"""
Entraînement du modèle LSTM pour la détection d'incendies.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class FireDataset(Dataset):
    """Dataset PyTorch pour séquences temporelles d'incendie."""

    def __init__(self, sequences, labels):
        self.sequences = torch.FloatTensor(sequences)
        self.labels = torch.FloatTensor(labels)

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return self.sequences[idx], self.labels[idx]


class ModelTrainer:
    """Entraîneur pour le modèle LSTM."""

    def __init__(self, model, device="auto"):
        self.model = model
        self.device = (
            torch.device("cuda" if torch.cuda.is_available() else "cpu")
            if device == "auto"
            else torch.device(device)
        )
        self.model.to(self.device)
        self.history = {
            "train_loss": [], "val_loss": [],
            "val_accuracy": [], "val_precision": [],
            "val_recall": [], "val_f1": [],
        }
        self.mean = None
        self.std = None
        logger.info("Trainer initialisé sur: %s", self.device)

    def prepare_data(self, sequences, labels, train_ratio=0.85, batch_size=64):
        """Normaliser et séparer les données en train/val."""
        self.mean = sequences.mean(axis=(0, 1))
        self.std = sequences.std(axis=(0, 1))
        sequences_norm = (sequences - self.mean) / (self.std + 1e-8)

        dataset = FireDataset(sequences_norm, labels)
        train_size = int(train_ratio * len(dataset))
        val_size = len(dataset) - train_size
        train_dataset, val_dataset = random_split(dataset, [train_size, val_size])

        self.train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        self.val_loader = DataLoader(val_dataset, batch_size=batch_size)

        logger.info("Données préparées: Train=%d, Val=%d", train_size, val_size)
        return self.train_loader, self.val_loader

    def train_epoch(self, optimizer, criterion):
        """Entraîner une époque."""
        self.model.train()
        total_loss = 0.0

        for sequences, labels in self.train_loader:
            sequences = sequences.to(self.device)
            labels = labels.to(self.device).unsqueeze(1)

            optimizer.zero_grad()
            outputs = self.model(sequences)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        return total_loss / len(self.train_loader)

    def validate(self):
        """Évaluer le modèle sur le jeu de validation."""
        self.model.eval()
        all_preds, all_labels = [], []
        total_loss = 0.0
        criterion = nn.BCELoss()

        with torch.no_grad():
            for sequences, labels in self.val_loader:
                sequences = sequences.to(self.device)
                labels_t = labels.to(self.device).unsqueeze(1)

                outputs = self.model(sequences)
                total_loss += criterion(outputs, labels_t).item()

                preds = (outputs > 0.5).float().cpu().numpy()
                all_preds.extend(preds)
                all_labels.extend(labels.numpy())

        all_preds = np.array(all_preds).flatten()
        all_labels = np.array(all_labels).flatten()

        return {
            "loss": total_loss / len(self.val_loader),
            "accuracy": float(np.mean(all_preds == all_labels)),
            "precision": precision_score(all_labels, all_preds, zero_division=0),
            "recall": recall_score(all_labels, all_preds, zero_division=0),
            "f1": f1_score(all_labels, all_preds, zero_division=0),
        }

    def train(self, num_epochs=50, learning_rate=0.001, save_path=None):
        """Boucle d'entraînement complète."""
        criterion = nn.BCELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        best_f1 = 0.0

        logger.info("Début entraînement: %d époques", num_epochs)

        for epoch in range(num_epochs):
            train_loss = self.train_epoch(optimizer, criterion)
            val = self.validate()

            self.history["train_loss"].append(train_loss)
            self.history["val_loss"].append(val["loss"])
            self.history["val_accuracy"].append(val["accuracy"])
            self.history["val_precision"].append(val["precision"])
            self.history["val_recall"].append(val["recall"])
            self.history["val_f1"].append(val["f1"])

            if (epoch + 1) % 10 == 0:
                logger.info(
                    "Epoch %d/%d — Loss: %.4f | Val: %.4f | Acc: %.2f%% | F1: %.2f%%",
                    epoch + 1, num_epochs, train_loss, val["loss"],
                    val["accuracy"] * 100, val["f1"] * 100,
                )

            if val["f1"] > best_f1:
                best_f1 = val["f1"]
                if save_path:
                    self.save_model(save_path, val)

        logger.info("Entraînement terminé — Meilleur F1: %.2f%%", best_f1 * 100)
        return self.history

    def save_model(self, path, metrics=None):
        """Sauvegarder le modèle et les paramètres de normalisation."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        checkpoint = {
            "model_state_dict": self.model.state_dict(),
            "normalization": {"mean": self.mean, "std": self.std},
        }
        if metrics:
            checkpoint["metrics"] = metrics

        torch.save(checkpoint, path)
        logger.info("Modèle sauvegardé: %s", path)
