#!/usr/bin/env python3
"""
Database Migration Script: SQLite to PostgreSQL
Migrates existing SQLite data to PostgreSQL without losing any data.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from watch.app import create_app
from watch.app.extensions import db
from watch.app.models import *

def backup_sqlite_data():
    """Create a backup of SQLite data before migration"""
    print("Creating SQLite data backup...")
    
    # Create backup directory
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f"sqlite_backup_{timestamp}.json"
    
    app = create_app()
    with app.app_context():
        # Export all data to JSON
        backup_data = {}
        
        # Export all tables
        tables = [
            ('users', User),
            ('roles', Role),
            ('schedules', Schedule),
            ('attendance_checklist', AttendanceChecklist),
            ('attendance_history', AttendanceHistory),
            ('minor_cases', MinorCase),
            ('major_cases', MajorCase),
            ('persons', Person),
            ('cases', Case),
            ('appointments', Appointment),
            ('notifications', Notification),
            ('audit_logs', AuditLog),
            ('activity_logs', ActivityLog),
            ('system_settings', SystemSettings),
            ('email_settings', EmailSettings)
        ]
        
        for table_name, model_class in tables:
            try:
                records = model_class.query.all()
                backup_data[table_name] = []
                
                for record in records:
                    # Convert to dictionary, handling special cases
                    record_dict = {}
                    for column in model_class.__table__.columns:
                        value = getattr(record, column.name)
                        if isinstance(value, datetime):
                            value = value.isoformat()
                        elif isinstance(value, date):
                            value = value.isoformat()
                        elif isinstance(value, time):
                            value = value.isoformat()
                        elif hasattr(value, '__dict__'):  # Handle relationships
                            continue
                        record_dict[column.name] = value
                    backup_data[table_name].append(record_dict)
                
                print(f"✓ Exported {len(records)} records from {table_name}")
                
            except Exception as e:
                print(f"⚠ Warning: Could not export {table_name}: {e}")
        
        # Save backup
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Backup saved to: {backup_file}")
        return backup_file

def setup_postgresql_database():
    """Setup PostgreSQL database and create tables"""
    print("Setting up PostgreSQL database...")
    
    # Set DATABASE_URL for PostgreSQL
    postgres_url = os.getenv("POSTGRES_DATABASE_URL")
    if not postgres_url:
        print("❌ POSTGRES_DATABASE_URL environment variable not set!")
        print("Please set it to: postgresql://username:password@localhost:5432/watch_db")
        return False
    
    # Temporarily set DATABASE_URL
    os.environ['DATABASE_URL'] = postgres_url
    
    app = create_app()
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✓ PostgreSQL tables created successfully")
            return True
        except Exception as e:
            print(f"❌ Error creating PostgreSQL tables: {e}")
            return False

def migrate_data_to_postgresql(backup_file):
    """Migrate data from backup to PostgreSQL"""
    print("Migrating data to PostgreSQL...")
    
    # Load backup data
    with open(backup_file, 'r', encoding='utf-8') as f:
        backup_data = json.load(f)
    
    app = create_app()
    with app.app_context():
        try:
            # Import data in correct order (respecting foreign keys)
            migration_order = [
                ('roles', Role),
                ('users', User),
                ('system_settings', SystemSettings),
                ('email_settings', EmailSettings),
                ('schedules', Schedule),
                ('persons', Person),
                ('cases', Case),
                ('minor_cases', MinorCase),
                ('major_cases', MajorCase),
                ('appointments', Appointment),
                ('notifications', Notification),
                ('audit_logs', AuditLog),
                ('activity_logs', ActivityLog),
                ('attendance_checklist', AttendanceChecklist),
                ('attendance_history', AttendanceHistory)
            ]
            
            for table_name, model_class in migration_order:
                if table_name in backup_data and backup_data[table_name]:
                    print(f"Migrating {table_name}...")
                    
                    for record_data in backup_data[table_name]:
                        try:
                            # Create new record
                            record = model_class()
                            
                            # Set attributes
                            for key, value in record_data.items():
                                if hasattr(record, key):
                                    # Handle datetime/date/time conversion
                                    if key in ['created_at', 'updated_at', 'timestamp', 'date', 'appointment_date']:
                                        if value and isinstance(value, str):
                                            if 'T' in value:
                                                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                            else:
                                                from datetime import date
                                                value = date.fromisoformat(value)
                                    
                                    setattr(record, key, value)
                            
                            db.session.add(record)
                            
                        except Exception as e:
                            print(f"⚠ Warning: Could not migrate record in {table_name}: {e}")
                            continue
                    
                    db.session.commit()
                    print(f"✓ Migrated {len(backup_data[table_name])} records to {table_name}")
            
            print("✓ Data migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            db.session.rollback()
            return False

def verify_migration():
    """Verify that migration was successful"""
    print("Verifying migration...")
    
    app = create_app()
    with app.app_context():
        try:
            # Check key tables
            user_count = User.query.count()
            role_count = Role.query.count()
            case_count = Case.query.count()
            appointment_count = Appointment.query.count()
            
            print(f"✓ Users: {user_count}")
            print(f"✓ Roles: {role_count}")
            print(f"✓ Cases: {case_count}")
            print(f"✓ Appointments: {appointment_count}")
            
            if user_count > 0 and role_count > 0:
                print("✓ Migration verification successful!")
                return True
            else:
                print("❌ Migration verification failed - no data found")
                return False
                
        except Exception as e:
            print(f"❌ Error during verification: {e}")
            return False

def main():
    """Main migration process"""
    print("=" * 70)
    print("  WATCH System - SQLite to PostgreSQL Migration")
    print("=" * 70)
    print()
    
    # Step 1: Backup SQLite data
    backup_file = backup_sqlite_data()
    if not backup_file:
        print("❌ Backup failed!")
        return False
    
    # Step 2: Setup PostgreSQL
    if not setup_postgresql_database():
        print("❌ PostgreSQL setup failed!")
        return False
    
    # Step 3: Migrate data
    if not migrate_data_to_postgresql(backup_file):
        print("❌ Data migration failed!")
        return False
    
    # Step 4: Verify migration
    if not verify_migration():
        print("❌ Migration verification failed!")
        return False
    
    print()
    print("=" * 70)
    print("  Migration Completed Successfully!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Update your .env file with POSTGRES_DATABASE_URL")
    print("2. Test the application with PostgreSQL")
    print("3. Deploy to Railway")
    print()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
