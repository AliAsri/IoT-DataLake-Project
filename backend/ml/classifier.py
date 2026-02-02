"""
ML Classifier for IoT data storage tier classification
Uses Random Forest to classify data into Hot/Warm/Cold tiers
"""
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from typing import Tuple, List
import pickle
import os

from backend.models.schemas import (
    SensorReading, ClassifiedData, StorageTier, DataPriority
)
from backend.ml.features import feature_extractor


class DataClassifier:
    """
    ML-based classifier for IoT data storage decisions
    
    Classification Logic:
    - CRITICAL (Hot Storage): Anomalies, high importance, needs immediate access
    - IMPORTANT (Warm Storage): Recent data, moderate importance
    - ROUTINE (Cold Storage): Normal readings, can be archived
    """
    
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=50,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self._generate_training_data()
    
    def _generate_training_data(self):
        """Generate synthetic training data based on domain knowledge"""
        np.random.seed(42)
        n_samples = 1000
        
        # Features: value, sensor_type, mean, std, range, trend, 
        #           anomaly_score, importance_score, hour, is_business
        X = []
        y = []
        
        for _ in range(n_samples):
            # Generate features
            sensor_type = np.random.randint(0, 4)
            hour = np.random.randint(0, 24)
            is_business = 1 if 8 <= hour <= 18 else 0
            
            # Random base value
            value = np.random.normal(50, 20)
            mean = value + np.random.normal(0, 5)
            std = np.abs(np.random.normal(10, 5))
            value_range = std * 3
            trend = np.random.normal(0, 0.5)
            
            # Anomaly and importance scores
            anomaly_score = np.random.beta(2, 5)  # Most readings are normal
            importance_score = np.random.beta(3, 3)
            
            features = [
                value, sensor_type, mean, std, value_range, 
                trend, anomaly_score, importance_score, hour, is_business
            ]
            X.append(features)
            
            # Determine label based on rules
            if anomaly_score > 0.6 or importance_score > 0.8:
                label = 0  # CRITICAL -> Hot
            elif anomaly_score > 0.3 or importance_score > 0.5 or is_business:
                label = 1  # IMPORTANT -> Warm
            else:
                label = 2  # ROUTINE -> Cold
            
            y.append(label)
        
        # Add some pure anomaly cases
        for _ in range(100):
            features = [
                np.random.uniform(80, 150),  # High value
                np.random.randint(0, 4),
                50, 10, 30, 0.1,
                np.random.uniform(0.7, 1.0),  # High anomaly
                np.random.uniform(0.6, 1.0),  # High importance
                np.random.randint(0, 24),
                np.random.randint(0, 2)
            ]
            X.append(features)
            y.append(0)  # Always CRITICAL
        
        X = np.array(X)
        y = np.array(y)
        
        # Train the model
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        self.model.fit(X_scaled, y)
        self.is_trained = True
    
    def classify(self, reading: SensorReading) -> ClassifiedData:
        """Classify a sensor reading into storage tier"""
        
        # Extract features
        features = feature_extractor.extract_features(reading)
        feature_vector = feature_extractor.features_to_vector(features)
        
        # Scale and predict
        X = self.scaler.transform(feature_vector.reshape(1, -1))
        prediction = self.model.predict(X)[0]
        probabilities = self.model.predict_proba(X)[0]
        
        # Map prediction to tier and priority
        tier_mapping = {
            0: (StorageTier.HOT, DataPriority.CRITICAL),
            1: (StorageTier.WARM, DataPriority.IMPORTANT),
            2: (StorageTier.COLD, DataPriority.ROUTINE)
        }
        
        storage_tier, priority = tier_mapping[prediction]
        confidence = probabilities[prediction]
        
        # Check for anomaly
        is_anomaly = features['anomaly_score'] > 0.5 or features.get('is_anomaly_metadata', False)
        
        return ClassifiedData(
            reading=reading,
            priority=priority,
            storage_tier=storage_tier,
            confidence=float(confidence),
            features=features,
            is_anomaly=is_anomaly
        )
    
    def classify_batch(self, readings: List[SensorReading]) -> List[ClassifiedData]:
        """Classify multiple readings"""
        return [self.classify(reading) for reading in readings]
    
    def get_feature_importance(self) -> dict:
        """Get feature importance from the model"""
        feature_names = [
            'value', 'sensor_type', 'mean', 'std', 'range', 
            'trend', 'anomaly_score', 'importance_score', 'hour', 'is_business'
        ]
        
        importances = self.model.feature_importances_
        
        return dict(sorted(
            zip(feature_names, importances),
            key=lambda x: x[1],
            reverse=True
        ))


# Singleton instance
classifier = DataClassifier()
