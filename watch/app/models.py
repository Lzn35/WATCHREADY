from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db


class TimestampMixin:
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	updated_at = db.Column(
		db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
	)


class Role(db.Model):
	__tablename__ = "roles"
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64), unique=True, nullable=False)


class User(db.Model, TimestampMixin):
	__tablename__ = "users"
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(120), unique=True, nullable=False)
	password_hash = db.Column(db.String(255), nullable=False)
	role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
	role = db.relationship(Role, lazy=True)
	is_protected = db.Column(db.Boolean, default=False, nullable=False)  # Protected accounts cannot be deleted
	is_active = db.Column(db.Boolean, default=True, nullable=False)  # User account status
	
	# Profile fields
	full_name = db.Column(db.String(255), nullable=True)
	title = db.Column(db.String(100), nullable=True)
	email = db.Column(db.String(120), nullable=True)
	phone = db.Column(db.String(20), nullable=True)
	gender = db.Column(db.String(10), nullable=True)
	gmail = db.Column(db.String(120), nullable=True)
	outlook = db.Column(db.String(120), nullable=True)
	profile_picture = db.Column(db.String(255), nullable=True)  # Path to profile picture
	
	def set_password(self, password):
		"""Hash and set the user's password"""
		self.password_hash = generate_password_hash(password)
	
	def check_password(self, password):
		"""Check if the provided password matches the user's password"""
		return check_password_hash(self.password_hash, password)
	
	@staticmethod
	def authenticate(username, password):
		"""Authenticate a user with username and password"""
		user = User.query.filter_by(username=username).first()
		if user and user.check_password(password):
			return user
		return None
	
	def is_admin(self):
		"""Check if user has admin role"""
		return self.role and self.role.name.lower() == 'admin'
	
	def is_user(self):
		"""Check if user has user role"""
		return self.role and self.role.name.lower() == 'user'
	
	def can_access_admin_features(self):
		"""Check if user can access admin-only features"""
		return self.is_admin()
	
	def __repr__(self):
		return f'<User {self.username}>'


class Room(db.Model):
	"""Reference table for rooms/classrooms - Panel Recommendation"""
	__tablename__ = "rooms"
	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	room_code = db.Column(db.String(50), unique=True, nullable=False)  # e.g., "RM-101", "LAB-A"
	room_name = db.Column(db.String(100), nullable=False)  # e.g., "Computer Lab A"
	building = db.Column(db.String(100), nullable=True)  # e.g., "Main Building"
	floor = db.Column(db.String(20), nullable=True)  # e.g., "2nd Floor"
	capacity = db.Column(db.Integer, nullable=True)  # Max students
	is_active = db.Column(db.Boolean, default=True, nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	
	def __repr__(self):
		return f'<Room {self.room_code}: {self.room_name}>'
	
	@staticmethod
	def get_active_rooms():
		"""Get all active rooms for dropdown"""
		return Room.query.filter_by(is_active=True).order_by(Room.room_code).all()
	
	def get_display_name(self):
		"""Get formatted display name for room"""
		return f"{self.room_code} - {self.room_name}"


class Section(db.Model):
	"""Reference table for sections - Panel Recommendation"""
	__tablename__ = "sections"
	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	section_code = db.Column(db.String(50), unique=True, nullable=False)  # e.g., "BSIT-3A"
	program = db.Column(db.String(100), nullable=False)  # e.g., "BSIT"
	year_level = db.Column(db.String(20), nullable=False)  # e.g., "3rd Year"
	section_name = db.Column(db.String(50), nullable=False)  # e.g., "A", "B"
	academic_year = db.Column(db.String(20), nullable=False)  # e.g., "2024-2025"
	is_active = db.Column(db.Boolean, default=True, nullable=False)
	is_graduated = db.Column(db.Boolean, default=False, nullable=False)  # For purging graduated students
	graduation_date = db.Column(db.Date, nullable=True)  # Track when they graduated
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	
	def __repr__(self):
		return f'<Section {self.section_code}>'
	
	@staticmethod
	def get_active_sections():
		"""Get all active (non-graduated) sections for dropdown"""
		return Section.query.filter_by(is_active=True, is_graduated=False).order_by(Section.section_code).all()
	
	@staticmethod
	def mark_as_graduated(section_id, graduation_date=None):
		"""Mark a section as graduated for purging"""
		section = Section.query.get(section_id)
		if section:
			section.is_graduated = True
			section.graduation_date = graduation_date or date.today()
			db.session.commit()
			return True
		return False
	
	@staticmethod
	def get_graduated_sections(academic_year=None):
		"""Get graduated sections, optionally filtered by academic year"""
		query = Section.query.filter_by(is_graduated=True)
		if academic_year:
			query = query.filter_by(academic_year=academic_year)
		return query.order_by(Section.graduation_date.desc()).all()


class Schedule(db.Model):
	__tablename__ = "schedules"
	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	professor_name = db.Column(db.String(255), nullable=False)
	subject = db.Column(db.String(255), nullable=False)
	day_of_week = db.Column(db.String(20), nullable=False)  # Monday, Tuesday, etc.
	start_time = db.Column(db.Time, nullable=False)
	end_time = db.Column(db.Time, nullable=False)
	
	# Room reference (Panel Recommendation) - Foreign key to Room table
	room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)
	room_ref = db.relationship('Room', lazy=True)
	
	# Keep old room field for backward compatibility (deprecated - will be phased out)
	room = db.Column(db.String(100), nullable=True)
	
	def __repr__(self):
		return f'<Schedule {self.id}: {self.professor_name} - {self.subject} ({self.day_of_week} {self.start_time}-{self.end_time})>'
	
	def get_room_display(self):
		"""Get room display name (uses Room reference if available, falls back to text field)"""
		if self.room_ref:
			return self.room_ref.get_display_name()
		return self.room or 'TBA'
	
	@staticmethod
	def check_time_overlap(professor_name, day_of_week, start_time, end_time, exclude_id=None):
		"""Check if there's a time overlap for the same professor on the same day"""
		query = Schedule.query.filter(
			Schedule.professor_name == professor_name,
			Schedule.day_of_week == day_of_week
		)
		
		if exclude_id:
			query = query.filter(Schedule.id != exclude_id)
		
		existing_schedules = query.all()
		
		for schedule in existing_schedules:
			# Check for overlap: (start1 < end2) and (start2 < end1)
			if (start_time < schedule.end_time and schedule.start_time < end_time):
				return True, schedule
		
		return False, None
	
	@staticmethod
	def get_schedules_by_professor():
		"""Get all schedules grouped by professor name"""
		schedules = Schedule.query.order_by(Schedule.professor_name, Schedule.day_of_week, Schedule.start_time).all()
		
		professors = {}
		for schedule in schedules:
			prof_name = schedule.professor_name
			if prof_name not in professors:
				professors[prof_name] = {
					'name': prof_name,
					'subjects': set(),
					'schedules': []
				}
			
			# Add subject to set
			professors[prof_name]['subjects'].add(schedule.subject)
			
			# Add schedule details
			professors[prof_name]['schedules'].append({
				'id': schedule.id,
				'subject': schedule.subject,
				'day_of_week': schedule.day_of_week,
				'start_time': schedule.start_time.strftime('%H:%M'),
				'end_time': schedule.end_time.strftime('%H:%M'),
				'room': schedule.room or 'TBA'
			})
		
		# Convert subjects sets to lists for JSON serialization
		for prof in professors.values():
			prof['subjects'] = list(prof['subjects'])
		
		return list(professors.values())


