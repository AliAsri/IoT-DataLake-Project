"""
IoT Data Lake - FastAPI Backend
Main API endpoints for sensor data, classification, and storage
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime
import asyncio

from backend.models.schemas import (
    SensorReading, ClassifiedData, StorageMetrics,
    GenerateRequest, QueryRequest, APIResponse,
    SensorType, StorageTier
)
from backend.sensors.simulator import simulator
from backend.ml.classifier import classifier
from backend.storage.storage_manager import storage_manager


# Initialize FastAPI app
app = FastAPI(
    title="IoT Data Lake Intelligent",
    description="""
    ## Système de stockage intelligent pour données IoT
    
    Utilise le Machine Learning pour classifier automatiquement 
    les données et les router vers le tier de stockage approprié.
    
    ### Tiers de stockage:
    - 🔥 **Hot**: Données critiques (mémoire)
    - 🌤️ **Warm**: Données importantes (SQLite)
    - ❄️ **Cold**: Données routinières (fichiers compressés)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store for real-time streaming
recent_classifications: List[dict] = []
MAX_RECENT = 100


@app.get("/", response_model=APIResponse)
async def root():
    """API root endpoint"""
    return APIResponse(
        success=True,
        message="IoT Data Lake API v1.0.0",
        data={"endpoints": ["/docs", "/sensors/generate", "/data/store", "/metrics"]}
    )


@app.post("/sensors/generate", response_model=APIResponse)
async def generate_sensor_data(request: GenerateRequest = None):
    """
    Generate simulated IoT sensor data
    
    - **count**: Number of readings to generate (1-1000)
    - **sensor_types**: Optional list of specific sensor types
    - **include_anomalies**: Whether to include anomalous readings
    - **anomaly_rate**: Rate of anomalies (0-1)
    """
    if request is None:
        request = GenerateRequest()
    
    readings = simulator.generate_batch(
        count=request.count,
        sensor_types=request.sensor_types,
        include_anomalies=request.include_anomalies,
        anomaly_rate=request.anomaly_rate
    )
    
    return APIResponse(
        success=True,
        message=f"Generated {len(readings)} sensor readings",
        data={
            "count": len(readings),
            "readings": [r.model_dump(mode='json') for r in readings]
        }
    )


@app.post("/data/classify", response_model=APIResponse)
async def classify_data(readings: List[SensorReading]):
    """
    Classify sensor readings using ML model
    
    Returns classification with storage tier and confidence score
    """
    classified = classifier.classify_batch(readings)
    
    return APIResponse(
        success=True,
        message=f"Classified {len(classified)} readings",
        data={
            "classifications": [
                {
                    "sensor_id": c.reading.sensor_id,
                    "value": c.reading.value,
                    "priority": c.priority.value,
                    "storage_tier": c.storage_tier.value,
                    "confidence": c.confidence,
                    "is_anomaly": c.is_anomaly
                }
                for c in classified
            ]
        }
    )


@app.post("/data/store", response_model=APIResponse)
async def generate_classify_store(request: GenerateRequest = None):
    """
    Generate, classify, and store sensor data in one operation
    
    This is the main pipeline endpoint that:
    1. Generates sensor readings
    2. Classifies each reading using ML
    3. Stores in appropriate tier (Hot/Warm/Cold)
    """
    global recent_classifications
    
    if request is None:
        request = GenerateRequest()
    
    # Generate readings
    readings = simulator.generate_batch(
        count=request.count,
        sensor_types=request.sensor_types,
        include_anomalies=request.include_anomalies,
        anomaly_rate=request.anomaly_rate
    )
    
    # Classify readings
    classified = classifier.classify_batch(readings)
    
    # Store in appropriate tiers
    keys = storage_manager.store_batch(classified)
    
    # Update recent classifications for streaming
    for c in classified:
        entry = {
            "timestamp": c.reading.timestamp.isoformat(),
            "sensor_id": c.reading.sensor_id,
            "sensor_type": c.reading.sensor_type.value,
            "value": c.reading.value,
            "unit": c.reading.unit,
            "priority": c.priority.value,
            "storage_tier": c.storage_tier.value,
            "confidence": c.confidence,
            "is_anomaly": c.is_anomaly
        }
        recent_classifications.append(entry)
    
    # Keep only recent
    recent_classifications = recent_classifications[-MAX_RECENT:]
    
    # Count by tier
    tier_counts = {
        "hot": len(keys['hot']),
        "warm": len(keys['warm']),
        "cold": len(keys['cold'])
    }
    
    return APIResponse(
        success=True,
        message=f"Processed {len(classified)} readings",
        data={
            "total_processed": len(classified),
            "stored_by_tier": tier_counts,
            "anomalies_detected": sum(1 for c in classified if c.is_anomaly),
            "recent": recent_classifications[-10:]
        }
    )


@app.post("/data/query", response_model=APIResponse)
async def query_data(request: QueryRequest = None):
    """
    Query stored data with filters
    
    - **tier**: Specific storage tier to query
    - **sensor_type**: Filter by sensor type
    - **start_time/end_time**: Time range filter
    - **only_anomalies**: Return only anomalous data
    """
    if request is None:
        request = QueryRequest()
    
    results = storage_manager.query(
        tier=request.tier,
        sensor_type=request.sensor_type,
        start_time=request.start_time,
        end_time=request.end_time,
        limit=request.limit,
        only_anomalies=request.only_anomalies
    )
    
    return APIResponse(
        success=True,
        message=f"Found {len(results)} records",
        data={"results": results}
    )


@app.get("/data/recent", response_model=APIResponse)
async def get_recent_data(limit: int = 50):
    """Get most recent classified data"""
    return APIResponse(
        success=True,
        message=f"Returning {min(limit, len(recent_classifications))} recent records",
        data={"recent": recent_classifications[-limit:]}
    )


@app.get("/metrics", response_model=APIResponse)
async def get_metrics():
    """
    Get storage system metrics
    
    Returns counts and sizes for each storage tier
    """
    metrics = storage_manager.get_metrics()
    detailed = storage_manager.get_detailed_stats()
    
    return APIResponse(
        success=True,
        message="Storage metrics retrieved",
        data={
            "summary": metrics.model_dump(),
            "detailed": detailed
        }
    )


@app.get("/ml/feature-importance", response_model=APIResponse)
async def get_feature_importance():
    """Get ML model feature importance"""
    importance = classifier.get_feature_importance()
    
    return APIResponse(
        success=True,
        message="Feature importance retrieved",
        data={"importance": importance}
    )


@app.delete("/data/clear", response_model=APIResponse)
async def clear_all_data():
    """Clear all stored data (for testing)"""
    global recent_classifications
    
    storage_manager.clear_all()
    recent_classifications = []
    
    return APIResponse(
        success=True,
        message="All data cleared",
        data={}
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Flush all buffers on shutdown"""
    storage_manager.flush()


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
