from flask import jsonify, render_template, redirect, url_for, request, flash, session
from ...auth_utils import login_required, admin_required
from ...models import EmailSettings, SystemSettings, User, Role
from ...extensions import db
from . import bp


# Keep the old decorator for backward compatibility, but it now uses admin_required
def discipline_officer_required(f):
	"""Decorator to require Discipline Officer role (alias for admin_required)"""
	return admin_required(f)


@bp.get('/')
@login_required
def get_settings():
	"""Redirect to system settings by default"""
	return redirect(url_for('settings.system_settings'))


@bp.get('/system')
@login_required
@discipline_officer_required
def system_settings():
	"""System settings page - General configuration"""
	# Get settings from database
	email_settings = EmailSettings.get_settings()
	system_settings = SystemSettings.get_settings()
	return render_template("settings/system_settings.html", 
						  email_settings=email_settings, 
						  system_settings=system_settings)


@bp.get('/users')
@login_required
@discipline_officer_required
def user_management():
	"""User management page - Manage users and roles"""
	# Get all users with their roles
	users = User.query.join(Role).all()
	roles = Role.query.all()
	
	# Calculate statistics
	total_users = len(users)
	active_users = len([u for u in users if u.is_active])
	inactive_users = len([u for u in users if not u.is_active])
	
	return render_template("settings/user_management.html", 
						  users=users, 
						  roles=roles,
						  total_users=total_users,
						  active_users=active_users,
						  inactive_users=inactive_users)


@bp.get('/reports')
@login_required
@discipline_officer_required
def reports():
	"""Reports page - Generate and view reports"""
	# Get some basic statistics for the dashboard
	from ...models import User, AuditLog, ActivityLog
	from datetime import date
	
	# Get recent activity logs
	recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(5).all()
	
	# Get user count
	user_count = User.query.count()
	
	# Get total audit logs count
	total_logs = AuditLog.query.count()
	
	return render_template("settings/reports.html", 
						  recent_logs=recent_logs,
						  user_count=user_count,
						  total_logs=total_logs,
						  today=date.today())


@bp.post('/email/save')
@login_required
@discipline_officer_required
def save_email_settings():
	"""Save email configuration settings"""
	try:
		# Get form data
		enabled = request.form.get('enabled') == 'on' or request.form.get('enabled') == 'true'
		provider = request.form.get('provider', 'gmail')
		sender_email = request.form.get('sender_email', '').strip()
		sender_password = request.form.get('sender_password', '').strip()
		sender_name = request.form.get('sender_name', 'Discipline Office').strip()
		
		# Validation
		if enabled and not sender_email:
			return jsonify({'success': False, 'error': 'Please provide a sender email address'})
		
		# Update settings
		EmailSettings.update_settings(
			enabled=enabled,
			provider=provider,
			sender_email=sender_email,
			sender_password=sender_password,
			sender_name=sender_name
		)
		
		return jsonify({'success': True, 'message': 'Email settings saved successfully!'})
		
	except Exception as e:
		return jsonify({'success': False, 'error': f'Error saving email settings: {str(e)}'})


