import pytest
import torch
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from models.lstm_model import LSTMModel, FireDetectionModel

class TestLSTMModel:
    def test_model_creation(self):
        model = LSTMModel(input_dim=2, hidden_dim=64, num_layers=2)
        assert model is not None
    
    def test_forward_pass(self):
        model = LSTMModel(input_dim=2, hidden_dim=64, num_layers=2)
        x = torch.randn(4, 30, 2)
        output = model(x)
        assert output.shape == (4, 1)
        assert torch.all((output >= 0) & (output <= 1))
    
    def test_prediction_range(self):
        config = {'input_dim': 2, 'hidden_dim': 64, 'num_layers': 2}
        fire_model = FireDetectionModel(config)
        fire_model.create_model()
        sequence = np.random.randn(30, 2).astype(np.float32)
        risk = fire_model.predict(sequence)
        assert 0 <= risk <= 1
