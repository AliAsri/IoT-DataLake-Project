"""
Cold Storage - Compressed file storage for routine data
Optimized for space, slower access
"""
import gzip
import json
import os
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from backend.models.schemas import ClassifiedData


class ColdStorage:
    """
    Compressed file-based storage for cold/routine data
    
    Features:
    - High compression ratio
    - Partitioned by date
    - Suitable for archival
    """
    
    COMPRESSION_LEVEL = 9
    
    def __init__(self, storage_path: str = None):
        if storage_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            storage_path = os.path.join(base_dir, 'data', 'cold')
        
        self.storage_path = storage_path
        self._ensure_directory()
        self.buffer: List[dict] = []
        self.buffer_size = 100
        self.metadata = {
            'total_stored': 0,
            'total_files': 0
        }
    
    def _ensure_directory(self):
        """Ensure storage directory exists"""
        os.makedirs(self.storage_path, exist_ok=True)
    
    def _get_partition_path(self, timestamp: datetime) -> str:
        """Get file path for a given timestamp (partitioned by hour)"""
        date_str = timestamp.strftime('%Y-%m-%d')
        hour_str = timestamp.strftime('%H')
        
        partition_dir = os.path.join(self.storage_path, date_str)
        os.makedirs(partition_dir, exist_ok=True)
        
        return os.path.join(partition_dir, f'data_{hour_str}.json.gz')
    
    def _generate_key(self, item: ClassifiedData) -> str:
        """Generate unique key for storage"""
        return f"{item.reading.sensor_id}_{item.reading.timestamp.timestamp()}"
    
    def _serialize_item(self, item: ClassifiedData) -> dict:
        """Serialize item for storage"""
        return {
            'key': self._generate_key(item),
            'reading': item.reading.model_dump(mode='json'),
            'priority': item.priority.value,
            'confidence': item.confidence,
            'is_anomaly': item.is_anomaly,
            'features': item.features,
            'stored_at': datetime.now().isoformat()
        }
    
    def _read_partition(self, path: str) -> List[dict]:
        """Read data from a partition file"""
        if not os.path.exists(path):
            return []
        
        try:
            with gzip.open(path, 'rt', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def _write_partition(self, path: str, data: List[dict]):
        """Write data to a partition file"""
        with gzip.open(path, 'wt', encoding='utf-8', 
                       compresslevel=self.COMPRESSION_LEVEL) as f:
            json.dump(data, f)
    
    def store(self, item: ClassifiedData) -> str:
        """Store an item in cold storage"""
        key = self._generate_key(item)
        serialized = self._serialize_item(item)
        
        self.buffer.append(serialized)
        self.metadata['total_stored'] += 1
        
        # Flush buffer when full
        if len(self.buffer) >= self.buffer_size:
            self.flush()
        
        return key
    
    def store_batch(self, items: List[ClassifiedData]) -> List[str]:
        """Store multiple items efficiently"""
        keys = []
        for item in items:
            keys.append(self.store(item))
        return keys
    
    def flush(self):
        """Flush buffer to disk"""
        if not self.buffer:
            return
        
        # Group by partition
        partitions = {}
        for item in self.buffer:
            timestamp = datetime.fromisoformat(item['reading']['timestamp'])
            path = self._get_partition_path(timestamp)
            
            if path not in partitions:
                partitions[path] = self._read_partition(path)
            
            partitions[path].append(item)
        
        # Write each partition
        for path, data in partitions.items():
            self._write_partition(path, data)
        
        self.metadata['total_files'] = len(list(Path(self.storage_path).rglob('*.json.gz')))
        self.buffer.clear()
    
    def query(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[dict]:
        """Query stored data with time range filter"""
        self.flush()  # Ensure buffer is written
        
        results = []
        
        # Iterate through partition files
        for partition_file in sorted(Path(self.storage_path).rglob('*.json.gz')):
            data = self._read_partition(str(partition_file))
            
            for item in data:
                timestamp = datetime.fromisoformat(item['reading']['timestamp'])
                
                if start_time and timestamp < start_time:
                    continue
                if end_time and timestamp > end_time:
                    continue
                
                results.append(item)
                
                if len(results) >= limit:
                    return results
        
        return results
    
    def get_recent(self, limit: int = 100) -> List[dict]:
        """Get most recent entries"""
        return self.query(limit=limit)
    
    def count(self) -> int:
        """Get approximate number of stored items"""
        return self.metadata['total_stored']
    
    def size_bytes(self) -> int:
        """Get total storage size (compressed)"""
        total_size = 0
        for partition_file in Path(self.storage_path).rglob('*.json.gz'):
            total_size += os.path.getsize(partition_file)
        return total_size
    
    def _estimate_uncompressed_size(self) -> int:
        """Estimate uncompressed size"""
        # Rough estimate: compressed is about 10x smaller
        return self.size_bytes() * 10
    
    def get_compression_ratio(self) -> float:
        """Calculate compression ratio"""
        compressed = self.size_bytes()
        if compressed == 0:
            return 1.0
        
        uncompressed = self._estimate_uncompressed_size()
        return uncompressed / compressed
    
    def get_stats(self) -> dict:
        """Get storage statistics"""
        self.flush()
        
        return {
            'count': self.count(),
            'size_bytes': self.size_bytes(),
            'estimated_uncompressed_bytes': self._estimate_uncompressed_size(),
            'compression_ratio': self.get_compression_ratio(),
            'total_files': len(list(Path(self.storage_path).rglob('*.json.gz')))
        }
    
    def clear(self):
        """Clear all data"""
        import shutil
        
        self.buffer.clear()
        if os.path.exists(self.storage_path):
            for item in Path(self.storage_path).iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        
        self.metadata = {'total_stored': 0, 'total_files': 0}


# Singleton instance  
cold_storage = ColdStorage()
