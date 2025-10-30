from flask import jsonify, render_template, request, redirect, url_for, flash, send_file, abort
from ...auth_utils import login_required, get_current_user
from ...models import MinorCase, MajorCase, ActivityLog, Person, Case
from ...extensions import db
from ...utils.file_upload import save_attachment, delete_attachment, get_attachment_url, format_file_size
from ...utils.case_detection import case_detector
from ...utils.safe_string import sanitize_string, safe_print, sanitize_form_data
from ...utils.validation import (
    validate_name, validate_subject_course, validate_section, validate_department,
    validate_faculty_department, validate_description, validate_case_date, sanitize_and_validate_text
)
from ...services.ocr_service import OCRService
from ...services.notification_service import NotificationService
from . import bp
from datetime import datetime, date
import os
from functools import wraps


def case_read_create_only(f):
    """Decorator to restrict case operations to read/create only for discipline committee"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        
        # Admin can do everything
        if user and user.role and user.role.name.lower() == 'admin':
            return f(*args, **kwargs)
        
        # Discipline Committee can only create and read
        if user and user.role and user.role.name.lower() == 'user':
            # Check if this is an edit or delete operation
            if 'edit' in request.endpoint or 'delete' in request.endpoint:
                flash('You do not have permission to edit or delete cases. Contact the Discipline Officer.', 'error')
                return redirect(url_for('cases.minor_cases_student'))
            
            # Allow create and read operations
            return f(*args, **kwargs)
        
        # No access for unauthenticated users
        flash('Access denied. Please log in.', 'error')
        return redirect(url_for('auth.login'))
    
    return decorated_function


# Minor Cases Routes by Entity Type
@bp.get('/minor/student')
@login_required
def minor_cases_student():
	"""Display minor cases for students with DataTables"""
	# Get persons with case counts for students
	persons_with_counts = Person.get_persons_with_case_counts()
	student_persons = [(person, minor_count, major_count) for person, minor_count, major_count in persons_with_counts if person.role == 'student']
	return render_template("cases/minor_student.html", cases=[], case_type="minor", entity_type="student", today=date.today())


@bp.get('/minor/cases')
@login_required
def minor_cases_list():
	"""Display individual minor cases with Date, Remarks, Created columns"""
	# Get all minor cases (all records in MinorCase table are minor cases)
	cases = MinorCase.query.order_by(MinorCase.created_at.desc()).all()
	return render_template("cases/minor_cases.html", cases=cases, case_type="minor", entity_type="student", today=date.today())


@bp.get('/minor/faculty')
@login_required
def minor_cases_faculty():
	"""Display minor cases for faculty with DataTables"""
	return render_template("cases/minor_faculty.html", cases=[], case_type="minor", entity_type="faculty", today=date.today())


@bp.get('/minor/staff')
@login_required
def minor_cases_staff():
	"""Display minor cases for staff with DataTables"""
	return render_template("cases/minor_staff.html", cases=[], case_type="minor", entity_type="staff", today=date.today())


# Major Cases Routes by Entity Type
@bp.get('/major/student')
@login_required
def major_cases_student():
	"""Display major cases for students with DataTables"""
	return render_template("cases/major_student.html", cases=[], case_type="major", entity_type="student", today=date.today())


@bp.get('/major/faculty')
@login_required
def major_cases_faculty():
	"""Display major cases for faculty with DataTables"""
	return render_template("cases/major_faculty.html", cases=[], case_type="major", entity_type="faculty", today=date.today())


@bp.get('/major/staff')
@login_required
def major_cases_staff():
	"""Display major cases for staff with DataTables"""
	return render_template("cases/major_staff.html", cases=[], case_type="major", entity_type="staff", today=date.today())


# Minor Cases CRUD Routes
@bp.post('/minor/add/<entity_type>')
@login_required
@limiter.limit('20 per hour')  # Rate limit case creation
def add_minor_case(entity_type):
	"""Add a new minor case for specific entity type"""
	try:
		# Validate entity_type
		if entity_type not in ['student', 'faculty', 'staff']:
			flash('Invalid entity type.', 'error')
			return redirect(url_for(f'cases.minor_cases_{entity_type}'))
		
		# Validate required fields with whitespace prevention
		last_name_valid, last_name_error, last_name = sanitize_and_validate_text(
			request.form.get('last_name', ''), validate_name, "Last Name"
		)
		if not last_name_valid:
			flash(last_name_error, 'error')
			return redirect(url_for(f'cases.minor_cases_{entity_type}'))
		
		first_name_valid, first_name_error, first_name = sanitize_and_validate_text(
			request.form.get('first_name', ''), validate_name, "First Name"
		)
		if not first_name_valid:
			flash(first_name_error, 'error')
			return redirect(url_for(f'cases.minor_cases_{entity_type}'))
		
		# Use specific validation for faculty department dropdown
		if entity_type == 'faculty':
			program_or_dept_valid, program_or_dept_error, program_or_dept = sanitize_and_validate_text(
				request.form.get('program_or_dept', ''), 
				validate_faculty_department, 
				"Department"
			)
		else:
			program_or_dept_valid, program_or_dept_error, program_or_dept = sanitize_and_validate_text(
				request.form.get('program_or_dept', ''), 
				validate_department if entity_type != 'student' else validate_subject_course, 
				"Program/Department"
			)
		if not program_or_dept_valid:
			flash(program_or_dept_error, 'error')
			return redirect(url_for(f'cases.minor_cases_{entity_type}'))
		
		section = sanitize_string(request.form.get('section', ''))
		date_str = sanitize_string(request.form.get('date', ''))
		
		# Validate date
		date_valid, date_error = validate_case_date(date_str, "Date")
		if not date_valid:
			flash(date_error, 'error')
			return redirect(url_for(f'cases.minor_cases_{entity_type}'))
		
		# Section is required only for students
		if entity_type == 'student':
			section_valid, section_error, section = sanitize_and_validate_text(
				section, validate_section, "Section"
			)
			if not section_valid:
				flash(section_error, 'error')
				return redirect(url_for(f'cases.minor_cases_{entity_type}'))
		
		# Create full name
		full_name = f"{first_name} {last_name}"
		
		# Check if person already exists
		person = Person.query.filter_by(
			full_name=full_name,
			role=entity_type,
			program_or_dept=program_or_dept,
			section=section if entity_type == 'student' else None
		).first()
		
		# If person doesn't exist, create them
		if not person:
			person = Person(
				full_name=full_name,
				role=entity_type,
				program_or_dept=program_or_dept,
				section=section if entity_type == 'student' else None
			)
			db.session.add(person)
			db.session.flush()  # Get the person ID
		
		# Validate offense type (required for minor cases)
		offense_type = request.form.get('offense_type', '').strip()
		if not offense_type:
			flash('Offense Type is required.', 'error')
			return redirect(url_for(f'cases.minor_cases_{entity_type}'))
		
		# Validate optional fields
		description = request.form.get('description', '').strip()
		if description:
			description_valid, description_error, description = sanitize_and_validate_text(
				description, validate_description, "Description"
			)
			if not description_valid:
				flash(description_error, 'error')
				return redirect(url_for(f'cases.minor_cases_{entity_type}'))
		
		remarks = request.form.get('remarks', '').strip()
		if remarks:
			remarks_valid, remarks_error, remarks = sanitize_and_validate_text(
				remarks, validate_description, "Remarks"
			)
			if not remarks_valid:
				flash(remarks_error, 'error')
				return redirect(url_for(f'cases.minor_cases_{entity_type}'))
		
		# Create the case
		case = Case(
			person_id=person.id,
			case_type='minor',
			offense_type=offense_type,
			description=description or None,
			date_reported=datetime.strptime(date_str, '%Y-%m-%d').date(),
			status='open',
			remarks=remarks or None
		)
		db.session.add(case)
		db.session.commit()
		
		# Send notification to admin about new case
		user = get_current_user()
		if user and user.username != 'discipline_officer':
			try:
				NotificationService.notify_case_action(
					action='created',
					case_type='minor',
					case_id=case.id,
					action_user_name=user.full_name or user.username
				)
			except Exception as e:
				print(f"Notification error: {e}")
		
		# Log activity
		if user:
			try:
				ActivityLog.log_activity(
					user_id=user.id,
					action="Minor Case Added",
					description=f"Added minor case for {entity_type}: {person.full_name}"
				)
				
				# Send notification to admin if current user is discipline committee
				if user.role and user.role.name.lower() == 'user':
					from ...models import Notification
					Notification.notify_admin_user_action(
						action_performed="Minor Case Creation",
						details=f"Added minor case for {entity_type.title()}: {person.full_name} - {offense_type} on {datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y')}",
						notification_type="case_creation",
						redirect_url=url_for(f'cases.minor_cases_{entity_type}')
					)
			except Exception as notification_error:
				# Log notification error but don't fail the case creation
				# print(f"DEBUG: Notification error (case still created successfully): {str(notification_error)}")
				pass
				pass
		
		flash('Minor case added successfully!', 'success')
	except Exception as e:
		db.session.rollback()
		# print(f"DEBUG: Error adding minor case: {str(e)}")
		import traceback
		traceback.print_exc()
		flash('Error adding minor case. Please try again.', 'error')
	
	return redirect(url_for(f'cases.minor_cases_{entity_type}'))


@bp.post('/minor/edit/<int:case_id>')
@login_required
@case_read_create_only
def edit_minor_case(case_id):
	"""Edit an existing minor case"""
	case = MinorCase.query.get_or_404(case_id)
	
	try:
		# Validate required fields
		last_name = sanitize_string(request.form.get('last_name', ''))
		first_name = sanitize_string(request.form.get('first_name', ''))
		program_or_dept = sanitize_string(request.form.get('program_or_dept', ''))
		section = sanitize_string(request.form.get('section', ''))
		date_str = sanitize_string(request.form.get('date', ''))
		
		if not all([last_name, first_name, program_or_dept, date_str]):
			flash('Please fill in all required fields.', 'error')
			return redirect(url_for(f'cases.minor_cases_{case.entity_type}'))
		
		# Section is required only for students
		if case.entity_type == 'student' and not section:
			flash('Section is required for students.', 'error')
			return redirect(url_for(f'cases.minor_cases_{case.entity_type}'))
		
		case.last_name = last_name
		case.first_name = first_name
		case.program_or_dept = program_or_dept
		case.section = section if case.entity_type == 'student' else None
		case.date = datetime.strptime(date_str, '%Y-%m-%d').date()
		case.remarks = request.form.get('remarks', '').strip() or None
		case.updated_at = datetime.utcnow()
		
		db.session.commit()
		
		# Log activity
		user = get_current_user()
		if user:
			ActivityLog.log_activity(
				user_id=user.id,
				action="Minor Case Updated",
				description=f"Updated minor case for {case.entity_type}: {case.first_name} {case.last_name}"
			)
		
		flash('Minor case updated successfully!', 'success')
	except Exception as e:
		db.session.rollback()
		flash('Error updating minor case. Please try again.', 'error')
	
	return redirect(url_for(f'cases.minor_cases_{case.entity_type}'))


@bp.post('/minor/delete/<int:case_id>')
@login_required
@case_read_create_only
def delete_minor_case(case_id):
	"""Delete a minor case"""
	case = MinorCase.query.get_or_404(case_id)
	
	try:
		case_name = f"{case.first_name} {case.last_name}"
		entity_type = case.entity_type
		db.session.delete(case)
		db.session.commit()
		
		# Log activity
		user = get_current_user()
		if user:
			ActivityLog.log_activity(
				user_id=user.id,
				action="Minor Case Deleted",
				description=f"Deleted minor case for {entity_type}: {case_name}"
			)
		
		flash('Minor case deleted successfully!', 'success')
	except Exception as e:
		db.session.rollback()
		flash('Error deleting minor case. Please try again.', 'error')
	
	return redirect(url_for(f'cases.minor_cases_{entity_type}'))


# Major Cases CRUD Routes
@bp.post('/major/add/<entity_type>')
@login_required
@limiter.limit('20 per hour')  # Rate limit case creation
def add_major_case(entity_type):
	"""Add a new major case for specific entity type"""
	try:
		# Validate entity_type
		if entity_type not in ['student', 'faculty', 'staff']:
			flash('Invalid entity type.', 'error')
			return redirect(url_for(f'cases.major_cases_{entity_type}'))
		
		# Validate required fields with whitespace prevention
		last_name_valid, last_name_error, last_name = sanitize_and_validate_text(
			request.form.get('last_name', ''), validate_name, "Last Name"
		)
		if not last_name_valid:
			flash(last_name_error, 'error')
			return redirect(url_for(f'cases.major_cases_{entity_type}'))
		
		first_name_valid, first_name_error, first_name = sanitize_and_validate_text(
			request.form.get('first_name', ''), validate_name, "First Name"
		)
		if not first_name_valid:
			flash(first_name_error, 'error')
			return redirect(url_for(f'cases.major_cases_{entity_type}'))
		
		program_or_dept_valid, program_or_dept_error, program_or_dept = sanitize_and_validate_text(
			request.form.get('program_or_dept', ''), 
			validate_department if entity_type != 'student' else validate_subject_course, 
			"Program/Department"
		)
		if not program_or_dept_valid:
			flash(program_or_dept_error, 'error')
			return redirect(url_for(f'cases.major_cases_{entity_type}'))
		
		section = sanitize_string(request.form.get('section', ''))
		date_str = sanitize_string(request.form.get('date', ''))
		
		# Validate date
		date_valid, date_error = validate_case_date(date_str, "Date")
		if not date_valid:
			flash(date_error, 'error')
			return redirect(url_for(f'cases.major_cases_{entity_type}'))
		
		# Validate offense category (required for major cases)
		category = request.form.get('category', '').strip()
		if not category:
			flash('Category is required.', 'error')
			return redirect(url_for(f'cases.major_cases_{entity_type}'))
		
		# Validate offense type (required for major cases)
		offense = request.form.get('offense', '').strip()
		if not offense:
			flash('Specific Offense is required.', 'error')
			return redirect(url_for(f'cases.major_cases_{entity_type}'))
		
		# Section is required only for students
		if entity_type == 'student':
			section_valid, section_error, section = sanitize_and_validate_text(
				section, validate_section, "Section"
			)
			if not section_valid:
				flash(section_error, 'error')
				return redirect(url_for(f'cases.major_cases_{entity_type}'))
		
		# Create full name
		full_name = f"{first_name} {last_name}"
		
		# Check if person already exists
		person = Person.query.filter_by(
			full_name=full_name,
			role=entity_type,
			program_or_dept=program_or_dept,
			section=section if entity_type == 'student' else None
		).first()
		
		# If person doesn't exist, create them
		if not person:
			person = Person(
				full_name=full_name,
				role=entity_type,
				program_or_dept=program_or_dept,
				section=section if entity_type == 'student' else None
			)
			db.session.add(person)
			db.session.flush()  # Get the person ID
		
		# Validate optional fields
		description = request.form.get('description', '').strip()
		if description:
			description_valid, description_error, description = sanitize_and_validate_text(
				description, validate_description, "Description"
			)
			if not description_valid:
				flash(description_error, 'error')
				return redirect(url_for(f'cases.major_cases_{entity_type}'))
		
		remarks = request.form.get('remarks', '').strip()
		if remarks:
			remarks_valid, remarks_error, remarks = sanitize_and_validate_text(
				remarks, validate_description, "Remarks"
			)
			if not remarks_valid:
				flash(remarks_error, 'error')
				return redirect(url_for(f'cases.major_cases_{entity_type}'))
		
		# Create the case
		case = Case(
			person_id=person.id,
			case_type='major',
			offense_category=category,
			offense_type=offense,
			description=description or None,
			date_reported=datetime.strptime(date_str, '%Y-%m-%d').date(),
			status='open',
			remarks=remarks or None
		)
		db.session.add(case)
		db.session.flush()  # Get the case ID for file upload
		
		# Handle file upload for major cases only
		attachment_info = None
		if 'attachment' in request.files:
			file = request.files['attachment']
			if file and file.filename != '':
				try:
					attachment_info = save_attachment(file, case.id, 'major')
					if attachment_info:
						case.attachment_filename = attachment_info['filename']
						case.attachment_data = attachment_info['data']
						case.attachment_size = attachment_info['size']
						case.attachment_type = attachment_info['type']
						case.attachment_hash = attachment_info['hash']
				except ValueError as e:
					flash(f'File upload error: {str(e)}', 'error')
					db.session.rollback()
					return redirect(url_for(f'cases.major_cases_{entity_type}'))
				except Exception as e:
					flash('Error uploading file. Please try again.', 'error')
					db.session.rollback()
					return redirect(url_for(f'cases.major_cases_{entity_type}'))
		
		db.session.commit()
		
		# Send notification to admin about new major case
		user = get_current_user()
		if user and user.username != 'discipline_officer':
			try:
				NotificationService.notify_case_action(
					action='created',
					case_type='major',
					case_id=case.id,
					action_user_name=user.full_name or user.username
				)
			except Exception as e:
				print(f"Notification error: {e}")
		
		# Log activity
		if user:
			try:
				activity_desc = f"Added major case for {entity_type}: {person.full_name}"
				if attachment_info:
					activity_desc += f" with attachment: {attachment_info['filename']}"
				ActivityLog.log_activity(
					user_id=user.id,
					action="Major Case Added",
					description=activity_desc
				)
				
				# Send notification to admin if current user is discipline committee
				if user.role and user.role.name.lower() == 'user':
					from ...models import Notification
					notification_details = f"Added major case for {entity_type.title()}: {person.full_name} - {category}: {offense} on {datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y')}"
					if attachment_info:
						notification_details += f" with attachment: {attachment_info['filename']}"
					Notification.notify_admin_user_action(
						action_performed="Major Case Creation",
						details=notification_details,
						notification_type="case_creation",
						redirect_url=url_for(f'cases.major_cases_{entity_type}')
					)
			except Exception as notification_error:
				# Log notification error but don't fail the case creation
				# print(f"DEBUG: Notification error (case still created successfully): {str(notification_error)}")
				pass
		
		success_msg = 'Major case added successfully!'
		if attachment_info:
			success_msg += f' File "{attachment_info["filename"]}" uploaded.'
		flash(success_msg, 'success')
	except Exception as e:
		db.session.rollback()
		flash('Error adding major case. Please try again.', 'error')
	
	return redirect(url_for(f'cases.major_cases_{entity_type}'))


@bp.post('/major/edit/<int:case_id>')
@login_required
@case_read_create_only
def edit_major_case(case_id):
	"""Edit an existing major case"""
	case = MajorCase.query.get_or_404(case_id)
	
	try:
		# Validate required fields
		last_name = sanitize_string(request.form.get('last_name', ''))
		first_name = sanitize_string(request.form.get('first_name', ''))
		program_or_dept = sanitize_string(request.form.get('program_or_dept', ''))
		section = sanitize_string(request.form.get('section', ''))
		date_str = sanitize_string(request.form.get('date', ''))
		
		if not all([last_name, first_name, program_or_dept, date_str]):
			flash('Please fill in all required fields.', 'error')
			return redirect(url_for(f'cases.major_cases_{case.entity_type}'))
		
		# Section is required only for students
		if case.entity_type == 'student' and not section:
			flash('Section is required for students.', 'error')
			return redirect(url_for(f'cases.major_cases_{case.entity_type}'))
		
		# Handle file upload for major cases only
		attachment_info = None
		if 'attachment' in request.files:
			file = request.files['attachment']
			if file and file.filename != '':
				try:
					# Clear old attachment data from database
					from ...utils.file_upload import clear_case_attachment
					clear_case_attachment(case)
					
					attachment_info = save_attachment(file, case.id, 'major')
					if attachment_info:
						case.attachment_filename = attachment_info['filename']
						case.attachment_data = attachment_info['data']
						case.attachment_size = attachment_info['size']
						case.attachment_type = attachment_info['type']
						case.attachment_hash = attachment_info['hash']
				except ValueError as e:
					flash(f'File upload error: {str(e)}', 'error')
					return redirect(url_for(f'cases.major_cases_{case.entity_type}'))
				except Exception as e:
					flash('Error uploading file. Please try again.', 'error')
					return redirect(url_for(f'cases.major_cases_{case.entity_type}'))
		
		case.last_name = last_name
		case.first_name = first_name
		case.program_or_dept = program_or_dept
		case.section = section if case.entity_type == 'student' else None
		case.date = datetime.strptime(date_str, '%Y-%m-%d').date()
		case.remarks = request.form.get('remarks', '').strip() or None
		case.updated_at = datetime.utcnow()
		
		db.session.commit()
		
		# Log activity
		user = get_current_user()
		if user:
			activity_desc = f"Updated major case for {case.entity_type}: {case.first_name} {case.last_name}"
			if attachment_info:
				activity_desc += f" with new attachment: {attachment_info['filename']}"
			ActivityLog.log_activity(
				user_id=user.id,
				action="Major Case Updated",
				description=activity_desc
			)
		
		success_msg = 'Major case updated successfully!'
		if attachment_info:
			success_msg += f' File "{attachment_info["filename"]}" uploaded.'
		flash(success_msg, 'success')
	except Exception as e:
		db.session.rollback()
		flash('Error updating major case. Please try again.', 'error')
	
	return redirect(url_for(f'cases.major_cases_{case.entity_type}'))


@bp.post('/major/delete/<int:case_id>')
@login_required
@case_read_create_only
def delete_major_case(case_id):
	"""Delete a major case"""
	case = MajorCase.query.get_or_404(case_id)
	
	try:
		case_name = f"{case.first_name} {case.last_name}"
		entity_type = case.entity_type
		
		# Clear attachment data from database (no file deletion needed)
		from ...utils.file_upload import clear_case_attachment
		clear_case_attachment(case)
		
		db.session.delete(case)
		db.session.commit()
		
		# Log activity
		user = get_current_user()
		if user:
			ActivityLog.log_activity(
				user_id=user.id,
				action="Major Case Deleted",
				description=f"Deleted major case for {entity_type}: {case_name}"
			)
		
		flash('Major case deleted successfully!', 'success')
	except Exception as e:
		db.session.rollback()
		flash('Error deleting major case. Please try again.', 'error')
	
	return redirect(url_for(f'cases.major_cases_{entity_type}'))


# Attachment Routes
@bp.get('/attachment/<int:case_id>')
@login_required
def download_attachment(case_id):
	"""Download attachment for a case (supports both MajorCase and Case models) - Database BLOB storage"""
	# Try to find the case in both models
	case = MajorCase.query.get(case_id)
	if not case:
		case = Case.query.get(case_id)
	
	if not case:
		abort(404)
	
	# Check if attachment exists in database
	if not case.attachment_data or not case.attachment_filename:
		abort(404)
	
	try:
		from io import BytesIO
		from flask import Response
		
		# Create BytesIO object from database BLOB
		file_data = BytesIO(case.attachment_data)
		
		# Return file as download
		return Response(
			file_data.getvalue(),
			mimetype=case.attachment_type or 'application/octet-stream',
			headers={
				'Content-Disposition': f'attachment; filename="{case.attachment_filename}"',
				'Content-Length': str(case.attachment_size or len(case.attachment_data))
			}
		)
	except Exception as e:
		abort(404)


@bp.get('/view-attachment/<int:case_id>')
@login_required
def view_attachment(case_id):
	"""View attachment in new tab (supports both MajorCase and Case models) - Database BLOB storage"""
	# Try to find the case in both models
	case = MajorCase.query.get(case_id)
	if not case:
		case = Case.query.get(case_id)
	
	if not case:
		abort(404)
	
	# Check if attachment exists in database
	if not case.attachment_data or not case.attachment_filename:
		abort(404)
	
	try:
		from io import BytesIO
		from flask import Response
		
		# Create BytesIO object from database BLOB
		file_data = BytesIO(case.attachment_data)
		
		# Return file for viewing (not as download)
		return Response(
			file_data.getvalue(),
			mimetype=case.attachment_type or 'application/octet-stream',
			headers={
				'Content-Disposition': f'inline; filename="{case.attachment_filename}"',
				'Content-Length': str(case.attachment_size or len(case.attachment_data))
			}
		)
	except Exception as e:
		abort(404)


@bp.post('/attachment/<int:case_id>/delete')
@login_required
def delete_case_attachment(case_id):
	"""Delete attachment from a case (supports both MajorCase and Case models)"""
	# Try to find the case in both models
	case = MajorCase.query.get(case_id)
	if not case:
		case = Case.query.get(case_id)
	
	if not case:
		abort(404)
	
	try:
		# Clear attachment data from database
		from ...utils.file_upload import clear_case_attachment
		clear_case_attachment(case)
		
		db.session.commit()
		
		# Log activity
		user = get_current_user()
		if user:
			# Get case name based on model type
			if hasattr(case, 'first_name'):  # MajorCase
				case_name = f"{case.first_name} {case.last_name}"
				entity_type = case.entity_type
			else:  # Case
				case_name = case.person.full_name if case.person else f"Case {case.id}"
				entity_type = case.person.role if case.person else 'unknown'
			
			ActivityLog.log_activity(
				user_id=user.id,
				action="Attachment Deleted",
				description=f"Deleted attachment from case: {case_name}"
			)
		
		flash('Attachment deleted successfully!', 'success')
	except Exception as e:
		db.session.rollback()
		flash('Error deleting attachment. Please try again.', 'error')
	
	# Redirect based on model type
	if hasattr(case, 'entity_type'):  # MajorCase
		return redirect(url_for(f'cases.major_cases_{case.entity_type}'))
	else:  # Case
		entity_type = case.person.role if case.person else 'student'
		return redirect(url_for(f'cases.major_cases_{entity_type}'))


# OCR Integration Routes
@bp.post('/minor/ocr-extract/<entity_type>')
@login_required
def minor_ocr_extract(entity_type):
	"""Extract data using OCR for minor cases - DISABLED (OCR only for major cases)"""
	# OCR is disabled for minor cases as they don't typically need document scanning
	return jsonify({'error': 'OCR is only available for major cases'}), 400


@bp.post('/major/ocr-extract/<entity_type>')
@login_required
def major_ocr_extract(entity_type):
	"""Extract data using OCR for major cases"""
	# This would integrate with existing OCR module
	# For now, return sample data based on entity type
	
	# Sample descriptions for different case types
	sample_descriptions = {
		'student': [
			'Student was caught cheating during the final exam using unauthorized materials and crib notes.',
			'Student involved in a physical fight with another student in the cafeteria, causing disruption.',
			'Student found smoking in the school restroom, violating the no-smoking policy.',
			'Student repeatedly using mobile phone during class despite warnings, disrupting other students.',
			'Student caught stealing another student\'s laptop from the computer lab.',
			'Student showing disrespectful behavior towards teacher, using inappropriate language and being defiant.',
			'Student vandalizing school property by writing graffiti on classroom walls.',
			'Student frequently absent without proper excuse, affecting academic performance.'
		],
		'faculty': [
			'Faculty member reported for inappropriate behavior during office hours with students.',
			'Faculty member found intoxicated during class, affecting teaching quality.',
			'Faculty member using school equipment for personal purposes without authorization.',
			'Faculty member showing favoritism and unfair treatment towards certain students.',
			'Faculty member violating dress code policy by wearing inappropriate attire to class.'
		],
		'staff': [
			'Staff member involved in workplace misconduct, creating hostile environment.',
			'Staff member caught stealing office supplies and school property.',
			'Staff member using school computer systems for unauthorized personal activities.',
			'Staff member showing disrespectful behavior towards students and colleagues.',
			'Staff member frequently late and absent without proper notification.'
		]
	}
	
	# Get random sample description
	import random
	description = random.choice(sample_descriptions.get(entity_type, ['General disciplinary incident reported.']))
	
	if entity_type == 'student':
		extracted_data = {
			'last_name': 'Sample',
			'first_name': 'Student',
			'program_or_dept': 'Computer Science',
			'section': 'A',
			'date': datetime.now().strftime('%Y-%m-%d'),
			'description': description,
			'remarks': ''  # Empty for Discipline Officer to fill
		}
	elif entity_type == 'faculty':
		extracted_data = {
			'last_name': 'Professor',
			'first_name': 'Sample',
			'program_or_dept': 'Computer Science Department',
			'section': '',
			'date': datetime.now().strftime('%Y-%m-%d'),
			'description': description,
			'remarks': ''  # Empty for Discipline Officer to fill
		}
	else:  # staff
		extracted_data = {
			'last_name': 'Staff',
			'first_name': 'Sample',
			'program_or_dept': 'Administrative Office',
			'section': '',
			'date': datetime.now().strftime('%Y-%m-%d'),
			'description': description,
			'remarks': ''  # Empty for Discipline Officer to fill
		}
	return jsonify(extracted_data)


# New Person-Centric Case Management Routes


@bp.get('/api/persons')
@login_required
def get_persons_api():
	"""API endpoint to get persons with case counts (for AJAX)"""
	search_term = request.args.get('search', '').strip()
	role_filter = request.args.get('role', '').strip()
	
	if search_term:
		persons = Person.search_persons(search_term, role_filter if role_filter else None)
		# Convert to format with case counts
		persons_with_counts = []
		for person in persons:
			minor_count = Case.query.filter_by(person_id=person.id, case_type='minor').count()
			major_count = Case.query.filter_by(person_id=person.id, case_type='major').count()
			persons_with_counts.append((person, minor_count, major_count))
	else:
		# Apply role filter even when no search term
		if role_filter:
			persons_with_counts = Person.get_persons_with_case_counts(role_filter=role_filter)
		else:
			persons_with_counts = Person.get_persons_with_case_counts()
	
	# Convert to JSON-serializable format
	result = []
	for person_data in persons_with_counts:
		person, minor_count, major_count = person_data
		
		# Get latest major case info for date display
		latest_major_case = Case.query.filter_by(person_id=person.id, case_type='major').order_by(Case.date_reported.desc()).first()
		latest_date = latest_major_case.date_reported.strftime('%Y-%m-%d') if latest_major_case else None
		
		# Get latest case overall (any type) for attachment info - order by created_at to get truly latest
		latest_case_overall = Case.query.filter_by(person_id=person.id).order_by(Case.created_at.desc()).first()
		has_attachment = latest_case_overall.attachment_filename is not None if latest_case_overall else False
		attachment_filename = latest_case_overall.attachment_filename if latest_case_overall and latest_case_overall.attachment_filename else None
		attachment_case_id = latest_case_overall.id if latest_case_overall and latest_case_overall.attachment_filename else None
		
		result.append({
			'id': person.id,
			'full_name': person.full_name,
			'role': person.role,
			'program_or_dept': person.program_or_dept or '',
			'section': person.section or '',
			'minor_count': minor_count,
			'major_count': major_count,
			'total_count': minor_count + major_count,
			'latest_date': latest_date,
			'has_attachment': has_attachment,
			'attachment_filename': attachment_filename,
			'attachment_case_id': attachment_case_id
		})
	
	return jsonify(result)


@bp.get('/api/person/<int:person_id>/cases')
@login_required
def get_person_cases_api(person_id):
	"""API endpoint to get all cases for a specific person"""
	person = Person.query.get_or_404(person_id)
	case_type_filter = request.args.get('case_type', '').strip()
	
	# Get cases with optional case type filter
	if case_type_filter:
		cases = Case.query.filter_by(person_id=person_id, case_type=case_type_filter).order_by(Case.date_reported.desc()).all()
	else:
		cases = Case.get_cases_by_person(person_id)
	
	# Convert to JSON-serializable format
	result = {
		'person': {
			'id': person.id,
			'full_name': person.full_name,
			'role': person.role,
			'program_or_dept': person.program_or_dept or '',
			'section': person.section or ''
		},
		'cases': []
	}
	
	for case in cases:
		case_data = {
			'id': case.id,
			'case_type': case.case_type,
			'description': case.description or '',
			'date_reported': case.date_reported.strftime('%Y-%m-%d'),
			'status': case.status,
			'remarks': case.remarks or '',
			'created_at': case.created_at.strftime('%Y-%m-%d %H:%M'),
			'offense_category': case.offense_category or '',
			'offense_type': case.offense_type or ''
		}
		
		# Add attachment info for major cases only
		if case.case_type == 'major':
			case_data['attachment_filename'] = case.attachment_filename
			case_data['attachment_size'] = case.attachment_size
			case_data['attachment_type'] = case.attachment_type
			case_data['has_attachment'] = bool(case.attachment_filename)
		else:
			case_data['attachment_filename'] = None
			case_data['attachment_size'] = None
			case_data['attachment_type'] = None
			case_data['has_attachment'] = False
		
		result['cases'].append(case_data)
	
	return jsonify(result)


@bp.post('/api/person/add')
@login_required
def add_person_api():
	"""API endpoint to add a new person"""
	try:
		data = request.get_json()
		
		# Validate required fields
		full_name = data.get('full_name', '').strip()
		role = data.get('role', '').strip()
		program_or_dept = data.get('program_or_dept', '').strip()
		section = data.get('section', '').strip()
		
		if not all([full_name, role]):
			return jsonify({'error': 'Full name and role are required'}), 400
		
		if role not in ['student', 'faculty', 'staff']:
			return jsonify({'error': 'Invalid role'}), 400
		
		# Check if person already exists
		existing_person = Person.query.filter_by(
			full_name=full_name,
			role=role,
			program_or_dept=program_or_dept,
			section=section
		).first()
		
		if existing_person:
			return jsonify({'error': 'Person already exists'}), 400
		
		person = Person(
			full_name=full_name,
			role=role,
			program_or_dept=program_or_dept if program_or_dept else None,
			section=section if section else None
		)
		db.session.add(person)
		db.session.commit()
		
		# Log activity
		user = get_current_user()
		if user:
			ActivityLog.log_activity(
				user_id=user.id,
				action="Person Added",
				description=f"Added new person: {person.full_name} ({person.role})"
			)
		
		return jsonify({
			'success': True,
			'person': {
				'id': person.id,
				'full_name': person.full_name,
				'role': person.role,
				'program_or_dept': person.program_or_dept or '',
				'section': person.section or ''
			}
		})
		
	except Exception as e:
		db.session.rollback()
		return jsonify({'error': 'Error adding person'}), 500


@bp.post('/api/person/<int:person_id>/case/add')
@login_required
def add_case_api(person_id):
	"""API endpoint to add a new case for a person"""
	try:
		person = Person.query.get_or_404(person_id)
		data = request.get_json()
		
		# Validate required fields
		case_type = data.get('case_type', '').strip()
		description = data.get('description', '').strip()
		date_reported = data.get('date_reported', '').strip()
		status = data.get('status', 'open').strip()
		remarks = data.get('remarks', '').strip()
		
		if not all([case_type, date_reported]):
			return jsonify({'error': 'Case type and date are required'}), 400
		
		if case_type not in ['minor', 'major']:
			return jsonify({'error': 'Invalid case type'}), 400
		
		case = Case(
			person_id=person_id,
			case_type=case_type,
			description=description if description else None,
			date_reported=datetime.strptime(date_reported, '%Y-%m-%d').date(),
			status=status,
			remarks=remarks if remarks else None
		)
		db.session.add(case)
		db.session.commit()
		
		# Log activity
		user = get_current_user()
		if user:
			ActivityLog.log_activity(
				user_id=user.id,
				action=f"{case_type.title()} Case Added",
				description=f"Added {case_type} case for {person.full_name}"
			)
		
		return jsonify({
			'success': True,
			'case': {
				'id': case.id,
				'case_type': case.case_type,
				'description': case.description or '',
				'date_reported': case.date_reported.strftime('%Y-%m-%d'),
				'status': case.status,
				'remarks': case.remarks or '',
				'created_at': case.created_at.strftime('%Y-%m-%d %H:%M')
			}
		})
		
	except Exception as e:
		db.session.rollback()
		return jsonify({'error': 'Error adding case'}), 500


@bp.post('/api/case/<int:case_id>/edit')
@login_required
@case_read_create_only
def edit_case_api(case_id):
	"""API endpoint to edit an existing case"""
	try:
		case = Case.query.get_or_404(case_id)
		data = request.get_json()
		
		# Update fields
		if 'case_type' in data:
			case.case_type = data['case_type']
		if 'description' in data:
			case.description = data['description'] if data['description'].strip() else None
		if 'date_reported' in data:
			case.date_reported = datetime.strptime(data['date_reported'], '%Y-%m-%d').date()
		if 'status' in data:
			case.status = data['status']
		if 'remarks' in data:
			case.remarks = data['remarks'] if data['remarks'].strip() else None
		
		case.updated_at = datetime.utcnow()
		db.session.commit()
		
		# Log activity
		user = get_current_user()
		if user:
			ActivityLog.log_activity(
				user_id=user.id,
				action="Case Updated",
				description=f"Updated {case.case_type} case for {case.person.full_name}"
			)
		
		return jsonify({'success': True})
		
	except Exception as e:
		db.session.rollback()
		return jsonify({'error': 'Error updating case'}), 500


@bp.post('/api/case/<int:case_id>/delete')
@login_required
@case_read_create_only
def delete_case_api(case_id):
	"""API endpoint to delete a case"""
	try:
		case = Case.query.get_or_404(case_id)
		person_name = case.person.full_name
		case_type = case.case_type
		
		db.session.delete(case)
		db.session.commit()
		
		# Log activity
		user = get_current_user()
		if user:
			ActivityLog.log_activity(
				user_id=user.id,
				action="Case Deleted",
				description=f"Deleted {case_type} case for {person_name}"
			)
		
		return jsonify({'success': True})
		
	except Exception as e:
		db.session.rollback()
		return jsonify({'error': 'Error deleting case'}), 500


@bp.get('/api/person/<int:person_id>')
@login_required
def get_person_api(person_id):
	"""API endpoint to get a specific person's data"""
	try:
		person = Person.query.get_or_404(person_id)
		
		return jsonify({
			'id': person.id,
			'first_name': person.get_first_name(),
			'last_name': person.get_last_name(),
			'full_name': person.full_name,
			'role': person.role,
			'program_or_dept': person.program_or_dept or '',
			'section': person.section or ''
		})
		
	except Exception as e:
		return jsonify({'error': 'Error loading person data'}), 500