@bp.post('/email/test')
@login_required
@discipline_officer_required
def test_email_connection():
	"""Test email connection with current settings"""
	try:
		from ...services.email_service import EmailService
		
		# Get test email from form or use sender email as test recipient
		test_email = request.form.get('test_email', '').strip()
		
		# Get current settings (either from form or database)
		if request.form.get('sender_email'):
			# Testing with form data (before saving)
			from ...models import EmailSettings as ES
			
			# Temporarily create settings object for testing
			class TempSettings:
				def __init__(self):
					self.enabled = True
					self.provider = request.form.get('provider', 'outlook')
					self.sender_email = request.form.get('sender_email', '').strip()
					self.sender_password = request.form.get('sender_password', '').strip()
					self.gmail_password = request.form.get('sender_password', '').strip() if self.provider == 'gmail' else ''
					self.outlook_password = request.form.get('sender_password', '').strip() if self.provider == 'outlook' else ''
					self.sender_name = request.form.get('sender_name', 'Discipline Office').strip()
				
				def is_configured(self):
					return bool(self.sender_email and self.sender_password)
				
				def get_current_password(self):
					"""Get the password for the current provider"""
					if self.provider == 'gmail':
						return self.gmail_password or self.sender_password
					elif self.provider == 'outlook':
						return self.outlook_password or self.sender_password
					return self.sender_password
			
			# Temporarily override get_settings for testing
			original_get_settings = ES.get_settings
			ES.get_settings = lambda: TempSettings()
		
		# Use sender email as test recipient if no test email provided
		if not test_email:
			email_settings = EmailSettings.get_settings()
			test_email = email_settings.sender_email or "test@example.com"
		
		# Try sending test email
		success = EmailService.send_email(
			to_email=test_email,
			subject="WATCH System - Test Email",
			body="This is a test email from the WATCH system. If you received this, your email configuration is working correctly!"
		)
		
		# Restore original get_settings if we temporarily overrode it
		if request.form.get('sender_email'):
			EmailSettings.get_settings = original_get_settings
		
		if success:
			return jsonify({
				'success': True,
				'message': f'Email sent successfully to {test_email}! Check your inbox.'
			}), 200
		else:
			return jsonify({
				'success': False,
				'message': 'Failed to send email. Please check your email settings and credentials.'
			}), 400
			
	except Exception as e:
		error_msg = str(e)
		
		# Provide specific error messages
		if 'Authentication' in error_msg or 'auth' in error_msg.lower() or '535' in error_msg:
			provider = request.form.get('provider', 'gmail')
			if provider == 'gmail':
				error_msg = 'Gmail Authentication failed. Please check:\n' \
						   '1. Email address is correct\n' \
						   '2. You are using an App Password (not your regular Gmail password)\n' \
						   '3. 2-Step Verification is enabled on your Google account\n' \
						   '4. App Password is generated for "Mail" application'
			else:
				error_msg = 'Outlook Authentication failed. Please check:\n' \
						   '1. Email address is correct\n' \
						   '2. Password is correct\n' \
						   '3. If using Microsoft account, you may need an App Password or contact IT to enable SMTP'
		elif 'Connection' in error_msg or 'connection' in error_msg.lower():
			error_msg = 'Connection failed. Please check your internet connection.'
		elif '535' in error_msg:
			error_msg = 'Authentication failed. Please use an App Password instead of your regular email password.'
		else:
			error_msg = f'Email test failed: {error_msg}'
		
		return jsonify({
			'success': False,
			'message': error_msg
		}), 500


@bp.get('/email/password-status')
@login_required
@discipline_officer_required
def get_password_status():
	"""Get password status for a specific provider"""
	try:
		provider = request.args.get('provider', 'gmail')
		settings = EmailSettings.get_settings()
		
		has_password = False
		if provider == 'gmail':
			has_password = bool(settings.gmail_password)
		elif provider == 'outlook':
			has_password = bool(settings.outlook_password)
		
		return jsonify({
			'has_password': has_password,
			'provider': provider
		}), 200
		
	except Exception as e:
		return jsonify({
			'has_password': False,
			'error': str(e)
		}), 500


@bp.post('/system/save')
@login_required
@discipline_officer_required
def save_system_settings():
	"""Save general system settings"""
	try:
		# Get form data
		school_name = request.form.get('school_name', '').strip()
		school_website = request.form.get('school_website', '').strip()
		academic_year = request.form.get('academic_year', '').strip()
		
		# Validation
		if not school_name:
			flash('School name is required', 'error')
			return redirect(url_for('settings.system_settings'))
		
		if not academic_year:
			flash('Academic year is required', 'error')
			return redirect(url_for('settings.system_settings'))
		
		# Update settings
		SystemSettings.update_settings(
			school_name=school_name,
			school_website=school_website,
			academic_year=academic_year
		)
		
		flash('System settings saved successfully!', 'success')
		return redirect(url_for('settings.system_settings') + '?system_saved=true')
		
	except Exception as e:
		flash(f'Error saving system settings: {str(e)}', 'error')
		return redirect(url_for('settings.system_settings'))


