"""
WATCH System - BACKUP Stress Test Data Generator (LOCAL SQLITE ONLY)

⚠️  DEPRECATED: Use the web interface instead!
Go to: Settings → Test Data Generator (on Railway)

This script is kept as a BACKUP for local testing only.
For Railway deployment, use the web-based generator!

Generates FULL dataset (takes 10-30 minutes):
- 1,200 Schedules
- 6,000 Attendance records
- 60,000 Persons
- 120,000 Cases
- 500 Appointments

USAGE (LOCAL SQLite ONLY):
    python generate_stress_test_data.py

This populates your LOCAL database (watch_db.sqlite), NOT Railway!
"""

import os
import sys
import random
from datetime import datetime, timedelta, date, time
from io import BytesIO

# Add the watch directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'watch'))

from app import create_app
from app.extensions import db
from app.models import (
    Person, Case, Schedule, Room, Section,
    AttendanceChecklist, AttendanceHistory, Appointment
)

# Sample data
FIRST_NAMES = [
    'Juan', 'Maria', 'Jose', 'Ana', 'Pedro', 'Sofia', 'Miguel', 'Isabel',
    'Carlos', 'Carmen', 'Luis', 'Rosa', 'Antonio', 'Elena', 'Manuel',
    'Lucia', 'Francisco', 'Teresa', 'Rafael', 'Patricia', 'Diego', 'Cristina',
    'Fernando', 'Julia', 'Ricardo', 'Beatriz', 'Alberto', 'Dolores', 'Jorge',
    'Raquel', 'Roberto', 'Claudia', 'Enrique', 'Sandra', 'Javier', 'Monica'
]

LAST_NAMES = [
    'Dela Cruz', 'Santos', 'Reyes', 'Garcia', 'Gonzales', 'Rodriguez',
    'Fernandez', 'Lopez', 'Martinez', 'Sanchez', 'Ramirez', 'Torres',
    'Rivera', 'Flores', 'Mendoza', 'Castro', 'Ramos', 'Villanueva',
    'Aquino', 'Bautista', 'De Leon', 'Santiago', 'Mercado', 'Chavez'
]

PROGRAMS_STUDENT = ['BSIT', 'BSCS', 'BSHM', 'BSBA', 'BSED', 'BSNE', 'BSA']
DEPARTMENTS_FACULTY = ['Computer Science', 'Business Administration', 'Education', 'Engineering', 'Arts and Sciences']
POSITIONS_STAFF = ['Administrative Assistant', 'Librarian', 'IT Support', 'Security Guard', 'Janitor', 'Registrar Staff']

MINOR_OFFENSES = [
    'Late to class', 'Improper uniform', 'No ID', 'Littering',
    'Noise disturbance', 'Loitering', 'Eating in computer lab',
    'Using phone in class', 'Incomplete requirements', 'Tardiness'
]

MAJOR_OFFENSES = [
    'Fighting', 'Cheating in exam', 'Vandalism', 'Bullying',
    'Insubordination', 'Theft', 'Plagiarism', 'Unauthorized entry',
    'Harassment', 'Substance abuse'
]

ROOMS = [
    ('RM-101', 'Computer Lab A', 'Main Building', '1st Floor', 40),
    ('RM-102', 'Computer Lab B', 'Main Building', '1st Floor', 40),
    ('RM-201', 'Lecture Room 1', 'Main Building', '2nd Floor', 50),
    ('RM-202', 'Lecture Room 2', 'Main Building', '2nd Floor', 50),
    ('RM-301', 'Lecture Room 3', 'Main Building', '3rd Floor', 45),
    ('LAB-A', 'Science Lab', 'Science Building', '1st Floor', 30),
    ('LAB-B', 'Physics Lab', 'Science Building', '2nd Floor', 30),
    ('GYM-1', 'Gymnasium', 'Sports Complex', 'Ground Floor', 200)
]

SECTIONS = [
    ('BSIT-1A', 'BSIT', '1st Year', 'A'),
    ('BSIT-1B', 'BSIT', '1st Year', 'B'),
    ('BSIT-2A', 'BSIT', '2nd Year', 'A'),
    ('BSIT-2B', 'BSIT', '2nd Year', 'B'),
    ('BSIT-3A', 'BSIT', '3rd Year', 'A'),
    ('BSIT-3B', 'BSIT', '3rd Year', 'B'),
    ('BSIT-4A', 'BSIT', '4th Year', 'A'),
    ('BSCS-1A', 'BSCS', '1st Year', 'A'),
    ('BSCS-2A', 'BSCS', '2nd Year', 'A'),
    ('BSCS-3A', 'BSCS', '3rd Year', 'A'),
    ('BSHM-1A', 'BSHM', '1st Year', 'A'),
    ('BSHM-2A', 'BSHM', '2nd Year', 'A'),
    ('BSBA-1A', 'BSBA', '1st Year', 'A'),
    ('BSBA-2A', 'BSBA', '2nd Year', 'A')
]

