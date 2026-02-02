"""
Feature extraction for IoT sensor data classification
"""
import numpy as np
from typing import List, Dict, Tuple
from collections import deque
from datetime import datetime, timedelta

from backend.models.schemas import SensorReading, SensorType


class FeatureExtractor:
    """Extracts features from sensor readings for ML classification"""
    
    # Store recent readings for statistical features
    WINDOW_SIZE = 100
    
    def __init__(self):
        self.reading_history: Dict[str, deque] = {}
        self.sensor_stats: Dict[str, Dict] = {}
        
        # Define normal ranges for each sensor type
        self.normal_ranges = {
            SensorType.TEMPERATURE: (-10, 45),
            SensorType.HUMIDITY: (15, 85),
            SensorType.ENERGY: (20, 400),
            SensorType.MOTION: (0, 15)
        }
        
        # Criticality weights
        self.criticality_weights = {
            SensorType.TEMPERATURE: 0.8,
            SensorType.HUMIDITY: 0.5,
            SensorType.ENERGY: 0.9,
            SensorType.MOTION: 0.6
        }
    
    def _update_history(self, reading: SensorReading):
        """Update reading history for a sensor"""
        sensor_id = reading.sensor_id
        
        if sensor_id not in self.reading_history:
            self.reading_history[sensor_id] = deque(maxlen=self.WINDOW_SIZE)
        
        self.reading_history[sensor_id].append({
            'value': reading.value,
            'timestamp': reading.timestamp
        })
    
    def _get_statistical_features(self, reading: SensorReading) -> Dict[str, float]:
        """Calculate statistical features from recent readings"""
        sensor_id = reading.sensor_id
        history = self.reading_history.get(sensor_id, [])
        
        if len(history) < 2:
            return {
                'mean': reading.value,
                'std': 0.0,
                'min': reading.value,
                'max': reading.value,
                'range': 0.0,
                'trend': 0.0
            }
        
        values = [h['value'] for h in history]
        
        return {
            'mean': np.mean(values),
            'std': np.std(values),
            'min': np.min(values),
            'max': np.max(values),
            'range': np.max(values) - np.min(values),
            'trend': (values[-1] - values[0]) / len(values) if len(values) > 1 else 0
        }
    
    def _calculate_anomaly_score(self, reading: SensorReading, stats: Dict) -> float:
        """Calculate anomaly score (0-1) based on deviation from normal"""
        normal_range = self.normal_ranges.get(reading.sensor_type, (0, 100))
        min_val, max_val = normal_range
        
        # Distance from normal range
        if reading.value < min_val:
            distance = (min_val - reading.value) / (max_val - min_val)
        elif reading.value > max_val:
            distance = (reading.value - max_val) / (max_val - min_val)
        else:
            distance = 0
        
        # Z-score based anomaly
        if stats['std'] > 0:
            z_score = abs(reading.value - stats['mean']) / stats['std']
        else:
            z_score = 0
        
        # Combine scores
        anomaly_score = min(1.0, (distance * 0.6 + z_score / 3 * 0.4))
        
        return anomaly_score
    
    def _calculate_importance_score(self, reading: SensorReading, anomaly_score: float) -> float:
        """Calculate importance score based on sensor type and anomaly"""
        base_weight = self.criticality_weights.get(reading.sensor_type, 0.5)
        
        # Higher anomaly = higher importance
        importance = base_weight * 0.3 + anomaly_score * 0.7
        
        return min(1.0, importance)
    
    def extract_features(self, reading: SensorReading) -> Dict:
        """Extract all features from a sensor reading"""
        
        # Update history
        self._update_history(reading)
        
        # Get statistical features
        stats = self._get_statistical_features(reading)
        
        # Calculate scores
        anomaly_score = self._calculate_anomaly_score(reading, stats)
        importance_score = self._calculate_importance_score(reading, anomaly_score)
        
        # Encode sensor type
        sensor_type_encoded = list(SensorType).index(reading.sensor_type)
        
        # Compile features
        features = {
            # Raw features
            'value': reading.value,
            'sensor_type_encoded': sensor_type_encoded,
            
            # Statistical features
            'mean': stats['mean'],
            'std': stats['std'],
            'value_range': stats['range'],
            'trend': stats['trend'],
            
            # Derived scores
            'anomaly_score': anomaly_score,
            'importance_score': importance_score,
            
            # Time features
            'hour': reading.timestamp.hour,
            'is_business_hours': 1 if 8 <= reading.timestamp.hour <= 18 else 0,
            
            # Metadata
            'is_anomaly_metadata': reading.metadata.get('is_anomaly', False)
        }
        
        return features
    
    def features_to_vector(self, features: Dict) -> np.ndarray:
        """Convert features dict to numpy array for ML model"""
        feature_keys = [
            'value', 'sensor_type_encoded', 'mean', 'std', 
            'value_range', 'trend', 'anomaly_score', 
            'importance_score', 'hour', 'is_business_hours'
        ]
        
        return np.array([features[k] for k in feature_keys])


# Singleton instance
feature_extractor = FeatureExtractor()
