"""
Admin Test Data Generation Routes
Generates scaled-down test data suitable for Railway (no timeout issues!)
"""

from flask import jsonify, render_template
from ...auth_utils import login_required
from ...models import Person, Case, Schedule, Room, Section, AttendanceHistory, Appointment
from ...extensions import db
from datetime import datetime, timedelta, date, time
import random
from . import bp

# Sample data
FIRST_NAMES = [
    'Juan', 'Maria', 'Jose', 'Ana', 'Pedro', 'Sofia', 'Miguel', 'Isabel',
    'Carlos', 'Carmen', 'Luis', 'Rosa', 'Antonio', 'Elena', 'Manuel',
    'Lucia', 'Francisco', 'Teresa', 'Rafael', 'Patricia'
]

LAST_NAMES = [
    'Dela Cruz', 'Santos', 'Reyes', 'Garcia', 'Gonzales', 'Rodriguez',
    'Fernandez', 'Lopez', 'Martinez', 'Sanchez', 'Ramirez', 'Torres'
]

PROGRAMS = ['BSIT', 'BSCS', 'BSHM', 'BSBA', 'BSED']
DEPARTMENTS = ['Computer Science', 'Business Administration', 'Education', 'Engineering']
POSITIONS = ['Administrative Assistant', 'Librarian', 'IT Support', 'Security Guard']

MINOR_OFFENSES = [
    'Late to class', 'Improper uniform', 'No ID', 'Littering',
    'Noise disturbance', 'Using phone in class', 'Tardiness'
]

MAJOR_OFFENSES = [
    'Fighting', 'Cheating in exam', 'Vandalism', 'Bullying',
    'Insubordination', 'Theft', 'Plagiarism'
]

def generate_random_name():
    """Generate random Filipino name"""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return f"{first} {last}", first, last


@bp.get('/test-data-generator')
@login_required
def test_data_generator_page():
    """Test data generator page for admins"""
    # Get current counts
    stats = {
        'persons': Person.query.count(),
        'cases': Case.query.count(),
        'schedules': Schedule.query.count(),
        'attendance': AttendanceHistory.query.count(),
        'appointments': Appointment.query.count()
    }
    
    return render_template('settings/test_data_generator.html', stats=stats)