@bp.post('/users/add')
@login_required
@discipline_officer_required
def add_user():
	"""Add a new user"""
	try:
		username = request.form.get('username', '').strip()
		email = request.form.get('email', '').strip()
		password = request.form.get('password', '').strip()
		role_id = request.form.get('role_id', '').strip()
		
		# Validation
		if not username or not email or not password or not role_id:
			return jsonify({'success': False, 'error': 'All fields are required'}), 400
		
		# Check if username already exists
		if User.query.filter_by(username=username).first():
			return jsonify({'success': False, 'error': 'Username already exists'}), 400
		
		# Check if email already exists
		if User.query.filter_by(email=email).first():
			return jsonify({'success': False, 'error': 'Email already exists'}), 400
		
		# Create new user
		user = User(
			username=username,
			email=email,
			role_id=int(role_id),
			is_active=True  # New users are active by default
		)
		user.set_password(password)
		
		db.session.add(user)
		db.session.commit()
		
		return jsonify({'success': True, 'message': 'User added successfully!'}), 200
		
	except Exception as e:
		db.session.rollback()
		return jsonify({'success': False, 'error': str(e)}), 500


@bp.post('/users/edit/<int:user_id>')
@login_required
@discipline_officer_required
def edit_user(user_id):
	"""Edit an existing user"""
	try:
		user = User.query.get_or_404(user_id)
		
		username = request.form.get('username', '').strip()
		email = request.form.get('email', '').strip()
		role_id = request.form.get('role_id', '').strip()
		password = request.form.get('password', '').strip()
		
		# Validation
		if not username or not email or not role_id:
			return jsonify({'success': False, 'error': 'Username, email, and role are required'}), 400
		
		# Check if username already exists (excluding current user)
		existing_user = User.query.filter_by(username=username).first()
		if existing_user and existing_user.id != user_id:
			return jsonify({'success': False, 'error': 'Username already exists'}), 400
		
		# Check if email already exists (excluding current user)
		existing_email = User.query.filter_by(email=email).first()
		if existing_email and existing_email.id != user_id:
			return jsonify({'success': False, 'error': 'Email already exists'}), 400
		
		# Update user
		user.username = username
		user.email = email
		user.role_id = int(role_id)
		
		# Update password if provided
		if password:
			user.set_password(password)
		
		db.session.commit()
		
		return jsonify({'success': True, 'message': 'User updated successfully!'}), 200
		
	except Exception as e:
		db.session.rollback()
		return jsonify({'success': False, 'error': str(e)}), 500


@bp.post('/users/toggle-status/<int:user_id>')
@login_required
@discipline_officer_required
def toggle_user_status(user_id):
	"""Toggle user active/inactive status"""
	try:
		user = User.query.get_or_404(user_id)
		
		# Prevent deactivating the current user
		if user.id == session.get('user_id'):
			return jsonify({'success': False, 'error': 'Cannot deactivate your own account'}), 400
		
		# Prevent deactivating protected accounts
		if user.is_protected:
			return jsonify({'success': False, 'error': 'Cannot deactivate protected admin account'}), 403
		
		# Toggle status
		user.is_active = not user.is_active
		db.session.commit()
		
		status_text = "activated" if user.is_active else "deactivated"
		return jsonify({
			'success': True, 
			'message': f'User {user.username} has been {status_text}!',
			'new_status': 'Active' if user.is_active else 'Inactive'
		}), 200
		
	except Exception as e:
		db.session.rollback()
		return jsonify({'success': False, 'error': str(e)}), 500