class AuditLog(db.Model):
	__tablename__ = "audit_logs"
	id = db.Column(db.Integer, primary_key=True)
	timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	action_type = db.Column(db.String(50), nullable=False)  # Created, Updated, Deleted, Confirmed, Viewed
	description = db.Column(db.Text, nullable=False)
	user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
	ip_address = db.Column(db.String(45), nullable=True)  # Support IPv4 and IPv6
	user_agent = db.Column(db.String(255), nullable=True)
	
	# Relationship to user
	user = db.relationship(User, lazy=True)
	
	def __repr__(self):
		return f'<AuditLog {self.id}: {self.action_type} - {self.description[:50]}>'
	
	@staticmethod
	def log_activity(action_type, description, user_id=None, ip_address=None, user_agent=None):
		"""Helper method to create audit log entries"""
		log_entry = AuditLog(
			action_type=action_type,
			description=description,
			user_id=user_id,
			ip_address=ip_address,
			user_agent=user_agent
		)
		db.session.add(log_entry)
		db.session.commit()
		return log_entry
	
	@staticmethod
	def get_recent_logs(limit=5):
		"""Get the most recent audit logs (LIFO order)"""
		return AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(limit).all()


class ActivityLog(db.Model):
	__tablename__ = "activity_logs"
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
	action = db.Column(db.String(100), nullable=False)  # Login, Logout, Case Added, etc.
	description = db.Column(db.Text, nullable=False)
	timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	
	# Relationship to user
	user = db.relationship(User, lazy=True)
	
	def __repr__(self):
		return f'<ActivityLog {self.id}: {self.action} - {self.description[:50]}>'
	
	@staticmethod
	def log_activity(user_id, action, description):
		"""Helper method to create activity log entries"""
		log_entry = ActivityLog(
			user_id=user_id,
			action=action,
			description=description
		)
		db.session.add(log_entry)
		
		# Keep only the latest 10 logs per user
		user_logs = ActivityLog.query.filter_by(user_id=user_id).order_by(ActivityLog.timestamp.desc()).all()
		if len(user_logs) > 10:
			# Delete the oldest logs
			for old_log in user_logs[10:]:
				db.session.delete(old_log)
		
		db.session.commit()
		return log_entry
	
	@staticmethod
	def get_user_logs(user_id, limit=10):
		"""Get the most recent activity logs for a specific user (LIFO order)"""
		return ActivityLog.query.filter_by(user_id=user_id).order_by(ActivityLog.timestamp.desc()).limit(limit).all()


