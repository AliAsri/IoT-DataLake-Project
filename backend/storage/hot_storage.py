"""
Hot Storage - In-memory storage for critical data
Ultra-fast access, limited capacity
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import OrderedDict
import json
import sys

from backend.models.schemas import ClassifiedData


class HotStorage:
    """
    In-memory storage for critical/hot data
    
    Features:
    - O(1) access time
    - LRU eviction when capacity exceeded
    - Automatic expiration of old entries
    """
    
    MAX_ENTRIES = 1000
    DEFAULT_TTL_MINUTES = 60
    
    def __init__(self):
        self.data: OrderedDict[str, dict] = OrderedDict()
        self.metadata = {
            'total_stored': 0,
            'total_evicted': 0,
            'created_at': datetime.now().isoformat()
        }
    
    def _generate_key(self, item: ClassifiedData) -> str:
        """Generate unique key for storage"""
        return f"{item.reading.sensor_id}_{item.reading.timestamp.timestamp()}"
    
    def _evict_if_needed(self):
        """Evict oldest entries if capacity exceeded"""
        while len(self.data) >= self.MAX_ENTRIES:
            self.data.popitem(last=False)
            self.metadata['total_evicted'] += 1
    
    def _clean_expired(self):
        """Remove expired entries"""
        now = datetime.now()
        expired_keys = []
        
        for key, entry in self.data.items():
            expires_at = datetime.fromisoformat(entry['expires_at'])
            if now > expires_at:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.data[key]
            self.metadata['total_evicted'] += 1
    
    def store(self, item: ClassifiedData, ttl_minutes: Optional[int] = None) -> str:
        """Store an item in hot storage"""
        
        self._evict_if_needed()
        
        key = self._generate_key(item)
        ttl = ttl_minutes or self.DEFAULT_TTL_MINUTES
        
        entry = {
            'key': key,
            'reading': item.reading.model_dump(mode='json'),
            'priority': item.priority.value,
            'confidence': item.confidence,
            'is_anomaly': item.is_anomaly,
            'features': item.features,
            'stored_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(minutes=ttl)).isoformat()
        }
        
        self.data[key] = entry
        self.data.move_to_end(key)  # Mark as recently used
        self.metadata['total_stored'] += 1
        
        return key
    
    def get(self, key: str) -> Optional[dict]:
        """Retrieve an item by key"""
        if key in self.data:
            self.data.move_to_end(key)  # Mark as recently used
            return self.data[key]
        return None
    
    def get_recent(self, limit: int = 100) -> List[dict]:
        """Get most recent entries"""
        self._clean_expired()
        entries = list(self.data.values())
        return entries[-limit:]
    
    def get_anomalies(self) -> List[dict]:
        """Get all anomalous entries"""
        return [e for e in self.data.values() if e.get('is_anomaly', False)]
    
    def count(self) -> int:
        """Get number of stored items"""
        return len(self.data)
    
    def size_bytes(self) -> int:
        """Estimate storage size in bytes"""
        return sys.getsizeof(json.dumps({k: v for k, v in self.data.items()}))
    
    def get_stats(self) -> dict:
        """Get storage statistics"""
        self._clean_expired()
        
        return {
            'count': len(self.data),
            'size_bytes': self.size_bytes(),
            'max_entries': self.MAX_ENTRIES,
            'utilization': len(self.data) / self.MAX_ENTRIES,
            'total_stored': self.metadata['total_stored'],
            'total_evicted': self.metadata['total_evicted'],
            'anomaly_count': len(self.get_anomalies())
        }
    
    def clear(self):
        """Clear all data"""
        self.data.clear()


# Singleton instance
hot_storage = HotStorage()