@bp.delete('/users/delete/<int:user_id>')
@login_required
@discipline_officer_required
def delete_user(user_id):
	"""Delete a user with security logging"""
	from ...utils.security_logger import log_admin_protection, log_security_event
	
	try:
		user = User.query.get_or_404(user_id)
		
		# Prevent deleting the current user
		if user.id == session.get('user_id'):
			return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
		
		# Prevent deleting protected accounts (admin/discipline officer)
		if user.is_protected:
			log_admin_protection('DELETE', user.id, user.username, 'Protected account flag set')
			return jsonify({'success': False, 'error': 'Cannot delete protected admin account'}), 403
		
		# Additional check: Prevent deleting any admin user
		if user.is_admin():
			log_admin_protection('DELETE', user.id, user.username, 'Administrator role detected')
			return jsonify({'success': False, 'error': 'Cannot delete administrator accounts'}), 403
		
		# Log successful deletion
		log_security_event('USER_DELETION', f"User deleted: {user.username} (ID:{user.id})")
		
		# Delete user
		db.session.delete(user)
		db.session.commit()
		
		return jsonify({'success': True, 'message': 'User deleted successfully!'}), 200
		
	except Exception as e:
		db.session.rollback()
		return jsonify({'success': False, 'error': str(e)}), 500


@bp.get('/users/get/<int:user_id>')
@login_required
@discipline_officer_required
def get_user(user_id):
	"""Get user details for editing"""
	try:
		user = User.query.get_or_404(user_id)
		return jsonify({
			'success': True,
			'user': {
				'id': user.id,
				'username': user.username,
				'email': user.email,
				'role_id': user.role_id,
				'role_name': user.role.name if user.role else None
			}
		}), 200
	except Exception as e:
		return jsonify({'success': False, 'error': str(e)}), 500


@bp.get('/api/reports/attendance')
@login_required
@discipline_officer_required
def generate_attendance_report():
	"""Generate attendance report based on AttendanceHistory"""
	# print(f"DEBUG: Attendance report requested with params: {request.args}")
	try:
		from datetime import datetime, timedelta, date
		from ...models import AttendanceHistory, Schedule
		
		# Get date range from query parameters
		start_date_str = request.args.get('start_date')
		end_date_str = request.args.get('end_date')
		
		if not start_date_str or not end_date_str:
			# Default to last 30 days
			end_date = date.today()
			start_date = end_date - timedelta(days=30)
		else:
			start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
			end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
		
		# Get attendance records within date range
		attendance_records = AttendanceHistory.query.filter(
			AttendanceHistory.date >= start_date,
			AttendanceHistory.date <= end_date
		).order_by(AttendanceHistory.date.desc(), AttendanceHistory.created_at.desc()).all()
		
		# print(f"DEBUG: Found {len(attendance_records)} attendance records")
		
		# Get schedule information for each record
		report_data = {
			'title': 'Watch Report - Attendance',
			'period': f'{start_date.strftime("%B %d, %Y")} to {end_date.strftime("%B %d, %Y")}',
			'total_records': len(attendance_records),
			'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
			'records': []
		}
		
		# Count statuses
		status_counts = {'Present': 0, 'Late': 0, 'Absent': 0, 'Not Marked': 0}
		
		for record in attendance_records:
			# Try to find schedule info by matching professor name and date
			schedule_info = None
			
			# Get weekday name for the attendance date
			weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
			weekday = weekday_names[record.date.weekday()]
			
			# Find schedule for this professor on this weekday
			schedule = Schedule.query.filter(
				Schedule.professor_name == record.professor_name,
				Schedule.day_of_week == weekday
			).first()
			
			if schedule:
				schedule_info = {
					'subject': schedule.subject,
					'time_slot': f"{schedule.start_time.strftime('%H:%M')} - {schedule.end_time.strftime('%H:%M')}",
					'room': schedule.room or 'TBA'
				}
			
			# Count status
			if record.status in status_counts:
				status_counts[record.status] += 1
			
			report_data['records'].append({
				'date': record.date.strftime('%Y-%m-%d'),
				'faculty_name': record.professor_name,
				'subject': schedule_info['subject'] if schedule_info else 'N/A',
				'time_slot': schedule_info['time_slot'] if schedule_info else 'N/A',
				'room': schedule_info['room'] if schedule_info else 'N/A',
				'status': record.status,
				'created_at': record.created_at.strftime('%Y-%m-%d %H:%M:%S')
			})
		
		report_data['status_summary'] = status_counts
		
		return jsonify({
			'success': True,
			'report_data': report_data
		}), 200
		
	except Exception as e:
		print(f"ERROR in generate_attendance_report: {str(e)}")
		import traceback
		traceback.print_exc()
		return jsonify({
			'success': False,
			'error': str(e)
		}), 500


