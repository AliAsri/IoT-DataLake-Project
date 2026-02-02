"""
IoT Sensor Simulator
Generates realistic sensor data with patterns and anomalies
"""
import random
import math
from datetime import datetime, timedelta
from typing import List, Optional
import uuid

from backend.models.schemas import SensorReading, SensorType


class IoTSensorSimulator:
    """Simulates various IoT sensors with realistic data patterns"""
    
    # Sensor configurations: (base_value, variance, unit, anomaly_threshold)
    SENSOR_CONFIGS = {
        SensorType.TEMPERATURE: {
            "base": 22.0,
            "variance": 5.0,
            "unit": "°C",
            "min": -10,
            "max": 50,
            "anomaly_min": -20,
            "anomaly_max": 80
        },
        SensorType.HUMIDITY: {
            "base": 50.0,
            "variance": 15.0,
            "unit": "%",
            "min": 20,
            "max": 80,
            "anomaly_min": 0,
            "anomaly_max": 100
        },
        SensorType.ENERGY: {
            "base": 150.0,
            "variance": 50.0,
            "unit": "W",
            "min": 50,
            "max": 300,
            "anomaly_min": 0,
            "anomaly_max": 1000
        },
        SensorType.MOTION: {
            "base": 0.0,
            "variance": 1.0,
            "unit": "events/min",
            "min": 0,
            "max": 10,
            "anomaly_min": 0,
            "anomaly_max": 100
        }
    }
    
    LOCATIONS = [
        "Building A - Floor 1",
        "Building A - Floor 2",
        "Building B - Floor 1",
        "Server Room",
        "Warehouse",
        "Outdoor - North",
        "Outdoor - South"
    ]
    
    def __init__(self):
        self.sensor_registry = {}
        self._time_offset = 0
    
    def _get_sensor_id(self, sensor_type: SensorType, location: str) -> str:
        """Generate or retrieve sensor ID"""
        key = f"{sensor_type.value}_{location}"
        if key not in self.sensor_registry:
            self.sensor_registry[key] = f"{sensor_type.value[:3].upper()}-{uuid.uuid4().hex[:8]}"
        return self.sensor_registry[key]
    
    def _add_time_pattern(self, base_value: float, sensor_type: SensorType) -> float:
        """Add time-based patterns to sensor values"""
        hour = datetime.now().hour
        
        if sensor_type == SensorType.TEMPERATURE:
            # Temperature varies with time of day
            daily_variation = 3 * math.sin((hour - 6) * math.pi / 12)
            return base_value + daily_variation
        
        elif sensor_type == SensorType.ENERGY:
            # Energy usage peaks during work hours
            if 9 <= hour <= 18:
                return base_value * 1.5
            elif 0 <= hour <= 6:
                return base_value * 0.3
            return base_value
        
        elif sensor_type == SensorType.MOTION:
            # Motion is higher during work hours
            if 8 <= hour <= 20:
                return base_value + 3
            return base_value
        
        return base_value
    
    def generate_reading(
        self,
        sensor_type: Optional[SensorType] = None,
        is_anomaly: bool = False,
        timestamp: Optional[datetime] = None
    ) -> SensorReading:
        """Generate a single sensor reading"""
        
        if sensor_type is None:
            sensor_type = random.choice(list(SensorType))
        
        config = self.SENSOR_CONFIGS[sensor_type]
        location = random.choice(self.LOCATIONS)
        
        if is_anomaly:
            # Generate anomalous value
            if random.random() > 0.5:
                value = random.uniform(config["anomaly_max"] * 0.8, config["anomaly_max"])
            else:
                value = random.uniform(config["anomaly_min"], config["min"] * 0.5)
        else:
            # Generate normal value with patterns
            base = self._add_time_pattern(config["base"], sensor_type)
            noise = random.gauss(0, config["variance"] * 0.2)
            value = max(config["min"], min(config["max"], base + noise))
        
        return SensorReading(
            sensor_id=self._get_sensor_id(sensor_type, location),
            sensor_type=sensor_type,
            value=round(value, 2),
            unit=config["unit"],
            timestamp=timestamp or datetime.now(),
            location=location,
            metadata={
                "is_anomaly": is_anomaly,
                "config_base": config["base"],
                "config_variance": config["variance"]
            }
        )
    
    def generate_batch(
        self,
        count: int = 10,
        sensor_types: Optional[List[SensorType]] = None,
        include_anomalies: bool = True,
        anomaly_rate: float = 0.1,
        time_spread_minutes: int = 60
    ) -> List[SensorReading]:
        """Generate a batch of sensor readings"""
        
        readings = []
        types_to_use = sensor_types or list(SensorType)
        
        for i in range(count):
            sensor_type = random.choice(types_to_use)
            is_anomaly = include_anomalies and random.random() < anomaly_rate
            
            # Spread timestamps over the time range
            time_offset = timedelta(minutes=random.uniform(0, time_spread_minutes))
            timestamp = datetime.now() - time_offset
            
            reading = self.generate_reading(
                sensor_type=sensor_type,
                is_anomaly=is_anomaly,
                timestamp=timestamp
            )
            readings.append(reading)
        
        # Sort by timestamp
        readings.sort(key=lambda x: x.timestamp)
        return readings
    
    def generate_stream(self, interval_seconds: float = 1.0):
        """Generator for continuous sensor data stream"""
        while True:
            yield self.generate_reading()


# Singleton instance
simulator = IoTSensorSimulator()