@bp.get('/api/case/<int:case_id>')
@login_required
def get_case_api(case_id):
	"""API endpoint to get a specific case's data"""
	try:
		case = Case.query.get_or_404(case_id)
		
		response_data = {
			'id': case.id,
			'case_type': case.case_type,
			'description': case.description or '',
			'date_reported': case.date_reported.strftime('%Y-%m-%d'),
			'status': case.status,
			'remarks': case.remarks or '',
			'created_at': case.created_at.strftime('%Y-%m-%d %H:%M')
		}
		
		return jsonify(response_data)
		
	except Exception as e:
		return jsonify({'error': 'Error loading case data'}), 500


@bp.post('/api/update-person')
@login_required
def update_person_api():
	"""API endpoint to update person information"""
	try:
		data = request.form
		# print(f"DEBUG: Received form data: {dict(data)}")
		
		person_id = data.get('person_id')
		# print(f"DEBUG: Person ID: {person_id}")
		
		if not person_id:
			return jsonify({'error': 'Person ID is required'}), 400
		
		person = Person.query.get_or_404(person_id)
		# print(f"DEBUG: Found person: {person.full_name}")
		
		# Get form data
		first_name = data.get('first_name', '').strip()
		last_name = data.get('last_name', '').strip()
		program_or_dept = data.get('program_or_dept', '').strip()
		section = data.get('section', '').strip()
		
		# print(f"DEBUG: New data - First: {first_name}, Last: {last_name}, Program: {program_or_dept}, Section: {section}")
		
		# Validate required fields based on role
		if person.role == 'student':
			# Students require all fields including section
			if not all([first_name, last_name, program_or_dept, section]):
				return jsonify({'error': 'All fields are required'}), 400
		else:
			# Faculty and staff don't require section
			if not all([first_name, last_name, program_or_dept]):
				return jsonify({'error': 'First name, last name, and program/department are required'}), 400
		
		# Update fields using the set_names method
		person.set_names(first_name, last_name)
		person.program_or_dept = program_or_dept
		person.section = section
		
		# print(f"DEBUG: Before commit - Person: {person.full_name}, Program: {person.program_or_dept}, Section: {person.section}")
		
		# Force flush to see if changes are being made
		db.session.flush()
		
		# Check if changes are in session
		# print(f"DEBUG: After flush - Person: {person.full_name}, Program: {person.program_or_dept}, Section: {person.section}")
		
		db.session.commit()
		
		# print(f"DEBUG: After commit - Person: {person.full_name}, Program: {person.program_or_dept}, Section: {person.section}")
		
		# Verify the changes persisted by re-querying
		db.session.refresh(person)
		# print(f"DEBUG: After refresh - Person: {person.full_name}, Program: {person.program_or_dept}, Section: {person.section}")
		
		# Log activity
		user = get_current_user()
		if user:
			ActivityLog.log_activity(
				user_id=user.id,
				action="Person Updated",
				description=f"Updated information for {person.full_name}"
			)
		
		return jsonify({'success': True})
		
	except Exception as e:
		db.session.rollback()
		return jsonify({'error': 'Error updating person'}), 500