class AttendanceChecklist(db.Model):
	__tablename__ = "attendance_checklist"
	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	professor_name = db.Column(db.String(255), nullable=False)  # Store professor name directly
	status = db.Column(db.Enum('Present', 'Absent', 'Late', name='attendance_status'), nullable=False)
	date = db.Column(db.Date, nullable=False)  # Removed default to force explicit date setting
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	
	# Add unique constraint: one attendance record per professor per day
	__table_args__ = (
		db.UniqueConstraint('professor_name', 'date', name='unique_professor_date'),
	)
	
	def __repr__(self):
		return f'<AttendanceChecklist {self.id}: Professor {self.professor_name} - {self.status} on {self.date}>'
	
	@staticmethod
	def get_todays_attendance():
		"""Get all attendance records for today (Philippine timezone)"""
		# Use absolute import to avoid relative import issues
		from app.utils.timezone import get_ph_today
		try:
			today = get_ph_today()
			print(f"📅 [AttendanceChecklist] Getting today's attendance for date: {today}")
			records = AttendanceChecklist.query.filter_by(date=today).all()
			print(f"✅ [AttendanceChecklist] Found {len(records)} attendance record(s) for {today}")
			return records
		except Exception as e:
			print(f"❌ [AttendanceChecklist] Error getting today's attendance: {e}")
			import traceback
			traceback.print_exc()
			# Fallback to server date
			from datetime import date
			today = date.today()
			print(f"⚠️ [AttendanceChecklist] Using fallback date: {today}")
			return AttendanceChecklist.query.filter_by(date=today).all()
	
	@staticmethod
	def get_professor_attendance_today(professor_name):
		"""Get attendance record for a specific professor today (Philippine timezone)"""
		# Use absolute import to avoid relative import issues
		from app.utils.timezone import get_ph_today
		try:
			today = get_ph_today()
			print(f"📅 [AttendanceChecklist] Getting attendance for {professor_name} on date: {today}")
			record = AttendanceChecklist.query.filter_by(
				professor_name=professor_name, 
				date=today
			).first()
			if record:
				print(f"✅ [AttendanceChecklist] Found record: {record.status} for {professor_name} on {today}")
			else:
				print(f"⚠️ [AttendanceChecklist] No record found for {professor_name} on {today}")
			return record
		except Exception as e:
			print(f"❌ [AttendanceChecklist] Error getting professor attendance: {e}")
			import traceback
			traceback.print_exc()
			# Fallback to server date
			from datetime import date
			today = date.today()
			print(f"⚠️ [AttendanceChecklist] Using fallback date: {today}")
			return AttendanceChecklist.query.filter_by(
				professor_name=professor_name,
				date=today
			).first()


