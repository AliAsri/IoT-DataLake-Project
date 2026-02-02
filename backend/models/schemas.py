"""
Pydantic schemas for IoT Data Lake
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum


class SensorType(str, Enum):
    """Types of IoT sensors"""
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    ENERGY = "energy"
    MOTION = "motion"


class StorageTier(str, Enum):
    """Storage tier levels"""
    HOT = "hot"      # Critical data - in memory
    WARM = "warm"    # Important data - SQLite
    COLD = "cold"    # Routine data - compressed files


class DataPriority(str, Enum):
    """Data priority classification"""
    CRITICAL = "critical"
    IMPORTANT = "important"
    ROUTINE = "routine"


class SensorReading(BaseModel):
    """Single sensor reading"""
    sensor_id: str = Field(..., description="Unique sensor identifier")
    sensor_type: SensorType = Field(..., description="Type of sensor")
    value: float = Field(..., description="Sensor reading value")
    unit: str = Field(..., description="Measurement unit")
    timestamp: datetime = Field(default_factory=datetime.now)
    location: Optional[str] = Field(None, description="Sensor location")
    metadata: Optional[dict] = Field(default_factory=dict)


class ClassifiedData(BaseModel):
    """Data after ML classification"""
    reading: SensorReading
    priority: DataPriority
    storage_tier: StorageTier
    confidence: float = Field(..., ge=0, le=1, description="Classification confidence")
    features: dict = Field(default_factory=dict, description="Extracted features")
    is_anomaly: bool = Field(False, description="Whether data is anomalous")


class StorageMetrics(BaseModel):
    """Storage system metrics"""
    hot_count: int = Field(0, description="Items in hot storage")
    warm_count: int = Field(0, description="Items in warm storage")
    cold_count: int = Field(0, description="Items in cold storage")
    hot_size_bytes: int = Field(0, description="Hot storage size")
    warm_size_bytes: int = Field(0, description="Warm storage size")
    cold_size_bytes: int = Field(0, description="Cold storage size")
    compression_ratio: float = Field(1.0, description="Cold storage compression ratio")
    total_processed: int = Field(0, description="Total readings processed")
    anomalies_detected: int = Field(0, description="Total anomalies detected")


class GenerateRequest(BaseModel):
    """Request to generate sensor data"""
    count: int = Field(10, ge=1, le=1000, description="Number of readings to generate")
    sensor_types: Optional[List[SensorType]] = Field(None, description="Specific sensor types")
    include_anomalies: bool = Field(True, description="Include anomalous readings")
    anomaly_rate: float = Field(0.1, ge=0, le=1, description="Rate of anomalies")


class QueryRequest(BaseModel):
    """Request to query stored data"""
    tier: Optional[StorageTier] = Field(None, description="Specific tier to query")
    sensor_type: Optional[SensorType] = Field(None, description="Filter by sensor type")
    start_time: Optional[datetime] = Field(None, description="Start of time range")
    end_time: Optional[datetime] = Field(None, description="End of time range")
    limit: int = Field(100, ge=1, le=1000, description="Maximum results")
    only_anomalies: bool = Field(False, description="Only return anomalies")


class APIResponse(BaseModel):
    """Standard API response"""
    success: bool
    message: str
    data: Optional[dict] = None
