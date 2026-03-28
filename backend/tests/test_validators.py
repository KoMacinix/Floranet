import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils.validators import DataValidator

class TestDataValidator:
    def setup_method(self):
        self.config = {
            'temperature_min': -40.0,
            'temperature_max': 100.0,
            'humidity_min': 0.0,
            'humidity_max': 100.0,
            'allow_missing_fields': False
        }
        self.validator = DataValidator(self.config)
    
    def test_valid_normal_data(self):
        data = {'sensor_id': 'sensor_1', 'temperature': 22.5, 'humidity': 60.0}
        assert self.validator.validate(data) == True
    
    def test_invalid_temperature_too_high(self):
        data = {'sensor_id': 'sensor_1', 'temperature': 150.0, 'humidity': 60.0}
        assert self.validator.validate(data) == False
    
    def test_invalid_temperature_too_low(self):
        data = {'sensor_id': 'sensor_1', 'temperature': -50.0, 'humidity': 60.0}
        assert self.validator.validate(data) == False
    
    def test_invalid_humidity_too_high(self):
        data = {'sensor_id': 'sensor_1', 'temperature': 25.0, 'humidity': 105.0}
        assert self.validator.validate(data) == False
    
    def test_missing_sensor_id(self):
        data = {'temperature': 25.0, 'humidity': 60.0}
        assert self.validator.validate(data) == False
    
    def test_statistics(self):
        self.validator.validate({'sensor_id': 'sensor_1', 'temperature': 25.0, 'humidity': 60.0})
        self.validator.validate({'sensor_id': 'sensor_1', 'temperature': 150.0, 'humidity': 60.0})
        stats = self.validator.get_stats()
        assert stats['total'] == 2
        assert stats['valid'] == 1
        assert stats['invalid'] == 1
