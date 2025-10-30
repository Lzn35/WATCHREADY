"""
Database Utilities and Initialization
Handles database setup, WAL mode configuration, and connection management
"""

import logging
from sqlalchemy import text, event
from sqlalchemy.engine import Engine
from ..extensions import db

logger = logging.getLogger(__name__)


def init_database_settings(app):
    """
    Initialize database settings for ACID compliance.
    
    This function should be called after app and db are configured.
    It enables WAL mode for SQLite and sets up proper connection handling.
    
    Args:
        app: Flask application instance
    """
    database_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    
    # Check if using SQLite
    if 'sqlite' in database_uri.lower():
        logger.info("Configuring SQLite for ACID compliance with WAL mode")
        
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            """
            Set SQLite pragmas on each new connection.
            
            WAL (Write-Ahead Logging) mode:
            - Allows concurrent reads and writes
            - Improves performance
            - Better crash recovery
            - Required for proper ACID compliance in SQLite
            """
            cursor = dbapi_conn.cursor()
            
            # Enable WAL mode for better concurrency and ACID compliance
            cursor.execute("PRAGMA journal_mode=WAL")
            
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys=ON")
            
            # Set synchronous mode to FULL for maximum durability
            cursor.execute("PRAGMA synchronous=FULL")
            
            # Enable automatic index creation for foreign keys
            cursor.execute("PRAGMA automatic_index=ON")
            
            cursor.close()
            
            logger.debug("SQLite pragmas set: WAL mode enabled, foreign keys ON, synchronous FULL")
        
        logger.info("SQLite ACID compliance configuration complete")
    else:
        logger.info(f"Non-SQLite database detected: {database_uri.split(':')[0]}")
        logger.info("ACID compliance settings should be configured at database server level")