class AttendanceHistory(db.Model):
	__tablename__ = "attendance_history"
	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	professor_name = db.Column(db.String(255), nullable=False)  # Store professor name directly
	status = db.Column(db.Enum('Present', 'Absent', 'Late', name='attendance_status'), nullable=False)
	date = db.Column(db.Date, nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	
	def __repr__(self):
		return f'<AttendanceHistory {self.id}: Professor {self.professor_name} - {self.status} on {self.date}>'
	
	@staticmethod
	def get_attendance_by_date(attendance_date):
		"""Get all attendance records for a specific date"""
		return AttendanceHistory.query.filter_by(date=attendance_date).all()
	
	@staticmethod
	def get_professor_history(professor_name, limit=None):
		"""Get attendance history for a specific professor"""
		query = AttendanceHistory.query.filter_by(professor_name=professor_name).order_by(AttendanceHistory.date.desc())
		if limit:
			query = query.limit(limit)
		return query.all()
	
	@staticmethod
	def get_attendance_range(start_date, end_date):
		"""Get attendance records within a date range"""
		return AttendanceHistory.query.filter(
			AttendanceHistory.date >= start_date,
			AttendanceHistory.date <= end_date
		).order_by(AttendanceHistory.date.desc()).all()


class MinorCase(db.Model, TimestampMixin):
	"""
	⚠️ LEGACY MODEL - DEPRECATED - For backward compatibility only
	
	This model is NO LONGER USED in active application code.
	The system now uses the unified Case model with case_type='minor'.
	
	Database table 'minor_cases' exists but is NOT actively written to.
	Routes have been refactored to use the Person + Case tables instead.
	
	This model is kept ONLY for:
	- Database backward compatibility
	- Historical data access (if any legacy data exists)
	- Preventing import errors in old code
	
	Future: Table can be dropped in a future database migration after confirming no legacy data exists.
	"""
	__tablename__ = "minor_cases"
	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	entity_type = db.Column(db.Enum('student', 'faculty', 'staff', name='entity_type'), nullable=False)
	last_name = db.Column(db.String(100), nullable=False)
	first_name = db.Column(db.String(100), nullable=False)
	program_or_dept = db.Column(db.String(100), nullable=False)  # Program for students, Department for faculty/staff
	section = db.Column(db.String(50), nullable=True)  # Only required for students
	date = db.Column(db.Date, nullable=False, default=date.today)
	remarks = db.Column(db.Text, nullable=True)
	
	def __repr__(self):
		return f'<MinorCase {self.id}: {self.first_name} {self.last_name} - {self.entity_type} - {self.program_or_dept}>'
	
	@staticmethod
	def get_recent_cases(entity_type=None, limit=None):
		"""Get recent minor cases ordered by created_at DESC (LIFO)"""
		query = MinorCase.query
		if entity_type:
			query = query.filter(MinorCase.entity_type == entity_type)
		query = query.order_by(MinorCase.created_at.desc())
		if limit:
			query = query.limit(limit)
		return query.all()
	
	@staticmethod
	def search_cases(search_term, entity_type=None):
		"""Search minor cases by name, program/dept, or section"""
		query = MinorCase.query.filter(
			db.or_(
				MinorCase.first_name.ilike(f'%{search_term}%'),
				MinorCase.last_name.ilike(f'%{search_term}%'),
				MinorCase.program_or_dept.ilike(f'%{search_term}%'),
				MinorCase.section.ilike(f'%{search_term}%')
			)
		)
		if entity_type:
			query = query.filter(MinorCase.entity_type == entity_type)
		return query.order_by(MinorCase.created_at.desc()).all()


class MajorCase(db.Model, TimestampMixin):
	"""
	⚠️ LEGACY MODEL - DEPRECATED - For backward compatibility only
	
	This model is NO LONGER USED in active application code.
	The system now uses the unified Case model with case_type='major'.
	
	Database table 'major_cases' exists but is NOT actively written to.
	Routes have been refactored to use the Person + Case tables instead.
	
	This model is kept ONLY for:
	- Database backward compatibility
	- Historical data access (if any legacy data exists)
	- Preventing import errors in old code
	
	Future: Table can be dropped in a future database migration after confirming no legacy data exists.
	"""
	__tablename__ = "major_cases"
	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	entity_type = db.Column(db.Enum('student', 'faculty', 'staff', name='entity_type'), nullable=False)
	last_name = db.Column(db.String(100), nullable=False)
	first_name = db.Column(db.String(100), nullable=False)
	program_or_dept = db.Column(db.String(100), nullable=False)  # Program for students, Department for faculty/staff
	section = db.Column(db.String(50), nullable=True)  # Only required for students
	date = db.Column(db.Date, nullable=False, default=date.today)
	remarks = db.Column(db.Text, nullable=True)
	# Attachment fields for major cases only - Database BLOB storage
	attachment_filename = db.Column(db.String(255), nullable=True)  # Original filename
	attachment_data = db.Column(db.LargeBinary, nullable=True)  # File content as BLOB
	attachment_size = db.Column(db.Integer, nullable=True)  # File size in bytes
	attachment_type = db.Column(db.String(100), nullable=True)  # MIME type
	attachment_hash = db.Column(db.String(64), nullable=True)  # File hash for integrity
	
	def __repr__(self):
		return f'<MajorCase {self.id}: {self.first_name} {self.last_name} - {self.entity_type} - {self.program_or_dept}>'
	
	@staticmethod
	def get_recent_cases(entity_type=None, limit=None):
		"""Get recent major cases ordered by created_at DESC (LIFO)"""
		query = MajorCase.query
		if entity_type:
			query = query.filter(MajorCase.entity_type == entity_type)
		query = query.order_by(MajorCase.created_at.desc())
		if limit:
			query = query.limit(limit)
		return query.all()
	
	@staticmethod
	def search_cases(search_term, entity_type=None):
		"""Search major cases by name, program/dept, or section"""
		query = MajorCase.query.filter(
			db.or_(
				MajorCase.first_name.ilike(f'%{search_term}%'),
				MajorCase.last_name.ilike(f'%{search_term}%'),
				MajorCase.program_or_dept.ilike(f'%{search_term}%'),
				MajorCase.section.ilike(f'%{search_term}%')
			)
		)
		if entity_type:
			query = query.filter(MajorCase.entity_type == entity_type)
		return query.order_by(MajorCase.created_at.desc()).all()


# New refactored models for person-centric case management
class Person(db.Model, TimestampMixin):
	__tablename__ = "persons"
	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	full_name = db.Column(db.String(255), nullable=False)
	first_name = db.Column(db.String(100), nullable=True)  # Added for editing
	last_name = db.Column(db.String(100), nullable=True)   # Added for editing
	role = db.Column(db.Enum('student', 'faculty', 'staff', name='person_role'), nullable=False, index=True)
	program_or_dept = db.Column(db.String(100), nullable=True)  # Program for students, Department for faculty/staff
	
	# Section reference (Panel Recommendation) - Foreign key to Section table (for students)
	section_id = db.Column(db.Integer, db.ForeignKey('sections.id'), nullable=True)
	section_ref = db.relationship('Section', lazy=True)
	
	# Keep old section field for backward compatibility (deprecated - will be phased out)
	section = db.Column(db.String(50), nullable=True)
	
	# Soft delete fields - For data recovery and audit
	is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
	deleted_at = db.Column(db.DateTime, nullable=True)
	deleted_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
	
	def __repr__(self):
		return f'<Person {self.id}: {self.full_name} - {self.role}>'
	
	def get_first_name(self):
		"""Get first name from first_name field or split from full_name"""
		if self.first_name:
			return self.first_name
		# Split full_name if first_name is not set
		if self.full_name:
			parts = self.full_name.split(' ', 1)
			return parts[0] if parts else ''
		return ''
	
	def get_last_name(self):
		"""Get last name from last_name field or split from full_name"""
		if self.last_name:
			return self.last_name
		# Split full_name if last_name is not set
		if self.full_name:
			parts = self.full_name.split(' ', 1)
			return parts[1] if len(parts) > 1 else ''
		return ''
	
	def set_names(self, first_name, last_name):
		"""Set first and last names and update full_name"""
		self.first_name = first_name
		self.last_name = last_name
		if first_name and last_name:
			self.full_name = f"{first_name} {last_name}"
		elif first_name:
			self.full_name = first_name
		elif last_name:
			self.full_name = last_name
	
	def get_section_display(self):
		"""Get section display (uses Section reference if available, falls back to text field)"""
		if self.section_ref:
			return self.section_ref.section_code
		return self.section or 'N/A'
	
	def is_graduated(self):
		"""Check if student's section has graduated (for purging)"""
		if self.role == 'student' and self.section_ref:
			return self.section_ref.is_graduated
		return False
	
	def soft_delete(self, deleted_by_user_id=None):
		"""Soft delete this person and all their cases"""
		self.is_deleted = True
		self.deleted_at = datetime.utcnow()
		self.deleted_by_id = deleted_by_user_id
		# Also soft delete all their cases
		for case in Case.query.filter_by(person_id=self.id, is_deleted=False).all():
			case.soft_delete(deleted_by_user_id)
		db.session.commit()
	
	def restore(self):
		"""Restore a soft-deleted person and optionally their cases"""
		self.is_deleted = False
		self.deleted_at = None
		self.deleted_by_id = None
		db.session.commit()
	
	@staticmethod
	def get_persons_with_case_counts(role_filter=None, include_deleted=False):
		"""Get all persons with their minor and major case counts, optionally filtered by role - excludes deleted by default"""
		from sqlalchemy import func
		
		# Get persons with minor case counts (exclude deleted cases)
		minor_counts = db.session.query(
			Case.person_id,
			func.count(Case.id).label('minor_count')
		).filter(
			Case.case_type == 'minor',
			Case.is_deleted == False
		).group_by(Case.person_id).subquery()
		
		# Get persons with major case counts (exclude deleted cases)
		major_counts = db.session.query(
			Case.person_id,
			func.count(Case.id).label('major_count')
		).filter(
			Case.case_type == 'major',
			Case.is_deleted == False
		).group_by(Case.person_id).subquery()
		
		# Join persons with case counts
		query = db.session.query(
			Person,
			func.coalesce(minor_counts.c.minor_count, 0).label('minor_count'),
			func.coalesce(major_counts.c.major_count, 0).label('major_count')
		).outerjoin(minor_counts, Person.id == minor_counts.c.person_id)\
		 .outerjoin(major_counts, Person.id == major_counts.c.person_id)
		
		# Filter out deleted persons by default
		if not include_deleted:
			query = query.filter(Person.is_deleted == False)
		
		# Apply role filter if provided
		if role_filter:
			query = query.filter(Person.role == role_filter)
		
		persons = query.order_by(Person.full_name).all()
		
		return persons
	
	@staticmethod
	def search_persons(search_term, role=None, include_deleted=False):
		"""Search persons by name, program/dept, or section - excludes deleted by default"""
		query = Person.query.filter(
			db.or_(
				Person.full_name.ilike(f'%{search_term}%'),
				Person.program_or_dept.ilike(f'%{search_term}%'),
				Person.section.ilike(f'%{search_term}%')
			)
		)
		if not include_deleted:
			query = query.filter(Person.is_deleted == False)
		if role:
			query = query.filter(Person.role == role)
		return query.order_by(Person.full_name).all()
	
	@staticmethod
	def get_deleted_persons(days_ago=60):
		"""Get soft-deleted persons for archive view"""
		return Person.query.filter(
			Person.is_deleted == True,
			Person.deleted_at.isnot(None)
		).order_by(Person.deleted_at.desc()).all()


class Case(db.Model, TimestampMixin):
	__tablename__ = "cases"
	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	person_id = db.Column(db.Integer, db.ForeignKey('persons.id', ondelete='CASCADE'), nullable=False, index=True)
	case_type = db.Column(db.Enum('minor', 'major', name='case_type'), nullable=False, index=True)
	offense_category = db.Column(db.String(100), nullable=True)  # Category of offense (for major cases)
	offense_type = db.Column(db.String(100), nullable=True)  # Type of offense (for minor/major cases)
	description = db.Column(db.Text, nullable=True)
	date_reported = db.Column(db.Date, nullable=False, default=date.today, index=True)
	status = db.Column(db.String(50), nullable=False, default='open')  # open, closed, resolved, etc.
	remarks = db.Column(db.Text, nullable=True)
	# Attachment fields for major cases only - Database BLOB storage
	attachment_filename = db.Column(db.String(255), nullable=True)  # Original filename
	attachment_data = db.Column(db.LargeBinary, nullable=True)  # File content as BLOB
	attachment_size = db.Column(db.Integer, nullable=True)  # File size in bytes
	attachment_type = db.Column(db.String(100), nullable=True)  # MIME type
	attachment_hash = db.Column(db.String(64), nullable=True)  # File hash for integrity
	
	# Soft delete fields - Panel recommendation for data recovery
	is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
	deleted_at = db.Column(db.DateTime, nullable=True)
	deleted_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
	
	# Relationships
	person = db.relationship('Person', lazy=True)
	deleted_by = db.relationship('User', foreign_keys=[deleted_by_id], lazy=True)
	
	def __repr__(self):
		return f'<Case {self.id}: {self.person.full_name if self.person else "Unknown"} - {self.case_type}>'
	
	def soft_delete(self, deleted_by_user_id=None):
		"""Soft delete this case - can be restored within 60 days"""
		self.is_deleted = True
		self.deleted_at = datetime.utcnow()
		self.deleted_by_id = deleted_by_user_id
		db.session.commit()
	
	def restore(self):
		"""Restore a soft-deleted case"""
		self.is_deleted = False
		self.deleted_at = None
		self.deleted_by_id = None
		db.session.commit()
	
	@staticmethod
	def get_cases_by_person(person_id, include_deleted=False):
		"""Get all cases for a specific person (excludes deleted by default)"""
		query = Case.query.filter_by(person_id=person_id)
		if not include_deleted:
			query = query.filter_by(is_deleted=False)
		return query.order_by(Case.date_reported.desc()).all()
	
	@staticmethod
	def get_recent_cases(case_type=None, limit=None, include_deleted=False):
		"""Get recent cases ordered by created_at DESC (LIFO) - excludes deleted by default"""
		query = Case.query
		if not include_deleted:
			query = query.filter(Case.is_deleted == False)
		if case_type:
			query = query.filter(Case.case_type == case_type)
		query = query.order_by(Case.created_at.desc())
		if limit:
			query = query.limit(limit)
		return query.all()
	
	@staticmethod
	def search_cases(search_term, case_type=None, include_deleted=False):
		"""Search cases by person name, description, or remarks - excludes deleted by default"""
		query = Case.query.join(Person).filter(
			db.or_(
				Person.full_name.ilike(f'%{search_term}%'),
				Case.description.ilike(f'%{search_term}%'),
				Case.remarks.ilike(f'%{search_term}%')
			)
		)
		if not include_deleted:
			query = query.filter(Case.is_deleted == False)
		if case_type:
			query = query.filter(Case.case_type == case_type)
		return query.order_by(Case.created_at.desc()).all()
	
	@staticmethod
	def get_deleted_cases(days_ago=60):
		"""Get soft-deleted cases for archive view"""
		return Case.query.filter(
			Case.is_deleted == True,
			Case.deleted_at.isnot(None)
		).order_by(Case.deleted_at.desc()).all()
	
	@staticmethod
	def get_cases_for_purge(days_old=60):
		"""Get cases deleted more than X days ago for permanent deletion"""
		cutoff_date = datetime.utcnow() - timedelta(days=days_old)
		return Case.query.filter(
			Case.is_deleted == True,
			Case.deleted_at < cutoff_date
		).all()


class Appointment(db.Model, TimestampMixin):
	__tablename__ = "appointments"
	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	appointment_number = db.Column(db.String(20), nullable=True)  # APT-001, APT-002, etc.
	full_name = db.Column(db.String(255), nullable=False)
	email = db.Column(db.String(255), nullable=False)
	appointment_date = db.Column(db.DateTime, nullable=False)
	appointment_type = db.Column(db.Enum('Complaint', 'Admission', 'Meeting', name='appointment_type'), nullable=False)
	appointment_description = db.Column(db.Text, nullable=True)  # Description field for appointment purpose
	status = db.Column(db.Enum('Pending', 'Scheduled', 'Cancelled', 'Rescheduled', name='appointment_status'), nullable=False, default='Pending')
	qr_code_data = db.Column(db.String(255), nullable=True)  # Store QR code reference if needed
	
	def __repr__(self):
		return f'<Appointment {self.id}: {self.full_name} - {self.appointment_type} on {self.appointment_date}>'
	
	@staticmethod
	def get_appointments_by_status(status=None):
		"""Get appointments filtered by status"""
		query = Appointment.query
		if status:
			query = query.filter(Appointment.status == status)
		return query.order_by(Appointment.appointment_date.asc()).all()
	
	@staticmethod
	def get_pending_appointments():
		"""Get all pending appointments"""
		return Appointment.query.filter_by(status='Pending').order_by(Appointment.appointment_date.asc()).all()
	
	@staticmethod
	def get_upcoming_appointments():
		"""Get scheduled appointments for today and future"""
		from datetime import datetime
		now = datetime.now()
		return Appointment.query.filter(
			Appointment.status == 'Scheduled',
			Appointment.appointment_date >= now
		).order_by(Appointment.appointment_date.asc()).all()
	
	@staticmethod
	def get_appointments_by_email_today(email):
		"""Get appointments by email for today (for spam protection) - Philippine timezone"""
		# Use absolute import to avoid relative import issues
		from app.utils.timezone import get_ph_today
		today = get_ph_today()
		return Appointment.query.filter(
			Appointment.email == email,
			db.func.date(Appointment.created_at) == today
		).count()
	
	@staticmethod
	def check_spam_protection(email, max_appointments=2):
		"""Check if user has exceeded daily appointment limit"""
		today_count = Appointment.get_appointments_by_email_today(email)
		return today_count >= max_appointments, today_count
	
	@staticmethod
	def generate_appointment_number():
		"""Generate daily appointment number (APT-001, APT-002, etc.) - Philippine timezone"""
		# Use absolute import to avoid relative import issues
		from app.utils.timezone import get_ph_today
		today = get_ph_today()
		
		# Count appointments created today
		today_count = Appointment.query.filter(
			db.func.date(Appointment.created_at) == today
		).count()
		
		# Generate next number (1-based)
		next_number = today_count + 1
		
		# Format as APT-XXX with zero padding
		return f"APT-{next_number:03d}"


class Notification(db.Model, TimestampMixin):
	__tablename__ = "notifications"
	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Nullable for admin notifications
	title = db.Column(db.String(255), nullable=False)
	message = db.Column(db.Text, nullable=False)
	notification_type = db.Column(db.String(50), nullable=False)  # 'appointment', 'case', etc.
	reference_id = db.Column(db.Integer, nullable=True)  # ID of the related appointment/case
	is_read = db.Column(db.Boolean, default=False, nullable=False)
	redirect_url = db.Column(db.String(500), nullable=True)  # URL to redirect when clicked
	
	def __repr__(self):
		return f'<Notification {self.id}: {self.title}>'
	
	@staticmethod
	def create_notification(title, message, notification_type, reference_id=None, redirect_url=None, user_id=None):
		"""Create a new notification"""
		notification = Notification(
			title=title,
			message=message,
			notification_type=notification_type,
			reference_id=reference_id,
			redirect_url=redirect_url,
			user_id=user_id,
			is_read=False
		)
		db.session.add(notification)
		db.session.commit()
		return notification
	
	@staticmethod
	def get_unread_notifications(user_id=None, limit=20):
		"""Get unread notifications for a user or all users (admin)"""
		query = Notification.query.filter_by(is_read=False)
		if user_id:
			query = query.filter_by(user_id=user_id)
		return query.order_by(Notification.created_at.desc()).limit(limit).all()
	
	@staticmethod
	def get_unread_count(user_id=None):
		"""Get count of unread notifications"""
		query = Notification.query.filter_by(is_read=False)
		if user_id:
			query = query.filter_by(user_id=user_id)
		return query.count()
	
	@staticmethod
	def mark_as_read(notification_id):
		"""Mark a notification as read"""
		notification = Notification.query.get(notification_id)
		if notification:
			notification.is_read = True
			db.session.commit()
			return True
		return False
	
	@staticmethod
	def mark_all_as_read(user_id=None):
		"""Mark all notifications as read for a user"""
		query = Notification.query.filter_by(is_read=False)
		if user_id:
			query = query.filter_by(user_id=user_id)
		query.update({'is_read': True})
		db.session.commit()
	
	@staticmethod
	def delete_by_reference(notification_type, reference_id):
		"""Delete notifications by reference_id and type"""
		notifications = Notification.query.filter_by(
			notification_type=notification_type,
			reference_id=reference_id
		).all()
		
		for notification in notifications:
			db.session.delete(notification)
		
		db.session.commit()
		return len(notifications)
	
	@staticmethod
	def notify_admin_user_action(action_performed, details, notification_type, reference_id=None, redirect_url=None):
		"""Send notification to admin when a user (discipline committee) performs an action"""
		# Get the admin user (discipline officer)
		admin_user = User.query.join(User.role).filter(Role.name == 'admin').first()
		if not admin_user:
			return None
		
		# Create notification for admin
		notification = Notification.create_notification(
			title=f"User Action: {action_performed}",
			message=f"Discipline Committee performed: {details}",
			notification_type=notification_type,
			reference_id=reference_id,
			redirect_url=redirect_url,
			user_id=admin_user.id
		)
		
		return notification


class SystemSettings(db.Model):
	__tablename__ = "system_settings"
	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	system_name = db.Column(db.String(255), default='WATCH System', nullable=False)
	school_name = db.Column(db.String(255), default='Your School Name', nullable=False)
	school_website = db.Column(db.String(255), default='', nullable=True)
	academic_year = db.Column(db.String(50), default='2024-2025', nullable=False)
	updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
	
	def __repr__(self):
		return f'<SystemSettings {self.id}: {self.system_name}>'
	
	@staticmethod
	def get_settings():
		"""Get system settings (creates default if doesn't exist)"""
		settings = SystemSettings.query.first()
		if not settings:
			# Create default settings
			settings = SystemSettings(
				system_name='WATCH System',
				school_name='Your School Name',
				school_website='',
				academic_year='2024-2025'
			)
			db.session.add(settings)
			db.session.commit()
		return settings
	
	@staticmethod
	def update_settings(school_name, school_website, academic_year):
		"""Update system settings"""
		settings = SystemSettings.get_settings()
		settings.school_name = school_name
		settings.school_website = school_website
		settings.academic_year = academic_year
		db.session.commit()
		return settings


class EmailSettings(db.Model):
	__tablename__ = "email_settings"
	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	enabled = db.Column(db.Boolean, default=False, nullable=False)
	provider = db.Column(db.String(20), default='gmail', nullable=False)  # 'gmail' or 'outlook'
	sender_email = db.Column(db.String(255), nullable=True)
	sender_password = db.Column(db.String(255), nullable=True)  # Current provider password
	gmail_password = db.Column(db.String(255), nullable=True)  # Gmail app password
	outlook_password = db.Column(db.String(255), nullable=True)  # Outlook app password
	sender_name = db.Column(db.String(255), default='Discipline Office', nullable=False)
	updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
	
	def __repr__(self):
		return f'<EmailSettings {self.id}: {self.provider} - {self.sender_email}>'
	
	@staticmethod
	def get_settings():
		"""Get email settings (creates default if doesn't exist)"""
		settings = EmailSettings.query.first()
		if not settings:
			# Create default settings
			settings = EmailSettings(
				enabled=False,
				provider='gmail',
				sender_email='',
				sender_password='',
				gmail_password='',
				outlook_password='',
				sender_name='Discipline Office'
			)
			try:
				db.session.add(settings)
				db.session.commit()
			except Exception as e:
				db.session.rollback()
				# If commit fails, return the settings object anyway (it exists in memory)
				print(f"⚠️ Warning: Could not save default email settings to database: {e}")
		return settings
	
	@staticmethod
	def update_settings(enabled, provider, sender_email, sender_password, sender_name):
		"""Update email settings"""
		settings = EmailSettings.get_settings()
		settings.enabled = enabled
		settings.provider = provider
		settings.sender_email = sender_email
		settings.sender_name = sender_name
		
		# Update provider-specific password and current password
		if sender_password:  # Only update if provided
			if provider == 'gmail':
				settings.gmail_password = sender_password
			elif provider == 'outlook':
				settings.outlook_password = sender_password
			settings.sender_password = sender_password
		
		db.session.commit()
		return settings
	
	def get_current_password(self):
		"""Get the password for the current provider"""
		if self.provider == 'gmail':
			return self.gmail_password or self.sender_password
		elif self.provider == 'outlook':
			return self.outlook_password or self.sender_password
		return self.sender_password
	
	@staticmethod
	def is_configured():
		"""Check if email is properly configured"""
		try:
			settings = EmailSettings.get_settings()
			if not settings:
				return False
			
			# Check all required fields
			has_email = bool(settings.sender_email and settings.sender_email.strip())
			has_password = bool(settings.get_current_password() and settings.get_current_password().strip())
			is_enabled = bool(settings.enabled)
			
			# Debug output
			if not is_enabled:
				print(f"⚠️ Email is disabled in settings")
			if not has_email:
				print(f"⚠️ Sender email is missing or empty")
			if not has_password:
				print(f"⚠️ Email password is missing or empty")
			
			return is_enabled and has_email and has_password
		except Exception as e:
			print(f"❌ Error checking email configuration: {e}")
			return False