@bp.post('/api/update-case')
@login_required
@case_read_create_only
def update_case_api():
	"""API endpoint to update case information"""
	try:
		data = request.form
		case_id = data.get('case_id')
		
		
		if not case_id:
			return jsonify({'error': 'Case ID is required'}), 400
		
		case = Case.query.get_or_404(case_id)
		
		# Update fields
		if 'date' in data:
			case.date_reported = datetime.strptime(data['date'], '%Y-%m-%d').date()
		if 'description' in data:
			case.description = data['description'].strip() if data['description'].strip() else None
		if 'remarks' in data:
			case.remarks = data['remarks'].strip() if data['remarks'].strip() else None
		
		case.updated_at = datetime.utcnow()
		db.session.commit()
		
		
		
		# Log activity
		user = get_current_user()
		if user:
			ActivityLog.log_activity(
				user_id=user.id,
				action="Case Updated",
				description=f"Updated {case.case_type} case for {case.person.full_name}"
			)
		
		return jsonify({'success': True})
		
	except Exception as e:
		db.session.rollback()
		return jsonify({'error': 'Error updating case'}), 500


@bp.post('/api/delete-person')
@login_required
@case_read_create_only
def delete_person_api():
	"""API endpoint to delete a person and all their cases"""
	try:
		data = request.form
		person_id = data.get('person_id')
		
		if not person_id:
			return jsonify({'error': 'Person ID is required'}), 400
		
		person = Person.query.get_or_404(person_id)
		person_name = person.full_name
		
		# Delete all cases first
		cases = Case.query.filter_by(person_id=person_id).all()
		for case in cases:
			db.session.delete(case)
		
		# Delete the person
		db.session.delete(person)
		db.session.commit()
		
		# Log activity
		user = get_current_user()
		if user:
			ActivityLog.log_activity(
				user_id=user.id,
				action="Person Deleted",
				description=f"Deleted {person_name} and all associated cases"
			)
		
		return jsonify({'success': True})
		
	except Exception as e:
		db.session.rollback()
		return jsonify({'error': 'Error deleting person'}), 500