@bp.get('/api/reports/appointments')
@login_required
@discipline_officer_required
def generate_appointments_report():
	"""Generate appointments report for confirmed appointments"""
	# print(f"DEBUG: Appointments report requested with params: {request.args}")
	try:
		from datetime import datetime, timedelta, date
		from ...models import Appointment
		
		# Get date range from query parameters
		start_date_str = request.args.get('start_date')
		end_date_str = request.args.get('end_date')
		
		if not start_date_str or not end_date_str:
			# Default to last 30 days
			end_date = date.today()
			start_date = end_date - timedelta(days=30)
		else:
			start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
			end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
		
		# Get confirmed appointments (Scheduled status) within date range
		appointments = Appointment.query.filter(
			Appointment.status == 'Scheduled',
			Appointment.appointment_date >= datetime.combine(start_date, datetime.min.time()),
			Appointment.appointment_date <= datetime.combine(end_date, datetime.max.time())
		).order_by(Appointment.appointment_date.desc()).all()
		
		# Generate report data
		report_data = {
			'title': 'Watch Report - Appointments',
			'period': f'{start_date.strftime("%B %d, %Y")} to {end_date.strftime("%B %d, %Y")}',
			'total_appointments': len(appointments),
			'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
			'appointments': []
		}
		
		# Count by appointment type
		type_counts = {'Complaint': 0, 'Admission': 0, 'Meeting': 0}
		
		for appointment in appointments:
			# Count by type
			if appointment.appointment_type in type_counts:
				type_counts[appointment.appointment_type] += 1
			
			report_data['appointments'].append({
				'id': appointment.id,
				'full_name': appointment.full_name,
				'email': appointment.email,
				'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d %H:%M'),
				'appointment_type': appointment.appointment_type,
				'appointment_description': appointment.appointment_description or 'No description provided',
				'status': appointment.status,
				'created_at': appointment.created_at.strftime('%Y-%m-%d %H:%M:%S')
			})
		
		report_data['type_summary'] = type_counts
		
		return jsonify({
			'success': True,
			'report_data': report_data
		}), 200
		
	except Exception as e:
		return jsonify({
			'success': False,
			'error': str(e)
		}), 500


