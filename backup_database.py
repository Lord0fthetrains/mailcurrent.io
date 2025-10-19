#!/usr/bin/env python3
"""
Database Backup Script for MailCurrent.io
Creates timestamped backups of the SQLite database
"""

import os
import shutil
import subprocess
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_backup():
    """Create a timestamped backup of the database"""
    
    # Get current directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'db.sqlite3')
    backup_dir = os.path.join(base_dir, 'backups')
    
    # Create backup directory if it doesn't exist
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'db_backup_{timestamp}.sqlite3'
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        # Copy database file
        shutil.copy2(db_path, backup_path)
        logger.info(f"Database backup created: {backup_path}")
        
        # Get file size
        file_size = os.path.getsize(backup_path)
        logger.info(f"Backup size: {file_size:,} bytes")
        
        # Create a compressed backup as well
        compressed_backup = f"{backup_path}.gz"
        subprocess.run(['gzip', '-c', backup_path], stdout=open(compressed_backup, 'wb'))
        compressed_size = os.path.getsize(compressed_backup)
        logger.info(f"Compressed backup created: {compressed_backup} ({compressed_size:,} bytes)")
        
        # Clean up old backups (keep last 10)
        cleanup_old_backups(backup_dir)
        
        return {
            'success': True,
            'backup_path': backup_path,
            'compressed_path': compressed_backup,
            'size': file_size,
            'compressed_size': compressed_size
        }
        
    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def cleanup_old_backups(backup_dir, keep_count=10):
    """Remove old backup files, keeping only the most recent ones"""
    
    try:
        # Get all backup files
        backup_files = []
        for filename in os.listdir(backup_dir):
            if filename.startswith('db_backup_') and filename.endswith('.sqlite3'):
                file_path = os.path.join(backup_dir, filename)
                file_time = os.path.getmtime(file_path)
                backup_files.append((file_time, file_path))
        
        # Sort by modification time (newest first)
        backup_files.sort(reverse=True)
        
        # Remove old backups
        if len(backup_files) > keep_count:
            for _, file_path in backup_files[keep_count:]:
                os.remove(file_path)
                logger.info(f"Removed old backup: {file_path}")
                
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")

def restore_backup(backup_path):
    """Restore database from backup"""
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'db.sqlite3')
    
    try:
        # Create backup of current database before restore
        current_backup = f"{db_path}.before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(db_path, current_backup)
        logger.info(f"Current database backed up to: {current_backup}")
        
        # Restore from backup
        shutil.copy2(backup_path, db_path)
        logger.info(f"Database restored from: {backup_path}")
        
        return {
            'success': True,
            'restored_from': backup_path,
            'current_backup': current_backup
        }
        
    except Exception as e:
        logger.error(f"Restore failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        if len(sys.argv) < 3:
            print("Usage: python backup_database.py restore <backup_path>")
            sys.exit(1)
        result = restore_backup(sys.argv[2])
    else:
        result = create_backup()
    
    if result['success']:
        print("✅ Backup operation completed successfully")
        if 'backup_path' in result:
            print(f"📁 Backup location: {result['backup_path']}")
            print(f"📦 Compressed: {result['compressed_path']}")
    else:
        print(f"❌ Backup operation failed: {result['error']}")
        sys.exit(1)
