#!/usr/bin/env python3
"""
Database Migration Script: Add Soft Delete Columns
Run this ONCE on Railway to update the PostgreSQL schema
"""

import os
import sys

# Add watch directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'watch'))

from app import create_app
from app.extensions import db

def migrate_database():
    """Add missing columns to PostgreSQL database"""
    print("="*60)
    print("  DATABASE MIGRATION - Add Soft Delete Columns")
    print("="*60)
    
    app = create_app()
    
    with app.app_context():
        # Get database connection
        conn = db.engine.connect()
        trans = conn.begin()
        
        try:
            print("\n🔧 Adding soft delete columns to 'cases' table...")
            
            # Add columns to cases table (PostgreSQL syntax)
            migrations = [
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE NOT NULL",
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP",
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS deleted_by_id INTEGER REFERENCES users(id)",
                "CREATE INDEX IF NOT EXISTS idx_cases_is_deleted ON cases(is_deleted)",
                
                "ALTER TABLE persons ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE NOT NULL",
                "ALTER TABLE persons ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP",
                "ALTER TABLE persons ADD COLUMN IF NOT EXISTS deleted_by_id INTEGER REFERENCES users(id)",
                "CREATE INDEX IF NOT EXISTS idx_persons_is_deleted ON persons(is_deleted)",
                
                # Add missing indexes for performance
                "CREATE INDEX IF NOT EXISTS idx_cases_person_id ON cases(person_id)",
                "CREATE INDEX IF NOT EXISTS idx_cases_case_type ON cases(case_type)",
                "CREATE INDEX IF NOT EXISTS idx_cases_date_reported ON cases(date_reported)",
                "CREATE INDEX IF NOT EXISTS idx_persons_role ON persons(role)",
            ]
            
            for sql in migrations:
                try:
                    print(f"  Executing: {sql[:60]}...")
                    conn.execute(db.text(sql))
                    print(f"  ✓ Success")
                except Exception as e:
                    # If column already exists, that's OK
                    if 'already exists' in str(e) or 'duplicate' in str(e).lower():
                        print(f"  ⚠ Already exists (skipping)")
                    else:
                        print(f"  ✗ Error: {e}")
                        raise
            
            trans.commit()
            print("\n✅ Migration completed successfully!")
            print("\nNew columns added:")
            print("  - cases.is_deleted")
            print("  - cases.deleted_at")
            print("  - cases.deleted_by_id")
            print("  - persons.is_deleted")
            print("  - persons.deleted_at")
            print("  - persons.deleted_by_id")
            print("\nIndexes created for better performance")
            print("="*60)
            
            return True
            
        except Exception as e:
            trans.rollback()
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            conn.close()

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)

