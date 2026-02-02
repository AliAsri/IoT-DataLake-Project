"""
Warm Storage - SQLite storage for important data
Fast queries with persistence
"""
import sqlite3
import json
import os
from typing import List, Optional
from datetime import datetime
from contextlib import contextmanager

from backend.models.schemas import ClassifiedData, SensorType


class WarmStorage:
    """
    SQLite-based storage for warm/important data
    
    Features:
    - Persistent storage
    - Indexed queries by sensor type, time range
    - Moderate access speed
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default path relative to project
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(base_dir, 'data', 'warm', 'iot_data.db')
        
        self.db_path = db_path
        self._ensure_directory()
        self._init_db()
    
    def _ensure_directory(self):
        """Ensure database directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    @contextmanager
    def _get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sensor_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE,
                    sensor_id TEXT,
                    sensor_type TEXT,
                    value REAL,
                    unit TEXT,
                    location TEXT,
                    timestamp DATETIME,
                    priority TEXT,
                    confidence REAL,
                    is_anomaly BOOLEAN,
                    features TEXT,
                    stored_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for common queries
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_sensor_type 
                ON sensor_data(sensor_type)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON sensor_data(timestamp)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_is_anomaly 
                ON sensor_data(is_anomaly)
            ''')
            
            conn.commit()
    
    def _generate_key(self, item: ClassifiedData) -> str:
        """Generate unique key for storage"""
        return f"{item.reading.sensor_id}_{item.reading.timestamp.timestamp()}"
    
    def store(self, item: ClassifiedData) -> str:
        """Store an item in warm storage"""
        key = self._generate_key(item)
        
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO sensor_data 
                (key, sensor_id, sensor_type, value, unit, location, 
                 timestamp, priority, confidence, is_anomaly, features)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                key,
                item.reading.sensor_id,
                item.reading.sensor_type.value,
                item.reading.value,
                item.reading.unit,
                item.reading.location,
                item.reading.timestamp.isoformat(),
                item.priority.value,
                item.confidence,
                item.is_anomaly,
                json.dumps(item.features)
            ))
            conn.commit()
        
        return key
    
    def store_batch(self, items: List[ClassifiedData]) -> List[str]:
        """Store multiple items efficiently"""
        keys = []
        
        with self._get_connection() as conn:
            for item in items:
                key = self._generate_key(item)
                conn.execute('''
                    INSERT OR REPLACE INTO sensor_data 
                    (key, sensor_id, sensor_type, value, unit, location, 
                     timestamp, priority, confidence, is_anomaly, features)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    key,
                    item.reading.sensor_id,
                    item.reading.sensor_type.value,
                    item.reading.value,
                    item.reading.unit,
                    item.reading.location,
                    item.reading.timestamp.isoformat(),
                    item.priority.value,
                    item.confidence,
                    item.is_anomaly,
                    json.dumps(item.features)
                ))
                keys.append(key)
            conn.commit()
        
        return keys
    
    def get(self, key: str) -> Optional[dict]:
        """Retrieve an item by key"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM sensor_data WHERE key = ?', (key,)
            )
            row = cursor.fetchone()
            
            if row:
                return dict(row)
        return None
    
    def query(
        self,
        sensor_type: Optional[SensorType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        only_anomalies: bool = False,
        limit: int = 100
    ) -> List[dict]:
        """Query stored data with filters"""
        
        query = 'SELECT * FROM sensor_data WHERE 1=1'
        params = []
        
        if sensor_type:
            query += ' AND sensor_type = ?'
            params.append(sensor_type.value)
        
        if start_time:
            query += ' AND timestamp >= ?'
            params.append(start_time.isoformat())
        
        if end_time:
            query += ' AND timestamp <= ?'
            params.append(end_time.isoformat())
        
        if only_anomalies:
            query += ' AND is_anomaly = 1'
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_recent(self, limit: int = 100) -> List[dict]:
        """Get most recent entries"""
        return self.query(limit=limit)
    
    def count(self) -> int:
        """Get number of stored items"""
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM sensor_data')
            return cursor.fetchone()[0]
    
    def size_bytes(self) -> int:
        """Get database file size"""
        try:
            return os.path.getsize(self.db_path)
        except:
            return 0
    
    def get_stats(self) -> dict:
        """Get storage statistics"""
        with self._get_connection() as conn:
            # Count by sensor type
            cursor = conn.execute('''
                SELECT sensor_type, COUNT(*) as count 
                FROM sensor_data GROUP BY sensor_type
            ''')
            by_type = {row['sensor_type']: row['count'] for row in cursor}
            
            # Count anomalies
            cursor = conn.execute(
                'SELECT COUNT(*) FROM sensor_data WHERE is_anomaly = 1'
            )
            anomaly_count = cursor.fetchone()[0]
        
        return {
            'count': self.count(),
            'size_bytes': self.size_bytes(),
            'by_sensor_type': by_type,
            'anomaly_count': anomaly_count
        }
    
    def clear(self):
        """Clear all data"""
        with self._get_connection() as conn:
            conn.execute('DELETE FROM sensor_data')
            conn.commit()


# Singleton instance
warm_storage = WarmStorage()