SUBJECTS = [
    'Programming 1', 'Programming 2', 'Data Structures', 'Database Systems',
    'Web Development', 'Mobile Development', 'Network Security', 'Operating Systems',
    'Mathematics', 'Physics', 'English', 'Filipino', 'History', 'PE'
]

PROFESSORS = [
    'Prof. Juan Santos', 'Prof. Maria Garcia', 'Prof. Pedro Reyes',
    'Prof. Ana Rodriguez', 'Prof. Carlos Fernandez', 'Prof. Sofia Lopez',
    'Prof. Miguel Martinez', 'Prof. Isabel Sanchez', 'Prof. Luis Ramirez'
]

def generate_random_name():
    """Generate random Filipino name"""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return f"{first} {last}", first, last

def create_dummy_pdf():
    """Create a small dummy PDF file as bytes"""
    # Minimal PDF structure (valid but tiny)
    pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000056 00000 n
0000000115 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
197
%%EOF"""
    return pdf_content


def main():
    print("=" * 80)
    print("🚀 WATCH SYSTEM - LOCAL STRESS TEST (BACKUP METHOD)")
    print("=" * 80)
    print()
    print("⚠️  NOTICE: For Railway, use the web interface instead!")
    print("   Go to: Settings → Test Data Generator")
    print()
    print("This script generates data for LOCAL SQLite database only.")
    print()
    print("Generates:")
    print("   - 1,200 Schedules")
    print("   - 6,000 Attendance records")
    print("   - 60,000 Persons")
    print("   - 120,000 Cases")
    print("   - 500 Appointments")
    print()
    print("⏱️  Estimated time: 10-30 minutes")
    print("💾 Database file size: ~500MB-1GB")
    print()
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response != 'yes':
        print("❌ Aborted")
        return
    
    print()
    print("🔧 Initializing Flask app (LOCAL SQLite)...")
    app = create_app()
    
    with app.app_context():
        print("✅ Flask app initialized")
        print()
        
        # ================== STEP 1: CREATE ROOMS ==================
        print("📍 Step 1/7: Creating Rooms...")
        rooms_created = 0
        room_objects = []
        
        for room_code, room_name, building, floor, capacity in ROOMS:
            existing = Room.query.filter_by(room_code=room_code).first()
            if not existing:
                room = Room(
                    room_code=room_code,
                    room_name=room_name,
                    building=building,
                    floor=floor,
                    capacity=capacity,
                    is_active=True
                )
                db.session.add(room)
                room_objects.append(room)
                rooms_created += 1
            else:
                room_objects.append(existing)
        
        db.session.commit()
        print(f"✅ Created {rooms_created} rooms (Total: {len(room_objects)} rooms)")
        print()
        
        # ================== STEP 2: CREATE SECTIONS ==================
        print("📚 Step 2/7: Creating Sections...")
        sections_created = 0
        section_objects = []
        
        for section_code, program, year_level, section_name in SECTIONS:
            existing = Section.query.filter_by(section_code=section_code).first()
            if not existing:
                section = Section(
                    section_code=section_code,
                    program=program,
                    year_level=year_level,
                    section_name=section_name,
                    academic_year='2024-2025',
                    is_active=True,
                    is_graduated=False
                )
                db.session.add(section)
                section_objects.append(section)
                sections_created += 1
            else:
                section_objects.append(existing)
        
        db.session.commit()
        print(f"✅ Created {sections_created} sections (Total: {len(section_objects)} sections)")
        print()
        
        # ================== STEP 3: CREATE SCHEDULES ==================
        print("📅 Step 3/7: Creating 1,200 Schedules...")
        schedules_created = 0
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        
        # Generate schedules to reach 1,200 total
        target_schedules = 1200
        existing_schedules = Schedule.query.count()
        schedules_to_create = max(0, target_schedules - existing_schedules)
        
        batch_size = 100
        for i in range(0, schedules_to_create, batch_size):
            batch = min(batch_size, schedules_to_create - i)
            
            for j in range(batch):
                professor = random.choice(PROFESSORS)
                subject = random.choice(SUBJECTS)
                day = random.choice(days)
                room = random.choice(room_objects)
                
                # Random time slots (7 AM to 7 PM)
                start_hour = random.randint(7, 18)
                start_time = time(start_hour, random.choice([0, 30]))
                end_time = time(start_hour + random.randint(1, 2), random.choice([0, 30]))
                
                schedule = Schedule(
                    professor_name=professor,
                    subject=subject,
                    day_of_week=day,
                    start_time=start_time,
                    end_time=end_time,
                    room_id=room.id
                )
                db.session.add(schedule)
                schedules_created += 1
            
            db.session.commit()
            print(f"  📊 Progress: {i + batch}/{schedules_to_create} schedules created...")
        
        print(f"✅ Created {schedules_created} schedules (Total: {Schedule.query.count()} schedules)")
        print()
        
        # ================== STEP 4: CREATE ATTENDANCE DATA ==================
        print("✅ Step 4/7: Creating Attendance Data...")
        print("   Generating 200 attendance records × 30 days = 6,000 records")
        
        attendance_created = 0
        start_date = date.today() - timedelta(days=30)
        
        for day_offset in range(30):
            current_date = start_date + timedelta(days=day_offset)
            day_name = current_date.strftime('%A')
            
            # Skip Sundays
            if day_name == 'Sunday':
                continue
            
            # Generate 200 attendance records for this day
            professors_today = random.sample(PROFESSORS * 25, 200)  # Repeat professors
            
            for professor in professors_today:
                # Check if record already exists
                existing = AttendanceHistory.query.filter_by(
                    professor_name=professor,
                    date=current_date
                ).first()
                
                if not existing:
                    status = random.choices(
                        ['Present', 'Absent', 'Late'],
                        weights=[85, 5, 10]  # 85% present, 5% absent, 10% late
                    )[0]
                    
                    attendance = AttendanceHistory(
                        professor_name=professor,
                        status=status,
                        date=current_date
                    )
                    db.session.add(attendance)
                    attendance_created += 1
            
            if day_offset % 5 == 0:
                db.session.commit()
                print(f"  📊 Progress: Day {day_offset + 1}/30 ({attendance_created} records)...")
        
        db.session.commit()
        print(f"✅ Created {attendance_created} attendance records")
        print()
        
        # ================== STEP 5: CREATE PERSONS ==================
        print("👥 Step 5/7: Creating Persons (60,000 total)...")
        print("   - 40,000 Students")
        print("   - 10,000 Faculty")
        print("   - 10,000 Staff")
        
        persons_created = {'student': 0, 'faculty': 0, 'staff': 0}
        person_objects = {'student': [], 'faculty': [], 'staff': []}
        
        # Create Students (40,000)
        print("   🎓 Creating 40,000 students...")
        for i in range(40000):
            full_name, first_name, last_name = generate_random_name()
            full_name = f"{full_name} {i}"  # Make unique
            
            section = random.choice(section_objects)
            
            person = Person(
                full_name=full_name,
                first_name=first_name,
                last_name=last_name,
                role='student',
                program_or_dept=section.program,
                section=section.section_code,
                section_id=section.id
            )
            db.session.add(person)
            person_objects['student'].append(person)
            persons_created['student'] += 1
            
            if (i + 1) % 1000 == 0:
                db.session.commit()
                print(f"      Progress: {i + 1}/40,000 students...")
        
        db.session.commit()
        print(f"   ✅ Created {persons_created['student']} students")
        
        # Create Faculty (10,000)
        print("   👨‍🏫 Creating 10,000 faculty...")
        for i in range(10000):
            full_name, first_name, last_name = generate_random_name()
            full_name = f"Prof. {full_name} {i}"
            
            person = Person(
                full_name=full_name,
                first_name=first_name,
                last_name=last_name,
                role='faculty',
                program_or_dept=random.choice(DEPARTMENTS_FACULTY)
            )
            db.session.add(person)
            person_objects['faculty'].append(person)
            persons_created['faculty'] += 1
            
            if (i + 1) % 1000 == 0:
                db.session.commit()
                print(f"      Progress: {i + 1}/10,000 faculty...")
        
        db.session.commit()
        print(f"   ✅ Created {persons_created['faculty']} faculty")
        
        # Create Staff (10,000)
        print("   👔 Creating 10,000 staff...")
        for i in range(10000):
            full_name, first_name, last_name = generate_random_name()
            full_name = f"{full_name} Staff {i}"
            
            person = Person(
                full_name=full_name,
                first_name=first_name,
                last_name=last_name,
                role='staff',
                program_or_dept=random.choice(POSITIONS_STAFF)
            )
            db.session.add(person)
            person_objects['staff'].append(person)
            persons_created['staff'] += 1
            
            if (i + 1) % 1000 == 0:
                db.session.commit()
                print(f"      Progress: {i + 1}/10,000 staff...")
        
        db.session.commit()
        print(f"   ✅ Created {persons_created['staff']} staff")
        print(f"✅ Total persons created: {sum(persons_created.values())}")
        print()
        
        # ================== STEP 6: CREATE CASES ==================
        print("📋 Step 6/7: Creating 120,000 Cases...")
        print("   This will take a while...")
        
        cases_created = {'minor': 0, 'major': 0}
        dummy_pdf = create_dummy_pdf()
        
        for role, persons in person_objects.items():
            print(f"   📌 Creating cases for {role}...")
            
            # Create 20,000 minor cases per role
            print(f"      Creating 20,000 minor {role} cases...")
            for i in range(20000):
                person = random.choice(persons)
                
                case = Case(
                    person_id=person.id,
                    case_type='minor',
                    description=random.choice(MINOR_OFFENSES),
                    date_reported=date.today() - timedelta(days=random.randint(0, 365)),
                    status=random.choice(['open', 'resolved', 'pending']),
                    remarks=f"Minor case #{i + 1}",
                    offense_category='Minor Offense',
                    offense_type=random.choice(MINOR_OFFENSES)
                )
                db.session.add(case)
                cases_created['minor'] += 1
                
                if (i + 1) % 1000 == 0:
                    db.session.commit()
                    print(f"         Progress: {i + 1}/20,000 minor {role} cases...")
            
            db.session.commit()
            
            # Create 20,000 major cases per role (with attachments!)
            print(f"      Creating 20,000 major {role} cases (with attachments)...")
            for i in range(20000):
                person = random.choice(persons)
                
                # 80% of major cases have attachments
                has_attachment = random.random() < 0.8
                
                case = Case(
                    person_id=person.id,
                    case_type='major',
                    description=random.choice(MAJOR_OFFENSES),
                    date_reported=date.today() - timedelta(days=random.randint(0, 365)),
                    status=random.choice(['open', 'resolved', 'pending', 'under_investigation']),
                    remarks=f"Major case #{i + 1}",
                    offense_category='Major Offense',
                    offense_type=random.choice(MAJOR_OFFENSES),
                    # Add attachment (BLOB)
                    attachment_filename=f'case_evidence_{i}.pdf' if has_attachment else None,
                    attachment_data=dummy_pdf if has_attachment else None,
                    attachment_size=len(dummy_pdf) if has_attachment else None,
                    attachment_type='application/pdf' if has_attachment else None
                )
                db.session.add(case)
                cases_created['major'] += 1
                
                if (i + 1) % 1000 == 0:
                    db.session.commit()
                    print(f"         Progress: {i + 1}/20,000 major {role} cases...")
            
            db.session.commit()
            print(f"   ✅ Completed {role} cases (40,000 total)")
        
        print(f"✅ Total cases created: {sum(cases_created.values())}")
        print(f"   - Minor cases: {cases_created['minor']}")
        print(f"   - Major cases: {cases_created['major']}")
        print()
        
        # ================== STEP 7: CREATE APPOINTMENTS ==================
        print("📅 Step 7/7: Creating Sample Appointments...")
        appointments_created = 0
        
        for i in range(500):
            full_name, first, last = generate_random_name()
            
            appointment = Appointment(
                full_name=full_name,
                email=f"{first.lower()}.{last.lower()}@example.com",
                appointment_date=datetime.now() + timedelta(days=random.randint(1, 30)),
                appointment_type=random.choice(['Complaint', 'Admission', 'Meeting']),
                appointment_description=f"Appointment #{i + 1}",
                status=random.choice(['Pending', 'Scheduled', 'Cancelled'])
            )
            db.session.add(appointment)
            appointments_created += 1
        
        db.session.commit()
        print(f"✅ Created {appointments_created} appointments")
        print()
        
        # ================== SUMMARY ==================
        print("=" * 80)
        print("🎉 STRESS TEST DATA GENERATION COMPLETE!")
        print("=" * 80)
        print()
        print("📊 Database Summary:")
        print(f"   - Rooms: {Room.query.count()}")
        print(f"   - Sections: {Section.query.count()}")
        print(f"   - Schedules: {Schedule.query.count()}")
        print(f"   - Attendance History: {AttendanceHistory.query.count()}")
        print(f"   - Persons: {Person.query.count()}")
        print(f"   - Cases: {Case.query.count()}")
        print(f"   - Appointments: {Appointment.query.count()}")
        print()
        print("🧪 System is now ready for stress testing!")
        print()
        print("📝 Next Steps:")
        print("   1. Start the system: python run.py")
        print("   2. Go to Cases → Major Cases → Student")
        print("   3. Search for any name - should be fast!")
        print("   4. Check page load times")
        print("   5. Test pagination and search")
        print()
        print("⚠️  To remove test data:")
        print("   - Delete instance/watch_db.sqlite")
        print("   - Run: python init_database.py")
        print()
        print("✅ Done!")


if __name__ == '__main__':
    main()

