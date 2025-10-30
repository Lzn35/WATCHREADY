"""
Database migration to add audit tables for enhanced security
"""
from sqlalchemy import text

def upgrade(connection):
    """Add audit tables"""
    
    # Enhanced audit log table
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS enhanced_audit_log (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            event_type VARCHAR(50) NOT NULL,
            action VARCHAR(100) NOT NULL,
            user_id INTEGER,
            ip_address VARCHAR(45),
            session_id VARCHAR(100),
            details JSONB,
            severity VARCHAR(20) DEFAULT 'medium',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # File encryption log table
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS file_encryption_log (
            id SERIAL PRIMARY KEY,
            case_id INTEGER,
            original_path TEXT NOT NULL,
            encrypted_filename VARCHAR(255) NOT NULL,
            sensitivity_level VARCHAR(20) NOT NULL,
            encrypted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # System maintenance log table
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS system_maintenance_log (
            id SERIAL PRIMARY KEY,
            maintenance_type VARCHAR(50) NOT NULL,
            status VARCHAR(20) NOT NULL,
            details TEXT,
            started_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create indexes for better performance
    connection.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_enhanced_audit_log_timestamp 
        ON enhanced_audit_log(timestamp)
    """))
    
    connection.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_enhanced_audit_log_user_id 
        ON enhanced_audit_log(user_id)
    """))
    
    connection.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_enhanced_audit_log_event_type 
        ON enhanced_audit_log(event_type)
    """))
    
    connection.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_file_encryption_log_case_id 
        ON file_encryption_log(case_id)
    """))
    
    connection.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_system_maintenance_log_type 
        ON system_maintenance_log(maintenance_type)
    """))

def downgrade(connection):
    """Remove audit tables"""
    connection.execute(text("DROP TABLE IF EXISTS enhanced_audit_log"))
    connection.execute(text("DROP TABLE IF EXISTS file_encryption_log"))
    connection.execute(text("DROP TABLE IF EXISTS system_maintenance_log"))