@bp.post('/generate-test-data')
@login_required
def generate_test_data():
    """
    Generate scaled-down test data for Railway (no timeout!)
    
    Generates:
    - 300 Schedules
    - 1,000 Attendance records
    - 3,000 Persons (2k students, 500 faculty, 500 staff)
    - 10,000 Cases (5k minor + 5k major, distributed across all entity types)
    - 100 Appointments
    
    This dataset is large enough to demonstrate scalability but small enough
    to generate within Railway's timeout limits (~2-3 minutes).
    """
    try:
        results = {
            'rooms': 0,
            'sections': 0,
            'schedules': 0,
            'attendance': 0,
            'persons': 0,
            'cases': 0,
            'appointments': 0
        }
        
        # Create Rooms
        rooms = [
            ('RM-101', 'Computer Lab A', 'Main Building', '1st Floor', 40),
            ('RM-102', 'Computer Lab B', 'Main Building', '1st Floor', 40),
            ('RM-201', 'Lecture Room 1', 'Main Building', '2nd Floor', 50),
            ('LAB-A', 'Science Lab', 'Science Building', '1st Floor', 30)
        ]
        
        room_objects = []
        for room_code, room_name, building, floor, capacity in rooms:
            existing = Room.query.filter_by(room_code=room_code).first()
            if not existing:
                room = Room(room_code=room_code, room_name=room_name, 
                           building=building, floor=floor, capacity=capacity, is_active=True)
                db.session.add(room)
                room_objects.append(room)
                results['rooms'] += 1
            else:
                room_objects.append(existing)
        db.session.commit()
        
        # Create Sections
        sections_data = [
            ('BSIT-3A', 'BSIT', '3rd Year', 'A'),
            ('BSIT-3B', 'BSIT', '3rd Year', 'B'),
            ('BSCS-2A', 'BSCS', '2nd Year', 'A'),
            ('BSHM-2A', 'BSHM', '2nd Year', 'A')
        ]
        
        section_objects = []
        for section_code, program, year_level, section_name in sections_data:
            existing = Section.query.filter_by(section_code=section_code).first()
            if not existing:
                section = Section(section_code=section_code, program=program,
                                year_level=year_level, section_name=section_name,
                                academic_year='2024-2025', is_active=True)
                db.session.add(section)
                section_objects.append(section)
                results['sections'] += 1
            else:
                section_objects.append(existing)
        db.session.commit()
        
        # Create 300 Schedules (to reach ~1200 total with existing)
        professors = ['Prof. Juan Santos', 'Prof. Maria Garcia', 'Prof. Pedro Reyes']
        subjects = ['Programming 1', 'Database Systems', 'Web Development', 'Mathematics']
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        
        for i in range(300):
            schedule = Schedule(
                professor_name=random.choice(professors),
                subject=random.choice(subjects),
                day_of_week=random.choice(days),
                start_time=time(random.randint(8, 16), 0),
                end_time=time(random.randint(9, 17), 0),
                room_id=random.choice(room_objects).id if room_objects else None
            )
            db.session.add(schedule)
            results['schedules'] += 1
            
            if i % 100 == 0:
                db.session.commit()
        db.session.commit()
        
        # Create 1,000 Attendance records
        for i in range(1000):
            attendance = AttendanceHistory(
                professor_name=random.choice(professors),
                status=random.choice(['Present', 'Absent', 'Late']),
                date=date.today() - timedelta(days=random.randint(0, 30))
            )
            db.session.add(attendance)
            results['attendance'] += 1
            
            if i % 200 == 0:
                db.session.commit()
        db.session.commit()
        
        # Create 3,000 Persons (2k students, 500 faculty, 500 staff)
        person_objects = {'student': [], 'faculty': [], 'staff': []}
        
        # Students (2,000)
        for i in range(2000):
            full_name, first, last = generate_random_name()
            full_name = f"{full_name} {i}"
            section = random.choice(section_objects) if section_objects else None
            
            person = Person(
                full_name=full_name, first_name=first, last_name=last,
                role='student',
                program_or_dept=section.program if section else random.choice(PROGRAMS),
                section=section.section_code if section else 'N/A',
                section_id=section.id if section else None
            )
            db.session.add(person)
            person_objects['student'].append(person)
            results['persons'] += 1
            
            if i % 500 == 0:
                db.session.commit()
        
        # Faculty (500)
        for i in range(500):
            full_name, first, last = generate_random_name()
            full_name = f"Prof. {full_name} {i}"
            
            person = Person(
                full_name=full_name, first_name=first, last_name=last,
                role='faculty',
                program_or_dept=random.choice(DEPARTMENTS)
            )
            db.session.add(person)
            person_objects['faculty'].append(person)
            results['persons'] += 1
        
        # Staff (500)
        for i in range(500):
            full_name, first, last = generate_random_name()
            full_name = f"{full_name} Staff {i}"
            
            person = Person(
                full_name=full_name, first_name=first, last_name=last,
                role='staff',
                program_or_dept=random.choice(POSITIONS)
            )
            db.session.add(person)
            person_objects['staff'].append(person)
            results['persons'] += 1
        
        db.session.commit()
        
        # Create 10,000 Cases (distributed across all entity types)
        # ~1,667 cases per entity type, mixed minor/major
        dummy_pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\nxref\n0 1\ntrailer<</Size 1/Root 1 0 R>>\nstartxref\n50\n%%EOF"
        
        for role, persons in person_objects.items():
            if not persons:
                continue
                
            # Create ~1,667 minor cases per role
            cases_per_role = 1667
            for i in range(cases_per_role):
                person = random.choice(persons)
                case = Case(
                    person_id=person.id, case_type='minor',
                    description=random.choice(MINOR_OFFENSES),
                    date_reported=date.today() - timedelta(days=random.randint(0, 365)),
                    status=random.choice(['open', 'resolved']),
                    offense_category='Minor Offense',
                    offense_type=random.choice(MINOR_OFFENSES)
                )
                db.session.add(case)
                results['cases'] += 1
                
                if i % 500 == 0:
                    db.session.commit()
            
            # Create ~1,667 major cases per role (with attachments)
            for i in range(cases_per_role):
                person = random.choice(persons)
                has_attachment = random.random() < 0.5  # 50% have attachments
                
                case = Case(
                    person_id=person.id, case_type='major',
                    description=random.choice(MAJOR_OFFENSES),
                    date_reported=date.today() - timedelta(days=random.randint(0, 365)),
                    status=random.choice(['open', 'resolved', 'under_investigation']),
                    offense_category='Major Offense',
                    offense_type=random.choice(MAJOR_OFFENSES),
                    attachment_filename=f'evidence_{i}.pdf' if has_attachment else None,
                    attachment_data=dummy_pdf if has_attachment else None,
                    attachment_size=len(dummy_pdf) if has_attachment else None,
                    attachment_type='application/pdf' if has_attachment else None
                )
                db.session.add(case)
                results['cases'] += 1
                
                if i % 500 == 0:
                    db.session.commit()
        
        db.session.commit()
        
        # Create 100 Appointments
        for i in range(100):
            full_name, first, last = generate_random_name()
            appointment = Appointment(
                full_name=full_name,
                email=f"{first.lower()}.{last.lower()}@example.com",
                appointment_date=datetime.now() + timedelta(days=random.randint(1, 30)),
                appointment_type=random.choice(['Complaint', 'Admission', 'Meeting']),
                status=random.choice(['Pending', 'Scheduled'])
            )
            db.session.add(appointment)
            results['appointments'] += 1
        
        db.session.commit()
        
        # Get final counts
        final_stats = {
            'rooms': Room.query.count(),
            'sections': Section.query.count(),
            'schedules': Schedule.query.count(),
            'attendance': AttendanceHistory.query.count(),
            'persons': Person.query.count(),
            'cases': Case.query.count(),
            'appointments': Appointment.query.count()
        }
        
        return jsonify({
            'success': True,
            'message': 'Test data generated successfully!',
            'generated': results,
            'totals': final_stats
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error generating test data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

