"""
Storage Manager - Orchestrates data flow between storage tiers
"""
from typing import List, Optional, Dict
from datetime import datetime

from backend.models.schemas import (
    ClassifiedData, StorageTier, SensorType, StorageMetrics
)
from backend.storage.hot_storage import hot_storage
from backend.storage.warm_storage import warm_storage
from backend.storage.cold_storage import cold_storage


class StorageManager:
    """
    Manages data flow across storage tiers
    Routes classified data to appropriate tier
    """
    
    def __init__(self):
        self.hot = hot_storage
        self.warm = warm_storage
        self.cold = cold_storage
        self.total_processed = 0
        self.anomalies_detected = 0
    
    def store(self, item: ClassifiedData) -> str:
        """Store classified data in appropriate tier"""
        
        self.total_processed += 1
        
        if item.is_anomaly:
            self.anomalies_detected += 1
        
        # Route to appropriate storage based on classification
        if item.storage_tier == StorageTier.HOT:
            return self.hot.store(item)
        elif item.storage_tier == StorageTier.WARM:
            return self.warm.store(item)
        else:  # COLD
            return self.cold.store(item)
    
    def store_batch(self, items: List[ClassifiedData]) -> Dict[str, List[str]]:
        """Store multiple items, returns keys grouped by tier"""
        
        result = {
            'hot': [],
            'warm': [],
            'cold': []
        }
        
        hot_items = []
        warm_items = []
        cold_items = []
        
        for item in items:
            self.total_processed += 1
            if item.is_anomaly:
                self.anomalies_detected += 1
            
            if item.storage_tier == StorageTier.HOT:
                hot_items.append(item)
            elif item.storage_tier == StorageTier.WARM:
                warm_items.append(item)
            else:
                cold_items.append(item)
        
        # Store in batches
        for item in hot_items:
            result['hot'].append(self.hot.store(item))
        
        if warm_items:
            result['warm'] = self.warm.store_batch(warm_items)
        
        if cold_items:
            result['cold'] = self.cold.store_batch(cold_items)
        
        return result
    
    def query(
        self,
        tier: Optional[StorageTier] = None,
        sensor_type: Optional[SensorType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        only_anomalies: bool = False
    ) -> List[dict]:
        """Query data from storage tiers"""
        
        results = []
        
        if tier == StorageTier.HOT or tier is None:
            hot_data = self.hot.get_recent(limit)
            if only_anomalies:
                hot_data = [d for d in hot_data if d.get('is_anomaly')]
            results.extend(hot_data)
        
        if tier == StorageTier.WARM or tier is None:
            warm_data = self.warm.query(
                sensor_type=sensor_type,
                start_time=start_time,
                end_time=end_time,
                only_anomalies=only_anomalies,
                limit=limit
            )
            results.extend(warm_data)
        
        if tier == StorageTier.COLD or tier is None:
            cold_data = self.cold.query(
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
            if only_anomalies:
                cold_data = [d for d in cold_data if d.get('is_anomaly')]
            results.extend(cold_data)
        
        # Sort by timestamp and limit
        results.sort(
            key=lambda x: x.get('timestamp') or x.get('reading', {}).get('timestamp', ''),
            reverse=True
        )
        
        return results[:limit]
    
    def get_metrics(self) -> StorageMetrics:
        """Get overall storage metrics"""
        
        hot_stats = self.hot.get_stats()
        warm_stats = self.warm.get_stats()
        cold_stats = self.cold.get_stats()
        
        return StorageMetrics(
            hot_count=hot_stats['count'],
            warm_count=warm_stats['count'],
            cold_count=cold_stats['count'],
            hot_size_bytes=hot_stats['size_bytes'],
            warm_size_bytes=warm_stats['size_bytes'],
            cold_size_bytes=cold_stats['size_bytes'],
            compression_ratio=cold_stats.get('compression_ratio', 1.0),
            total_processed=self.total_processed,
            anomalies_detected=self.anomalies_detected
        )
    
    def get_detailed_stats(self) -> dict:
        """Get detailed statistics from all tiers"""
        return {
            'hot': self.hot.get_stats(),
            'warm': self.warm.get_stats(),
            'cold': self.cold.get_stats(),
            'total_processed': self.total_processed,
            'anomalies_detected': self.anomalies_detected,
            'anomaly_rate': self.anomalies_detected / max(1, self.total_processed)
        }
    
    def flush(self):
        """Flush all buffers to disk"""
        self.cold.flush()
    
    def clear_all(self):
        """Clear all storage (for testing)"""
        self.hot.clear()
        self.warm.clear()
        self.cold.clear()
        self.total_processed = 0
        self.anomalies_detected = 0


# Singleton instance
storage_manager = StorageManager()
