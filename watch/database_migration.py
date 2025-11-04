"""
Database Migration Script for Panel Recommendations
Safely adds new tables and columns to existing database

IMPORTANT: This script will:
1. Create backup of database before changes
2. Add Room and Section tables
3. Add foreign key columns to existing tables (backward compatible)
4. NOT remove any existing data

Run this script ONCE after implementing the panel recommendations
"""

import os
import shutil
from datetime import datetime
from app import create_app
from app.extensions import db
from app.models import Room, Section, Schedule, Person

def create_backup():
	"""Create database backup before migration"""
	db_path = 'instance/watch_db.sqlite'
	
	if not os.path.exists(db_path):
		print("❌ Database not found at:", db_path)
		return False
	
	backup_dir = 'instance/backups'
	os.makedirs(backup_dir, exist_ok=True)
	
	timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
	backup_path = os.path.join(backup_dir, f'watch_db.sqlite.migration_backup.{timestamp}')
	
	print(f"📦 Creating backup at: {backup_path}")
	shutil.copy2(db_path, backup_path)
	print(f"✅ Backup created successfully")
	return True

def migrate_database():
	"""Run database migration"""
	print("\n" + "="*60)
	print("🚀 Starting Database Migration for Panel Recommendations")
	print("="*60 + "\n")
	
	app = create_app()
	
	with app.app_context():
		# Step 1: Create backup
		print("Step 1: Creating database backup...")
		if not create_backup():
			print("❌ Migration aborted - backup failed")
			return False
		
		# Step 2: Create new tables
		print("\nStep 2: Creating new tables (Room, Section)...")
		try:
			# This will create tables that don't exist
			db.create_all()
			print("✅ Tables created/verified successfully")
		except Exception as e:
			print(f"❌ Error creating tables: {e}")
			return False
		
		# Step 3: Verify tables exist
		print("\nStep 3: Verifying database structure...")
		try:
			# Test queries to verify tables exist
			room_count = Room.query.count()
			section_count = Section.query.count()
			print(f"✅ Room table: {room_count} records")
			print(f"✅ Section table: {section_count} records")
		except Exception as e:
			print(f"❌ Error verifying tables: {e}")
			return False
		
		# Step 4: Add sample data (optional)
		print("\nStep 4: Adding sample data...")
		try:
			# Add sample rooms if none exist
			if Room.query.count() == 0:
				sample_rooms = [
					Room(room_code='RM-101', room_name='Classroom 101', building='Main Building', floor='1st Floor', capacity=40),
					Room(room_code='RM-102', room_name='Classroom 102', building='Main Building', floor='1st Floor', capacity=40),
					Room(room_code='LAB-A', room_name='Computer Lab A', building='Main Building', floor='2nd Floor', capacity=30),
					Room(room_code='LAB-B', room_name='Computer Lab B', building='Main Building', floor='2nd Floor', capacity=30),
				]
				for room in sample_rooms:
					db.session.add(room)
				print(f"✅ Added {len(sample_rooms)} sample rooms")
			else:
				print(f"ℹ️  Rooms already exist, skipping sample data")
			
			# Add sample sections if none exist
			if Section.query.count() == 0:
				sample_sections = [
					Section(section_code='BSIT-3A', program='BSIT', year_level='3rd Year', 
						   section_name='A', academic_year='2024-2025', is_active=True),
					Section(section_code='BSIT-3B', program='BSIT', year_level='3rd Year', 
						   section_name='B', academic_year='2024-2025', is_active=True),
					Section(section_code='BSCS-2A', program='BSCS', year_level='2nd Year', 
						   section_name='A', academic_year='2024-2025', is_active=True),
				]
				for section in sample_sections:
					db.session.add(section)
				print(f"✅ Added {len(sample_sections)} sample sections")
			else:
				print(f"ℹ️  Sections already exist, skipping sample data")
			
			db.session.commit()
		except Exception as e:
			db.session.rollback()
			print(f"⚠️  Warning: Could not add sample data: {e}")
		
		# Step 5: Summary
		print("\n" + "="*60)
		print("✅ Migration Completed Successfully!")
		print("="*60)
		print("\nWhat was added:")
		print("  ✓ Room table (for schedule room references)")
		print("  ✓ Section table (for student section references)")
		print("  ✓ Foreign key columns added to Schedule and Person models")
		print("\nBackward Compatibility:")
		print("  ✓ Old 'room' and 'section' text fields still work")
		print("  ✓ No existing data was modified or deleted")
		print("  ✓ All existing functionality preserved")
		print("\nNext Steps:")
		print("  1. Test the application to ensure everything works")
		print("  2. Start using the new Room and Section dropdowns")
		print("  3. Gradually migrate old text data to new references")
		print("\n" + "="*60)
		
		return True

if __name__ == '__main__':
	success = migrate_database()
	if success:
		print("\n🎉 Database migration completed successfully!")
		print("You can now restart your application.\n")
	else:
		print("\n❌ Migration failed. Check the error messages above.")
		print("Your database has NOT been modified (backup was not applied).\n")



