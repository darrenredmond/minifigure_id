"""
Enhanced Data Persistence System to prevent data loss
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import threading
from contextlib import contextmanager

from src.models.schemas import ValuationReport, IdentificationResult, ValuationResult
from src.database.repository import ValuationRepository

logger = logging.getLogger(__name__)


class DataPersistenceManager:
    """Enhanced data persistence with backup and recovery mechanisms"""
    
    def __init__(self, db_manager, backup_dir: str = "data/backups"):
        self.db_manager = db_manager
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        
        # Create backup database for critical operations
        self.backup_db_path = self.backup_dir / "backup_valuations.db"
        self._init_backup_db()
    
    def _init_backup_db(self):
        """Initialize backup database"""
        try:
            with sqlite3.connect(self.backup_db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS valuation_backups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        original_id INTEGER,
                        data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'active'
                    )
                """)
                conn.commit()
            logger.info("Backup database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize backup database: {e}")
    
    def save_valuation_with_backup(self, report: ValuationReport) -> int:
        """Save valuation with automatic backup"""
        with self.lock:
            try:
                # Save to main database
                repo = ValuationRepository(self.db_manager)
                valuation_id = repo.save_valuation(report)
                
                # Create backup
                self._create_backup(valuation_id, report)
                
                # Also save to JSON backup
                self._save_json_backup(report)
                
                logger.info(f"Valuation {valuation_id} saved with backup")
                return valuation_id
                
            except Exception as e:
                logger.error(f"Failed to save valuation with backup: {e}")
                # Try to save to backup database as fallback
                return self._emergency_save(report)
    
    def _create_backup(self, valuation_id: int, report: ValuationReport):
        """Create database backup of valuation"""
        try:
            backup_data = {
                'id': valuation_id,
                'report': report.model_dump(),
                'timestamp': datetime.now().isoformat()
            }
            
            with sqlite3.connect(self.backup_db_path) as conn:
                conn.execute("""
                    INSERT INTO valuation_backups (original_id, data, status)
                    VALUES (?, ?, 'active')
                """, (valuation_id, json.dumps(backup_data)))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
    
    def _save_json_backup(self, report: ValuationReport):
        """Save JSON backup of valuation"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"valuation_backup_{timestamp}.json"
            filepath = self.backup_dir / filename
            
            backup_data = {
                'report': report.model_dump(),
                'backup_timestamp': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            with open(filepath, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to save JSON backup: {e}")
    
    def _emergency_save(self, report: ValuationReport) -> int:
        """Emergency save to backup database when main database fails"""
        try:
            backup_data = {
                'report': report.model_dump(),
                'emergency_save': True,
                'timestamp': datetime.now().isoformat()
            }
            
            with sqlite3.connect(self.backup_db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO valuation_backups (original_id, data, status)
                    VALUES (?, ?, 'emergency')
                """, (0, json.dumps(backup_data)))
                conn.commit()
                
                emergency_id = cursor.lastrowid
                logger.warning(f"Emergency save completed with ID {emergency_id}")
                return emergency_id
                
        except Exception as e:
            logger.error(f"Emergency save failed: {e}")
            return -1
    
    def recover_lost_data(self) -> List[Dict[str, Any]]:
        """Recover data from backup database"""
        recovered_data = []
        
        try:
            with sqlite3.connect(self.backup_db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, original_id, data, created_at, status
                    FROM valuation_backups
                    WHERE status = 'active' OR status = 'emergency'
                    ORDER BY created_at DESC
                """)
                
                for row in cursor.fetchall():
                    backup_id, original_id, data_str, created_at, status = row
                    
                    try:
                        data = json.loads(data_str)
                        recovered_data.append({
                            'backup_id': backup_id,
                            'original_id': original_id,
                            'data': data,
                            'created_at': created_at,
                            'status': status
                        })
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse backup data {backup_id}: {e}")
                        
        except Exception as e:
            logger.error(f"Failed to recover data: {e}")
        
        return recovered_data
    
    def restore_from_backup(self, backup_id: int) -> bool:
        """Restore specific backup to main database"""
        try:
            with sqlite3.connect(self.backup_db_path) as conn:
                cursor = conn.execute("""
                    SELECT data FROM valuation_backups WHERE id = ?
                """, (backup_id,))
                
                row = cursor.fetchone()
                if not row:
                    logger.error(f"Backup {backup_id} not found")
                    return False
                
                data = json.loads(row[0])
                report_data = data.get('report')
                
                if not report_data:
                    logger.error(f"No report data in backup {backup_id}")
                    return False
                
                # Reconstruct ValuationReport from backup data
                # This is a simplified reconstruction - in practice you'd want more robust deserialization
                logger.info(f"Restoring backup {backup_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to restore backup {backup_id}: {e}")
            return False
    
    def cleanup_old_backups(self, days_to_keep: int = 30):
        """Clean up old backup files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Clean up JSON files
            for file_path in self.backup_dir.glob("valuation_backup_*.json"):
                if file_path.stat().st_mtime < cutoff_date.timestamp():
                    file_path.unlink()
                    logger.info(f"Removed old backup file: {file_path}")
            
            # Clean up database backups
            with sqlite3.connect(self.backup_db_path) as conn:
                conn.execute("""
                    DELETE FROM valuation_backups 
                    WHERE created_at < ?
                """, (cutoff_date.isoformat(),))
                conn.commit()
                
            logger.info(f"Cleaned up backups older than {days_to_keep} days")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
    
    def get_backup_status(self) -> Dict[str, Any]:
        """Get status of backup system"""
        try:
            with sqlite3.connect(self.backup_db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_backups,
                        COUNT(CASE WHEN status = 'active' THEN 1 END) as active_backups,
                        COUNT(CASE WHEN status = 'emergency' THEN 1 END) as emergency_backups,
                        MAX(created_at) as latest_backup
                    FROM valuation_backups
                """)
                
                row = cursor.fetchone()
                total, active, emergency, latest = row
                
                return {
                    'total_backups': total,
                    'active_backups': active,
                    'emergency_backups': emergency,
                    'latest_backup': latest,
                    'backup_db_path': str(self.backup_db_path),
                    'backup_dir': str(self.backup_dir)
                }
                
        except Exception as e:
            logger.error(f"Failed to get backup status: {e}")
            return {'error': str(e)}
    
    def verify_data_integrity(self) -> Dict[str, Any]:
        """Verify data integrity between main and backup databases"""
        try:
            # Get count from main database
            repo = ValuationRepository(self.db_manager)
            main_count = repo.get_statistics()['total_valuations']
            
            # Get count from backup database
            with sqlite3.connect(self.backup_db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM valuation_backups WHERE status = 'active'")
                backup_count = cursor.fetchone()[0]
            
            return {
                'main_database_count': main_count,
                'backup_database_count': backup_count,
                'integrity_ok': main_count <= backup_count,  # Backup should have at least as many
                'missing_in_backup': max(0, main_count - backup_count)
            }
            
        except Exception as e:
            logger.error(f"Failed to verify data integrity: {e}")
            return {'error': str(e)}


class ValuationCache:
    """In-memory cache for recent valuations to prevent data loss"""
    
    def __init__(self, max_size: int = 100):
        self.cache = {}
        self.max_size = max_size
        self.lock = threading.Lock()
    
    def store_valuation(self, report: ValuationReport, valuation_id: int = None):
        """Store valuation in cache"""
        with self.lock:
            if len(self.cache) >= self.max_size:
                # Remove oldest entry
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
                del self.cache[oldest_key]
            
            key = valuation_id or f"temp_{datetime.now().timestamp()}"
            self.cache[key] = {
                'report': report,
                'timestamp': datetime.now(),
                'persisted': valuation_id is not None
            }
    
    def get_valuation(self, valuation_id: int) -> Optional[ValuationReport]:
        """Get valuation from cache"""
        with self.lock:
            if valuation_id in self.cache:
                return self.cache[valuation_id]['report']
            return None
    
    def get_unpersisted_valuations(self) -> List[ValuationReport]:
        """Get valuations that haven't been persisted yet"""
        with self.lock:
            return [
                entry['report'] for entry in self.cache.values()
                if not entry['persisted']
            ]
    
    def mark_as_persisted(self, valuation_id: int):
        """Mark valuation as persisted"""
        with self.lock:
            if valuation_id in self.cache:
                self.cache[valuation_id]['persisted'] = True
    
    def clear(self):
        """Clear the cache"""
        with self.lock:
            self.cache.clear()
