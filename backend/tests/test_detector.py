import pytest
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils.validators import DataValidator
from core.config import Config

def test_validator_valid():
    config = {'temperature_min': -40, 'temperature_max': 100, 'humidity_min': 0, 'humidity_max': 100, 'allow_missing_fields': False}
    validator = DataValidator(config)
    data = {'sensor_id': 'sensor_1', 'temperature': 25.5, 'humidity': 60.0}
    assert validator.validate(data) == True

def test_validator_invalid():
    config = {'temperature_min': -40, 'temperature_max': 100, 'humidity_min': 0, 'humidity_max': 100, 'allow_missing_fields': False}
    validator = DataValidator(config)
    data = {'sensor_id': 'sensor_1', 'temperature': 150.0, 'humidity': 60.0}
    assert validator.validate(data) == False
