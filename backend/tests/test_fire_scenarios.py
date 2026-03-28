import pytest
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from models.lstm_model import FireDetectionModel

class TestFireScenarios:
    def setup_method(self):
        config = {'input_dim': 2, 'hidden_dim': 128, 'num_layers': 3, 'dropout': 0.3}
        self.model = FireDetectionModel(config)
        model_path = Path(__file__).parent.parent / 'data' / 'models' / 'lstm_fire_detection.pth'
        self.model.load_model(str(model_path))
    
    def generate_normal(self):
        sequence = []
        for i in range(30):
            temp = 22 + np.random.uniform(-2, 2)
            humidity = 60 + np.random.uniform(-5, 5)
            sequence.append([temp, humidity])
        return np.array(sequence, dtype=np.float32)
    
    def generate_fire(self):
        sequence = []
        temp, humidity = 24, 55
        for i in range(30):
            if i > 15:
                temp += np.random.uniform(3, 6)
                humidity -= np.random.uniform(2, 4)
            else:
                temp += np.random.uniform(-0.5, 0.5)
                humidity += np.random.uniform(-1, 1)
            sequence.append([temp, humidity])
        return np.array(sequence, dtype=np.float32)
    
    def test_normal_no_fire(self):
        sequence = self.generate_normal()
        risk = self.model.predict(sequence)
        assert risk < 0.3, f"Fausse alerte! Risque: {risk:.2%}"
    
    def test_fire_detected(self):
        sequence = self.generate_fire()
        risk = self.model.predict(sequence)
        assert risk > 0.9, f"Feu non detecte! Risque: {risk:.2%}"
