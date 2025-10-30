"""
Logging Configuration for WATCH System
Configures file and console logging for database operations and application events
"""

import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logging(app):
    """
    Setup comprehensive logging for the application.
    
    Args:
        app: Flask application instance
    """
    # Create logs directory if it doesn't exist
    log_dir = Path(app.root_path).parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # ========== Database Operations Log ==========
    db_log_file = log_dir / 'db_operations.log'
    db_handler = RotatingFileHandler(
        db_log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    db_handler.setLevel(logging.INFO)
    db_handler.setFormatter(detailed_formatter)
    
    # Add handler to specific loggers
    db_logger = logging.getLogger('app.services.stored_procedures')
    db_logger.addHandler(db_handler)
    db_logger.setLevel(logging.INFO)
    
    database_logger = logging.getLogger('app.services.database')
    database_logger.addHandler(db_handler)
    database_logger.setLevel(logging.INFO)
    
    # ========== Application Log ==========
    app_log_file = log_dir / 'application.log'
    app_handler = RotatingFileHandler(
        app_log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(detailed_formatter)
    
    # Add to root logger for all application logs
    root_logger.addHandler(app_handler)
    
    # ========== Error Log ==========
    error_log_file = log_dir / 'errors.log'
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # ========== Console Handler (for development) ==========
    if app.debug:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)
    
    # Log startup
    app.logger.info("=" * 60)
    app.logger.info(f"WATCH System started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    app.logger.info(f"Debug mode: {app.debug}")
    app.logger.info(f"Database: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')}")
    app.logger.info("=" * 60)
    
    return root_logger


def get_db_logger():
    """
    Get the database operations logger.
    
    Returns:
        Logger instance for database operations
    """
    return logging.getLogger('app.services.stored_procedures')


def get_app_logger():
    """
    Get the application logger.
    
    Returns:
        Logger instance for general application logs
    """
    return logging.getLogger('app')


def log_database_operation(operation_type, details, success=True, error=None):
    """
    Log a database operation with consistent formatting.
    
    Args:
        operation_type: Type of operation (e.g., 'INSERT', 'UPDATE', 'DELETE')
        details: Dictionary with operation details
        success: Whether the operation was successful
        error: Error message if operation failed
    """
    logger = get_db_logger()
    
    status = "SUCCESS" if success else "FAILED"
    message = f"{operation_type} - {status}"
    
    if details:
        detail_str = ", ".join([f"{k}={v}" for k, v in details.items()])
        message += f" | {detail_str}"
    
    if error:
        message += f" | Error: {error}"
    
    if success:
        logger.info(message)
    else:
        logger.error(message)


def log_transaction(transaction_type, entity, entity_id, user_id=None, details=None):
    """
    Log a transaction with structured information.
    
    Args:
        transaction_type: Type of transaction ('CREATE', 'READ', 'UPDATE', 'DELETE')
        entity: Entity type (e.g., 'User', 'Case', 'Appointment')
        entity_id: ID of the entity
        user_id: ID of user performing the action (optional)
        details: Additional details dictionary (optional)
    """
    logger = get_db_logger()
    
    message = f"TRANSACTION: {transaction_type} {entity} [ID:{entity_id}]"
    
    if user_id:
        message += f" [User:{user_id}]"
    
    if details:
        detail_str = ", ".join([f"{k}={v}" for k, v in details.items()])
        message += f" | {detail_str}"
    
    logger.info(message)