@bp.get('/api/reports/cases')
@login_required
@discipline_officer_required
def generate_cases_report():
	"""Generate cases report for minor or major cases with role separation"""
	# print(f"DEBUG: Cases report requested with params: {request.args}")
	try:
		from datetime import datetime, timedelta, date
		from ...models import Case, Person
		
		# Get parameters
		start_date_str = request.args.get('start_date')
		end_date_str = request.args.get('end_date')
		case_type = request.args.get('case_type', 'minor')  # 'minor' or 'major'
		
		if not start_date_str or not end_date_str:
			# Default to last 30 days
			end_date = date.today()
			start_date = end_date - timedelta(days=30)
		else:
			start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
			end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
		
		# Get cases within date range
		cases = Case.query.filter(
			Case.case_type == case_type,
			Case.created_at >= datetime.combine(start_date, datetime.min.time()),
			Case.created_at <= datetime.combine(end_date, datetime.max.time())
		).order_by(Case.created_at.desc()).all()
		
		# print(f"DEBUG: Found {len(cases)} {case_type} cases")
		# print(f"DEBUG: Case types in database: {[c.case_type for c in Case.query.all()]}")
		# print(f"DEBUG: Person roles: {[p.role for p in Person.query.all() if p.role]}")
		
		# Debug: Check each case's person and role (commented out for production)
		# for case in cases:
		# 	person = Person.query.get(case.person_id) if case.person_id else None
		# 	if person:
		# 		print(f"DEBUG: Case {case.id} -> Person: {person.full_name}, Role: {person.role}")
		# 	else:
		# 		print(f"DEBUG: Case {case.id} -> No person found (person_id: {case.person_id})")
		
		# Generate report data
		report_data = {
			'title': f'Watch Report - {case_type.title()} Cases',
			'period': f'{start_date.strftime("%B %d, %Y")} to {end_date.strftime("%B %d, %Y")}',
			'case_type': case_type,
			'total_cases': len(cases),
			'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
			'cases': {
				'students': [],
				'faculty': [],
				'staff': []
			}
		}
		
		# Count by role
		role_counts = {'students': 0, 'faculty': 0, 'staff': 0}
		
		for case in cases:
			# Get person info
			person = Person.query.get(case.person_id) if case.person_id else None
			
			case_data = {
				'id': case.id,
				'case_number': f"CASE-{case.id:04d}",  # Generate case number
				'person_name': person.full_name if person else 'Unknown',
				'person_role': person.role if person else 'Unknown',
				'offense': case.description or 'No description provided',  # Use description as offense
				'offense_type': case.offense_type or 'N/A',  # Add offense type field
				'description': case.description,
				'remarks': case.remarks or 'No remarks',
				'status': case.status,
				'date_reported': case.date_reported.strftime('%Y-%m-%d') if case.date_reported else 'N/A',
				'created_at': case.created_at.strftime('%Y-%m-%d %H:%M:%S'),
				'updated_at': case.updated_at.strftime('%Y-%m-%d %H:%M:%S') if case.updated_at else 'N/A',
				# Add the missing fields for proper display
				'program_or_dept': person.program_or_dept if person else 'N/A',
				'section_or_position': None  # Initialize
			}
			
			# Set section_or_position based on role
			if person and person.role:
				role_key = person.role.lower()
				if role_key == 'student':
					case_data['section_or_position'] = person.section if person.section else 'N/A'
				elif role_key == 'faculty':
					case_data['section_or_position'] = person.program_or_dept if person.program_or_dept else 'N/A'  # Department for faculty
				elif role_key == 'staff':
					case_data['section_or_position'] = person.program_or_dept if person.program_or_dept else 'N/A'  # Position for staff
			
			# Separate by role - Fix the role mapping
			if person and person.role:
				role_key = person.role.lower()
				# print(f"DEBUG: Person {person.full_name} has role: {person.role} -> {role_key}")
				
				# Map roles correctly
				if role_key in ['student', 'students']:
					report_data['cases']['students'].append(case_data)
					role_counts['students'] += 1
					# print(f"DEBUG: Added to students cases")
				elif role_key in ['faculty', 'teacher', 'professor']:
					report_data['cases']['faculty'].append(case_data)
					role_counts['faculty'] += 1
					# print(f"DEBUG: Added to faculty cases")
				elif role_key in ['staff', 'employee', 'worker']:
					report_data['cases']['staff'].append(case_data)
					role_counts['staff'] += 1
					# print(f"DEBUG: Added to staff cases")
				else:
					# Handle other roles as 'staff'
					report_data['cases']['staff'].append(case_data)
					role_counts['staff'] += 1
					print(f"DEBUG: Added to staff cases (unknown role: {role_key})")
			else:
				# Unknown role goes to staff
				report_data['cases']['staff'].append(case_data)
				role_counts['staff'] += 1
				print(f"DEBUG: Added to staff cases (no person/role)")
		
		report_data['role_summary'] = role_counts
		
		return jsonify({
			'success': True,
			'report_data': report_data
		}), 200
		
	except Exception as e:
		print(f"ERROR in generate_cases_report: {str(e)}")
		import traceback
		traceback.print_exc()
		return jsonify({
			'success': False,
			'error': str(e)
		}), 500


