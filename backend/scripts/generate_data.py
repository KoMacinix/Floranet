import numpy as np
import random
from pathlib import Path

class DataGenerator:
    def __init__(self):
        self.window_size = 30
        self.sequences = []
        self.labels = []
    
    def generate_normal_sequence(self):
        """Sequence normale - pas de feu"""
        sequence = []
        base_temp = random.uniform(18, 28)
        base_humidity = random.uniform(55, 75)
        
        for _ in range(self.window_size):
            temp = base_temp + random.uniform(-2, 2)
            humidity = base_humidity + random.uniform(-5, 5)
            sequence.append([temp, humidity])
        
        return sequence, 0  # Label: 0 = pas de feu
    
    def generate_false_alarm(self):
        """Fausse alerte - chaleur mais pas d'incendie"""
        sequence = []
        base_temp = random.uniform(28, 38)
        base_humidity = random.uniform(40, 60)
        
        for _ in range(self.window_size):
            temp = base_temp + random.uniform(-3, 3)
            humidity = base_humidity + random.uniform(-8, 8)
            sequence.append([temp, humidity])
        
        return sequence, 0  # Label: 0 = pas de feu
    
    def generate_slow_fire(self):
        """Feu lent - progression graduelle"""
        sequence = []
        start_temp = random.uniform(22, 28)
        start_humidity = random.uniform(55, 70)
        
        for i in range(self.window_size):
            progress = i / self.window_size
            temp = start_temp + (progress * random.uniform(25, 40))
            humidity = start_humidity - (progress * random.uniform(20, 35))
            sequence.append([temp, humidity])
        
        return sequence, 1  # Label: 1 = feu
    
    def generate_fast_fire(self):
        """Feu rapide - explosion"""
        sequence = []
        start_temp = random.uniform(20, 25)
        start_humidity = random.uniform(50, 65)
        
        for i in range(self.window_size):
            if i < 20:
                # Normal
                temp = start_temp + random.uniform(-2, 2)
                humidity = start_humidity + random.uniform(-5, 5)
            else:
                # Explosion soudaine
                progress = (i - 20) / 10
                temp = start_temp + (progress * random.uniform(35, 50))
                humidity = start_humidity - (progress * random.uniform(25, 40))
            
            sequence.append([temp, humidity])
        
        return sequence, 1  # Label: 1 = feu
    
    def generate_intense_fire(self):
        """Feu intense - haute temperature constante"""
        sequence = []
        fire_temp = random.uniform(50, 70)
        fire_humidity = random.uniform(15, 35)
        
        for _ in range(self.window_size):
            temp = fire_temp + random.uniform(-5, 5)
            humidity = fire_humidity + random.uniform(-5, 5)
            sequence.append([temp, humidity])
        
        return sequence, 1  # Label: 1 = feu
    
    def generate_dataset(self, n_normal=1500, n_false=500, n_fires=2000):
        """Generer le dataset complet"""
        print("=" * 70)
        print("GENERATION DU DATASET")
        print("=" * 70)
        
        # Sequences normales
        print(f"Generation de {n_normal} sequences normales...")
        for _ in range(n_normal):
            seq, label = self.generate_normal_sequence()
            self.sequences.append(seq)
            self.labels.append(label)
        
        # Fausses alertes
        print(f"Generation de {n_false} fausses alertes...")
        for _ in range(n_false):
            seq, label = self.generate_false_alarm()
            self.sequences.append(seq)
            self.labels.append(label)
        
        # Feux (melange de types)
        print(f"Generation de {n_fires} sequences d'incendie...")
        for _ in range(n_fires):
            fire_type = random.choice(['slow', 'fast', 'intense'])
            
            if fire_type == 'slow':
                seq, label = self.generate_slow_fire()
            elif fire_type == 'fast':
                seq, label = self.generate_fast_fire()
            else:
                seq, label = self.generate_intense_fire()
            
            self.sequences.append(seq)
            self.labels.append(label)
        
        # Convertir en arrays
        self.sequences = np.array(self.sequences, dtype=np.float32)
        self.labels = np.array(self.labels, dtype=np.float32)
        
        print(f"\nDataset genere:")
        print(f"  - Sequences: {self.sequences.shape}")
        print(f"  - Labels: {self.labels.shape}")
        print(f"  - Feux: {self.labels.sum():.0f} ({self.labels.sum()/len(self.labels)*100:.1f}%)")
        print(f"  - Normaux: {len(self.labels) - self.labels.sum():.0f}")
        
        return self.sequences, self.labels
    
    def save_dataset(self, output_dir):
        """Sauvegarder le dataset"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        np.save(output_path / 'sequences.npy', self.sequences)
        np.save(output_path / 'labels.npy', self.labels)
        
        print(f"\nDataset sauvegarde dans: {output_path}")
        print(f"  - sequences.npy: {(self.sequences.nbytes / 1024 / 1024):.2f} MB")
        print(f"  - labels.npy: {(self.labels.nbytes / 1024):.2f} KB")

if __name__ == "__main__":
    generator = DataGenerator()
    sequences, labels = generator.generate_dataset(
        n_normal=1500,
        n_false=500,
        n_fires=2000
    )
    
    # Sauvegarder
    data_dir = Path(__file__).parent.parent / 'data' / 'datasets'
    generator.save_dataset(data_dir)
    
    print("\n" + "=" * 70)
    print("GENERATION TERMINEE!")
    print("=" * 70)