def verify_database_settings():
    """
    Verify that database settings are properly configured.
    
    Returns:
        Dictionary with verification results
    """
    try:
        results = {
            'success': True,
            'settings': {}
        }
        
        # Check if connection is active
        try:
            db.session.execute(text('SELECT 1'))
            results['settings']['connection'] = 'OK'
        except Exception as e:
            results['success'] = False
            results['settings']['connection'] = f'ERROR: {str(e)}'
            return results
        
        # Check database type
        database_uri = db.engine.url.drivername
        results['settings']['database_type'] = database_uri
        
        # For SQLite, check WAL mode and other pragmas
        if 'sqlite' in database_uri.lower():
            try:
                # Check journal mode
                result = db.session.execute(text('PRAGMA journal_mode')).scalar()
                results['settings']['journal_mode'] = result
                
                # Check foreign keys
                result = db.session.execute(text('PRAGMA foreign_keys')).scalar()
                results['settings']['foreign_keys'] = 'ON' if result == 1 else 'OFF'
                
                # Check synchronous mode
                result = db.session.execute(text('PRAGMA synchronous')).scalar()
                sync_modes = {0: 'OFF', 1: 'NORMAL', 2: 'FULL', 3: 'EXTRA'}
                results['settings']['synchronous'] = sync_modes.get(result, f'UNKNOWN ({result})')
                
                # Verify WAL mode is enabled
                if results['settings']['journal_mode'].upper() != 'WAL':
                    results['success'] = False
                    results['warning'] = 'WAL mode is not enabled'
                
            except Exception as e:
                results['success'] = False
                results['error'] = f'Error checking SQLite settings: {str(e)}'
        
        return results
        
    except Exception as e:
        logger.error(f"Error verifying database settings: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def execute_with_retry(operation, max_retries=3):
    """
    Execute a database operation with retry logic for handling lock timeouts.
    
    Args:
        operation: Callable that performs the database operation
        max_retries: Maximum number of retry attempts
        
    Returns:
        Result of the operation
        
    Raises:
        Exception: If all retry attempts fail
    """
    import time
    from sqlalchemy.exc import OperationalError
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            result = operation()
            db.session.commit()
            return result
            
        except OperationalError as e:
            db.session.rollback()
            last_error = e
            
            if 'locked' in str(e).lower() and attempt < max_retries - 1:
                # Database is locked, wait and retry
                wait_time = 0.1 * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Database locked, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise
                
        except Exception as e:
            db.session.rollback()
            raise
    
    # If we get here, all retries failed
    raise last_error


def backup_database(backup_path=None):
    """
    Create a backup of the SQLite database.
    
    Args:
        backup_path: Path where backup should be saved (optional)
        
    Returns:
        Dictionary with backup status and path
    """
    import shutil
    from datetime import datetime
    from pathlib import Path
    
    try:
        database_uri = db.engine.url.database
        
        if not database_uri or 'sqlite' not in db.engine.url.drivername.lower():
            return {
                'success': False,
                'error': 'Backup is only supported for SQLite databases'
            }
        
        db_path = Path(database_uri)
        
        if not db_path.exists():
            return {
                'success': False,
                'error': f'Database file not found: {db_path}'
            }
        
        # Generate backup filename if not provided
        if backup_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = db_path.parent / f"{db_path.stem}.backup.{timestamp}"
        else:
            backup_path = Path(backup_path)
        
        # Create backup directory if it doesn't exist
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Perform backup
        shutil.copy2(db_path, backup_path)
        
        logger.info(f"Database backup created: {backup_path}")
        
        return {
            'success': True,
            'backup_path': str(backup_path),
            'message': 'Database backup created successfully'
        }
        
    except Exception as e:
        logger.error(f"Error creating database backup: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def optimize_database():
    """
    Optimize the database by running VACUUM and ANALYZE.
    
    Returns:
        Dictionary with optimization results
    """
    try:
        database_uri = db.engine.url.drivername
        
        if 'sqlite' in database_uri.lower():
            # For SQLite, run VACUUM and ANALYZE
            logger.info("Optimizing SQLite database...")
            
            # VACUUM reclaims unused space
            db.session.execute(text('VACUUM'))
            
            # ANALYZE updates query optimizer statistics
            db.session.execute(text('ANALYZE'))
            
            db.session.commit()
            
            logger.info("Database optimization complete")
            
            return {
                'success': True,
                'message': 'Database optimized successfully (VACUUM and ANALYZE completed)'
            }
        else:
            return {
                'success': False,
                'error': 'Optimization is only supported for SQLite databases'
            }
            
    except Exception as e:
        logger.error(f"Error optimizing database: {str(e)}")
        db.session.rollback()
        return {
            'success': False,
            'error': str(e)
        }


def get_database_info():
    """
    Get information about the current database.
    
    Returns:
        Dictionary with database information
    """
    try:
        info = {
            'driver': db.engine.url.drivername,
            'database': db.engine.url.database,
            'host': db.engine.url.host,
            'pool_size': db.engine.pool.size() if hasattr(db.engine.pool, 'size') else 'N/A',
        }
        
        # For SQLite, add file size
        if 'sqlite' in info['driver'].lower() and info['database']:
            from pathlib import Path
            db_path = Path(info['database'])
            if db_path.exists():
                size_bytes = db_path.stat().st_size
                size_mb = size_bytes / (1024 * 1024)
                info['database_size_mb'] = round(size_mb, 2)
                info['database_size_bytes'] = size_bytes
        
        return info
        
    except Exception as e:
        logger.error(f"Error getting database info: {str(e)}")
        return {'error': str(e)}


def safe_table_backup(table_name):
    """
    Safely backup specific table with parameterized queries and validation.
    
    Args:
        table_name: Name of the table to backup
        
    Returns:
        list: Table data or raises ValueError for invalid table
    """
    # Whitelist of allowed tables for security
    allowed_tables = {
        'users', 'roles', 'persons', 'cases', 'minor_cases', 'major_cases',
        'schedules', 'attendance_checklist', 'attendance_history', 'appointments',
        'notifications', 'audit_logs', 'activity_logs', 'system_settings', 'email_settings'
    }
    
    if table_name not in allowed_tables:
        raise ValueError(f"Table '{table_name}' not allowed for backup")
    
    try:
        # Use parameterized query with table name validation
        result = db.session.execute(text(f"SELECT * FROM {table_name}"))
        return result.fetchall()
    except Exception as e:
        logger.error(f"Table backup failed for {table_name}: {str(e)}")
        raise ValueError(f"Failed to backup table {table_name}: {str(e)}")


def safe_database_query(query, params=None):
    """
    Execute a safe database query with parameter validation.
    
    Args:
        query: SQL query string
        params: Dictionary of parameters
        
    Returns:
        Result of the query execution
    """
    try:
        # Validate query for dangerous patterns
        dangerous_patterns = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
        query_upper = query.upper()
        
        for pattern in dangerous_patterns:
            if pattern in query_upper:
                raise ValueError(f"Dangerous SQL pattern '{pattern}' detected")
        
        # Execute with parameters
        if params:
            result = db.session.execute(text(query), params)
        else:
            result = db.session.execute(text(query))
        
        return result
    except Exception as e:
        logger.error(f"Safe query execution failed: {str(e)}")
        raise ValueError(f"Query execution failed: {str(e)}")