@bp.get('/api/reports/system-logs')
@login_required
@discipline_officer_required
def generate_system_logs_report():
	"""Generate system logs report with all activity logs and audit trails"""
	# print(f"DEBUG: System logs report requested with params: {request.args}")
	try:
		from datetime import datetime, timedelta, date
		from ...models import AuditLog, User
		
		# Get date range from query parameters
		start_date_str = request.args.get('start_date')
		end_date_str = request.args.get('end_date')
		
		if not start_date_str or not end_date_str:
			# Default to last 30 days
			end_date = date.today()
			start_date = end_date - timedelta(days=30)
		else:
			start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
			end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
		
		# Get all audit logs within date range
		audit_logs = AuditLog.query.filter(
			AuditLog.timestamp >= datetime.combine(start_date, datetime.min.time()),
			AuditLog.timestamp <= datetime.combine(end_date, datetime.max.time())
		).order_by(AuditLog.timestamp.desc()).all()
		
		# Generate report data with Philippines timezone (simplified)
		ph_now = datetime.utcnow() + timedelta(hours=8)  # Philippines is UTC+8
		
		report_data = {
			'title': 'Watch Report - System Logs',
			'period': f'{start_date.strftime("%B %d, %Y")} to {end_date.strftime("%B %d, %Y")}',
			'total_logs': len(audit_logs),
			'generated_at': ph_now.strftime('%Y-%m-%d %H:%M:%S (Philippines Time)'),
			'logs': []
		}
		
		# Count by action type
		action_counts = {}
		user_counts = {}
		
		for log in audit_logs:
			# Count by action type
			action_counts[log.action_type] = action_counts.get(log.action_type, 0) + 1
			
			# Count by user (if available)
			if log.user_id:
				user = User.query.get(log.user_id)
				username = user.username if user else f"User ID {log.user_id}"
				user_counts[username] = user_counts.get(username, 0) + 1
			else:
				user_counts['System/Unknown'] = user_counts.get('System/Unknown', 0) + 1
			
			# Convert timestamp to Philippines timezone for display (simplified)
			ph_timestamp = log.timestamp + timedelta(hours=8) if log.timestamp else datetime.utcnow() + timedelta(hours=8)
			
			report_data['logs'].append({
				'id': log.id,
				'timestamp': ph_timestamp.strftime('%Y-%m-%d %H:%M:%S (Philippines Time)'),
				'action_type': log.action_type,
				'description': log.description,
				'user_id': log.user_id,
				'username': user.username if log.user_id and user else 'System/Unknown',
				'ip_address': log.ip_address or 'N/A',
				'user_agent': log.user_agent or 'N/A'
			})
		
		report_data['action_summary'] = action_counts
		report_data['user_summary'] = user_counts
		
		return jsonify({
			'success': True,
			'report_data': report_data
		}), 200
		
	except Exception as e:
		return jsonify({
			'success': False,
			'error': str(e)
		}), 500


@bp.post('/email/disconnect')
@login_required
@discipline_officer_required
def disconnect_email():
	"""Disconnect/clear email settings"""
	try:
		EmailSettings.update_settings(
			enabled=False,
			provider='gmail',
			sender_email='',
			sender_password='',
			sender_name='Discipline Office'
		)
		return jsonify({'success': True, 'message': 'Email disconnected successfully!'})
	except Exception as e:
		return jsonify({'success': False, 'error': str(e)})


@bp.get('/api')
@login_required
def get_settings_api():
	return jsonify({"reports": True}), 200