@bp.post('/ocr/extract')
@login_required
def extract_ocr_data():
	"""Extract structured data from OCR text"""
	try:
		data = request.get_json()
		ocr_text = data.get('text', '').strip()
		entity_type = data.get('entity_type', 'student').strip().lower()
		
		if not ocr_text:
			return jsonify({'error': 'No text provided'}), 400
		
		# Validate entity type
		if entity_type not in ['student', 'faculty', 'staff']:
			entity_type = 'student'
		
		# Extract information using OCR service
		extracted_data = OCRService.extract_all_info(ocr_text, entity_type)
		
		# Validate extraction
		is_valid, validation_errors = OCRService.validate_extraction(extracted_data)
		
		# Log activity
		user = get_current_user()
		if user:
			ActivityLog.log_activity(
				user_id=user.id,
				action="OCR Extraction",
				description=f"Extracted {entity_type} data from OCR text (confidence: {extracted_data.get('extraction_confidence', 0)})"
			)
		
		return jsonify({
			'success': True,
			'data': extracted_data,
			'validation': {
				'is_valid': is_valid,
				'errors': validation_errors
			}
		})
		
	except Exception as e:
		print(f"OCR extraction error: {str(e)}")
		return jsonify({'error': 'Failed to extract data from OCR text'}), 500
