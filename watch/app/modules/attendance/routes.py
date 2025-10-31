from flask import jsonify, render_template, request, send_file, redirect, url_for, flash, session
from datetime import datetime, date, time, timedelta
from ...auth_utils import login_required
from ...models import Schedule, AuditLog, AttendanceChecklist, AttendanceHistory, User
from ...extensions import db, csrf
from ...utils.safe_string import sanitize_string, safe_print, create_error_response
from ...utils.timezone import get_ph_today, get_ph_weekday, get_ph_now
from ...utils.validation import (
    validate_name, validate_subject_course, validate_room,
    sanitize_and_validate_text
)
from . import bp
import os
import tempfile
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


@bp.get('/')
@login_required
def list_checklists():
	"""Attendance Checklist - Check and mark faculty attendance"""
	try:
		# Get today's date and weekday in Philippine timezone (not server timezone)
		today = get_ph_today()  # Uses Philippine timezone (UTC+8)
		today_weekday = get_ph_weekday()  # Get weekday name based on Philippine time
	except Exception as e:
		# Fallback to regular date if timezone conversion fails
		print(f"⚠️ Timezone error, using server date: {e}")
		import traceback
		traceback.print_exc()
		from datetime import date
		today = date.today()
		weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
		today_weekday = weekday_names[today.weekday()]
	
	try:
		# Debug: Print weekday being searched
		print(f"🔍 Looking for schedules on: '{today_weekday}'")
		
		# Get all schedules first for debugging
		all_schedules = Schedule.query.all()
		print(f"📋 Total schedules in database: {len(all_schedules)}")
		
		# Fetch all schedules for today's weekday, sorted by start_time
		# Try exact match first (most common case)
		schedules_query = Schedule.query.filter(
			Schedule.day_of_week == today_weekday
		).order_by(Schedule.start_time.asc()).all()
		
		# If no results, try case-insensitive match (for edge cases)
		if not schedules_query and all_schedules:
			# Filter in Python (more reliable than SQL functions)
			today_weekday_lower = today_weekday.lower().strip()
			schedules_query = [
				sched for sched in all_schedules
				if sched.day_of_week and sched.day_of_week.lower().strip() == today_weekday_lower
			]
			# Sort by start_time
			schedules_query.sort(key=lambda x: x.start_time)
		
		print(f"✅ Found {len(schedules_query)} schedule(s) for {today_weekday}")
		
		# Debug: Show what schedules exist for each day
		weekday_counts = {}
		for sched in all_schedules:
			day = sched.day_of_week or 'Unknown'
			weekday_counts[day] = weekday_counts.get(day, 0) + 1
		print(f"📊 Schedules by day: {weekday_counts}")
		
		# Get today's attendance records
		todays_attendance = {record.professor_name: record.status for record in AttendanceChecklist.get_todays_attendance()}
	except Exception as e:
		print(f"❌ Error fetching schedules/attendance: {e}")
		import traceback
		traceback.print_exc()
		schedules_query = []
		todays_attendance = {}
	
	# Convert schedules to the format expected by the template
	schedules = []
	for schedule in schedules_query:
		# Get attendance status for this professor today
		attendance_status = todays_attendance.get(schedule.professor_name, 'Not Marked')
		
		# Format time slot (e.g., "08:00 - 09:00")
		start_time_str = schedule.start_time.strftime('%H:%M')
		end_time_str = schedule.end_time.strftime('%H:%M')
		time_slot = f"{start_time_str} - {end_time_str}"
		
		# Create schedule data in the expected format
		schedule_data = {
			'id': schedule.id,
			'professor_name': schedule.professor_name,  # Use professor name directly
			'faculty_name': schedule.professor_name,
			'subject': schedule.subject,
			'time_slot': time_slot,
			'room': schedule.room or 'TBA',
			'status': attendance_status
		}
		schedules.append(schedule_data)
	
	return render_template("attendance/checklist.html", schedules=schedules, date=today, today_weekday=today_weekday)


@bp.get('/schedule-management')
@login_required
def schedule_management():
	"""Schedule Management - Create, edit, and delete faculty schedules"""
	# Get schedules from database grouped by professor
	professors_list = Schedule.get_schedules_by_professor()
	
	return render_template("attendance/schedule_management.html", professors=professors_list, date=get_ph_today())


@bp.post('/schedule-management/add')
@login_required
def add_schedule():
	"""Add a new schedule"""
	safe_print("Add schedule route called")
	safe_print(f"Form data received: {dict(request.form)}")
	
	try:
		# Get and validate form data with whitespace prevention
		professor_name_valid, professor_error, professor_name = sanitize_and_validate_text(
			request.form.get('professor_name', ''), validate_name, "Professor Name"
		)
		if not professor_name_valid:
			flash(professor_error, 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		subject_valid, subject_error, subject = sanitize_and_validate_text(
			request.form.get('subject', ''), validate_subject_course, "Subject"
		)
		if not subject_valid:
			flash(subject_error, 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		day_of_week = sanitize_string(request.form.get('day_of_week', ''))
		start_time_str = sanitize_string(request.form.get('start_time', ''))
		end_time_str = sanitize_string(request.form.get('end_time', ''))
		
		room_valid, room_error, room = sanitize_and_validate_text(
			request.form.get('room', ''), validate_room, "Room"
		)
		if not room_valid:
			flash(room_error, 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		safe_print(f"DEBUG Parsed data:")
		safe_print(f"  professor_name: '{professor_name}'")
		safe_print(f"  subject: '{subject}'")
		safe_print(f"  day_of_week: '{day_of_week}'")
		safe_print(f"  start_time: '{start_time_str}'")
		safe_print(f"  end_time: '{end_time_str}'")
		safe_print(f"  room: '{room}'")
		
		# Validation
		if not all([professor_name, subject, day_of_week, start_time_str, end_time_str]):
			flash('All required fields must be filled.', 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		# Parse times
		try:
			start_time = datetime.strptime(start_time_str, '%H:%M').time()
			end_time = datetime.strptime(end_time_str, '%H:%M').time()
		except ValueError:
			flash('Invalid time format. Use HH:MM format.', 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		# Validate start time < end time
		if start_time >= end_time:
			flash('Start time must be before end time.', 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		# Validate time range (7 AM to 8 PM)
		min_time = datetime.strptime('07:00', '%H:%M').time()
		max_time = datetime.strptime('20:00', '%H:%M').time()
		
		if start_time < min_time or end_time > max_time:
			flash('Schedule times must be between 7:00 AM and 8:00 PM only.', 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		# Check for time overlap
		has_overlap, conflicting_schedule = Schedule.check_time_overlap(
			professor_name, day_of_week, start_time, end_time
		)
		
		if has_overlap:
			flash(f'Time conflict detected! {professor_name} already has a schedule on {day_of_week} from {conflicting_schedule.start_time} to {conflicting_schedule.end_time}.', 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		# Create new schedule
		new_schedule = Schedule(
			professor_name=professor_name,
			subject=subject,
			day_of_week=day_of_week,
			start_time=start_time,
			end_time=end_time,
			room=room if room else None
		)
		
		db.session.add(new_schedule)
		db.session.commit()
		
		# Log activity
		AuditLog.log_activity(
			action_type='Created',
			description=f'Added schedule for {professor_name}: {subject} on {day_of_week} {start_time}-{end_time}'
		)
		
		flash(f'Schedule added successfully for {professor_name}!', 'success')
		
	except Exception as e:
		db.session.rollback()
		error_msg = f'Error adding schedule: {str(e)}'
		safe_print(error_msg)
		flash(error_msg, 'error')
	
	return redirect(url_for('attendance.schedule_management'))


@bp.get('/schedule-management/edit/<int:id>')
@login_required
def edit_schedule_form(id):
	"""Show edit schedule form"""
	schedule = Schedule.query.get_or_404(id)
	professors_list = Schedule.get_schedules_by_professor()
	return render_template("attendance/schedule_management.html", 
						 professors=professors_list, 
						 edit_schedule=schedule, 
						 date=get_ph_today())


@bp.post('/schedule-management/edit/<int:id>')
@login_required
def update_schedule(id):
	"""Update an existing schedule"""
	safe_print(f"Update schedule route called for ID: {id}")
	safe_print(f"Form data received: {dict(request.form)}")
	
	try:
		schedule = Schedule.query.get_or_404(id)
		safe_print(f"Found schedule: {schedule}")
		
		# Get and validate form data with whitespace prevention
		professor_name_valid, professor_error, professor_name = sanitize_and_validate_text(
			request.form.get('professor_name', ''), validate_name, "Professor Name"
		)
		if not professor_name_valid:
			flash(professor_error, 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		subject_valid, subject_error, subject = sanitize_and_validate_text(
			request.form.get('subject', ''), validate_subject_course, "Subject"
		)
		if not subject_valid:
			flash(subject_error, 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		day_of_week = sanitize_string(request.form.get('day_of_week', ''))
		start_time_str = sanitize_string(request.form.get('start_time', ''))
		end_time_str = sanitize_string(request.form.get('end_time', ''))
		
		room_valid, room_error, room = sanitize_and_validate_text(
			request.form.get('room', ''), validate_room, "Room"
		)
		if not room_valid:
			flash(room_error, 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		safe_print(f"DEBUG Parsed data:")
		safe_print(f"  professor_name: '{professor_name}'")
		safe_print(f"  subject: '{subject}'")
		safe_print(f"  day_of_week: '{day_of_week}'")
		safe_print(f"  start_time: '{start_time_str}'")
		safe_print(f"  end_time: '{end_time_str}'")
		safe_print(f"  room: '{room}'")
		
		# Validation - be more lenient with professor_name in edit mode
		required_fields = [subject, day_of_week, start_time_str, end_time_str]
		
		# If professor_name is empty but schedule has one, use the existing one
		if not professor_name:
			professor_name = schedule.professor_name
		safe_print(f"INFO Using existing professor name: {professor_name}")
		
		if not all(required_fields):
			flash('All required fields must be filled.', 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		# Parse times
		try:
			start_time = datetime.strptime(start_time_str, '%H:%M').time()
			end_time = datetime.strptime(end_time_str, '%H:%M').time()
		except ValueError:
			flash('Invalid time format. Use HH:MM format.', 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		# Validate start time < end time
		if start_time >= end_time:
			flash('Start time must be before end time.', 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		# Validate time range (7 AM to 8 PM)
		min_time = datetime.strptime('07:00', '%H:%M').time()
		max_time = datetime.strptime('20:00', '%H:%M').time()
		
		if start_time < min_time or end_time > max_time:
			flash('Schedule times must be between 7:00 AM and 8:00 PM only.', 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		# Check for time overlap (excluding current schedule)
		has_overlap, conflicting_schedule = Schedule.check_time_overlap(
			professor_name, day_of_week, start_time, end_time, exclude_id=id
		)
		
		if has_overlap:
			flash(f'Time conflict detected! {professor_name} already has a schedule on {day_of_week} from {conflicting_schedule.start_time} to {conflicting_schedule.end_time}.', 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		# Update schedule
		old_description = f'{schedule.professor_name}: {schedule.subject} on {schedule.day_of_week} {schedule.start_time}-{schedule.end_time}'
		
		schedule.professor_name = professor_name
		schedule.subject = subject
		schedule.day_of_week = day_of_week
		schedule.start_time = start_time
		schedule.end_time = end_time
		schedule.room = room if room else None
		
		db.session.commit()
		safe_print("Schedule updated successfully in database")
		
		# Log activity
		new_description = f'{professor_name}: {subject} on {day_of_week} {start_time}-{end_time}'
		AuditLog.log_activity(
			action_type='Updated',
			description=f'Updated schedule from {old_description} to {new_description}'
		)
		safe_print("Activity logged")
		
		flash(f'Schedule updated successfully!', 'success')
		safe_print("Flash message set")
		
	except Exception as e:
		error_msg = f'Error updating schedule: {str(e)}'
		safe_print(error_msg)
		db.session.rollback()
		flash(error_msg, 'error')
	
	return redirect(url_for('attendance.schedule_management'))


@bp.post('/schedule-management/delete/<int:id>')
@login_required
def delete_schedule(id):
	"""Delete a schedule"""
	try:
		schedule = Schedule.query.get_or_404(id)
		
		# Log activity before deletion
		description = f'{schedule.professor_name}: {schedule.subject} on {schedule.day_of_week} {schedule.start_time}-{schedule.end_time}'
		AuditLog.log_activity(
			action_type='Deleted',
			description=f'Deleted schedule for {description}'
		)
		
		# Delete schedule
		db.session.delete(schedule)
		db.session.commit()
		
		flash(f'Schedule deleted successfully!', 'success')
		
	except Exception as e:
		db.session.rollback()
		error_msg = f'Error deleting schedule: {str(e)}'
		safe_print(error_msg)
		flash(error_msg, 'error')
	
	return redirect(url_for('attendance.schedule_management'))


@bp.post('/schedule-management/update-professor-name')
@login_required
def update_professor_name():
	"""Update professor name for all schedules"""
	try:
		old_name = sanitize_string(request.form.get('old_name', ''))
		new_name = sanitize_string(request.form.get('new_name', ''))
		
		# Validation
		if not old_name or not new_name:
			flash('Both old and new professor names are required.', 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		if old_name == new_name:
			flash('The new name is the same as the old name.', 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		# Find all schedules for this professor
		schedules = Schedule.query.filter_by(professor_name=old_name).all()
		
		if not schedules:
			flash(f'No schedules found for professor "{old_name}".', 'error')
			return redirect(url_for('attendance.schedule_management'))
		
		# Update all schedules
		updated_count = 0
		for schedule in schedules:
			schedule.professor_name = new_name
			updated_count += 1
		
		db.session.commit()
		
		# Log activity
		AuditLog.log_activity(
			action_type='Updated',
			description=f'Updated professor name from "{old_name}" to "{new_name}" for {updated_count} schedules'
		)
		
		flash(f'Successfully updated professor name from "{old_name}" to "{new_name}" for {updated_count} schedule(s)!', 'success')
		
	except Exception as e:
		db.session.rollback()
		error_msg = f'Error updating professor name: {str(e)}'
		safe_print(error_msg)
		flash(error_msg, 'error')
	
	return redirect(url_for('attendance.schedule_management'))


@bp.get('/history')
@login_required
def attendance_history():
	"""Attendance History - View historical attendance records with filters"""
	# Get filter parameters
	selected_date = request.args.get('date', '')
	selected_month = request.args.get('month', '')
	
	# Default to today's date if no filter is provided (Philippine timezone)
	if not selected_date and not selected_month:
		selected_date = get_ph_today().strftime('%Y-%m-%d')
	
	# Get attendance history from database
	if selected_date:
		# Filter by specific date
		try:
			filter_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
			attendance_records = AttendanceHistory.get_attendance_by_date(filter_date)
		except ValueError:
			attendance_records = []
	elif selected_month:
		# Filter by month
		try:
			year, month = selected_month.split('-')
			start_date = date(int(year), int(month), 1)
			# Get last day of month
			if int(month) == 12:
				end_date = date(int(year) + 1, 1, 1) - timedelta(days=1)
			else:
				end_date = date(int(year), int(month) + 1, 1) - timedelta(days=1)
			attendance_records = AttendanceHistory.get_attendance_range(start_date, end_date)
		except (ValueError, IndexError):
			attendance_records = []
	else:
		# Default to today (Philippine timezone)
		attendance_records = AttendanceHistory.get_attendance_by_date(get_ph_today())
	
	# Convert to template format
	history = []
	for record in attendance_records:
		# Get schedule details for context (if available)
		# We'll try to find a schedule that matches this professor on this date
		schedule_info = None
		
		# Get weekday name for this date
		weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
		weekday = weekday_names[record.date.weekday()]
		
		# Find a schedule for this professor on this weekday
		schedule = Schedule.query.filter(
			Schedule.professor_name == record.professor_name,
			Schedule.day_of_week == weekday
		).first()
		
		if schedule:
			start_time_str = schedule.start_time.strftime('%H:%M')
			end_time_str = schedule.end_time.strftime('%H:%M')
			schedule_info = {
				'subject': schedule.subject,
				'time_slot': f"{start_time_str} - {end_time_str}",
				'room': schedule.room or 'TBA'
			}
		
		history_record = {
			'id': record.id,  # Add the missing ID field!
			'date': record.date.strftime('%Y-%m-%d'),
			'faculty_name': record.professor_name,
			'subject': schedule_info['subject'] if schedule_info else 'N/A',
			'time_slot': schedule_info['time_slot'] if schedule_info else 'N/A',
			'status': record.status,
			'room': schedule_info['room'] if schedule_info else 'N/A',
			'created_at': record.created_at.strftime('%Y-%m-%d %H:%M:%S')
		}
		history.append(history_record)
	
	# Sort by date and time (newest first)
	history.sort(key=lambda x: (x['date'], x['created_at']), reverse=True)
	
	return render_template("attendance/history.html", 
						 history=history, 
						 selected_date=selected_date,
						 selected_month=selected_month,
						 date=date)


@bp.post('/generate-report')
@login_required
def generate_report():
	"""Generate attendance report for selected date/month"""
	try:
		# Get form data
		report_type = request.form.get('report_type', 'all')
		date_value = request.form.get('date_value', '')
		faculty_filter = request.form.get('faculty', '')
		status_filter = request.form.get('status', '')
		
		# Determine date range
		start_date = None
		end_date = None
		report_title = "Attendance Report"
		
		if report_type == 'date' and date_value:
			start_date = datetime.strptime(date_value, '%Y-%m-%d').date()
			end_date = start_date
			report_title = f"Daily Attendance Report - {start_date.strftime('%B %d, %Y')}"
		elif report_type == 'month' and date_value:
			# Parse month (YYYY-MM format)
			year, month = map(int, date_value.split('-'))
			start_date = date(year, month, 1)
			# Get last day of month
			if month == 12:
				end_date = date(year + 1, 1, 1) - timedelta(days=1)
			else:
				end_date = date(year, month + 1, 1) - timedelta(days=1)
			report_title = f"Monthly Attendance Report - {start_date.strftime('%B %Y')}"
		else:
			# All time report (use Philippine timezone)
			today_ph = get_ph_today()
			start_date = today_ph - timedelta(days=30)  # Last 30 days
			end_date = today_ph
			report_title = f"Attendance Report - Last 30 Days"
		
		# Query attendance records
		query = AttendanceHistory.query
		
		if start_date and end_date:
			query = query.filter(
				AttendanceHistory.date >= start_date,
				AttendanceHistory.date <= end_date
			)
		
		if faculty_filter:
			query = query.filter(AttendanceHistory.professor_name == faculty_filter)
		
		if status_filter:
			query = query.filter(AttendanceHistory.status == status_filter)
		
		attendance_records = query.order_by(AttendanceHistory.date.desc()).all()
		
		# Generate PDF report (use Philippine timezone)
		pdf_filename = f"attendance_report_{get_ph_now().strftime('%Y%m%d_%H%M%S')}.pdf"
		temp_dir = tempfile.gettempdir()
		pdf_path = os.path.join(temp_dir, pdf_filename)
		
		# Create PDF document
		doc = SimpleDocTemplate(pdf_path, pagesize=A4)
		story = []
		
		# Define styles
		styles = getSampleStyleSheet()
		title_style = ParagraphStyle(
			'CustomTitle',
			parent=styles['Heading1'],
			fontSize=18,
			spaceAfter=30,
			alignment=TA_CENTER,
			textColor=colors.darkblue
		)
		
		subtitle_style = ParagraphStyle(
			'CustomSubtitle',
			parent=styles['Normal'],
			fontSize=12,
			spaceAfter=20,
			alignment=TA_CENTER,
			textColor=colors.grey
		)
		
		# Add title
		story.append(Paragraph("WATCH", title_style))
		story.append(Paragraph("Web-based Attendance Tracking and Case Handling System", subtitle_style))
		story.append(Paragraph(report_title, subtitle_style))
		story.append(Spacer(1, 20))
		
		# Add report summary
		summary_data = [
			['Report Period:', f"{start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}"],
			['Total Records:', str(len(attendance_records))],
			['Faculty Filter:', faculty_filter if faculty_filter else 'All Faculty'],
			['Status Filter:', status_filter if status_filter else 'All Status'],
			['Generated On:', get_ph_now().strftime('%B %d, %Y at %I:%M %p')]
		]
		
		summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
		summary_table.setStyle(TableStyle([
			('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
			('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
			('ALIGN', (0, 0), (-1, -1), 'LEFT'),
			('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
			('FONTSIZE', (0, 0), (-1, -1), 10),
			('BOTTOMPADDING', (0, 0), (-1, -1), 12),
			('GRID', (0, 0), (-1, -1), 1, colors.black)
		]))
		
		story.append(summary_table)
		story.append(Spacer(1, 30))
		
		# Add attendance records table
		if attendance_records:
			# Table headers
			table_data = [['Date', 'Faculty Name', 'Status', 'Time Recorded']]
			
			# Add attendance records
			for record in attendance_records:
				table_data.append([
					record.date.strftime('%Y-%m-%d'),
					record.professor_name,
					record.status,
					record.created_at.strftime('%I:%M %p')
				])
			
			# Create table
			attendance_table = Table(table_data, colWidths=[1.5*inch, 2.5*inch, 1*inch, 1.5*inch])
			attendance_table.setStyle(TableStyle([
				('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
				('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
				('ALIGN', (0, 0), (-1, -1), 'CENTER'),
				('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
				('FONTSIZE', (0, 0), (-1, 0), 12),
				('BOTTOMPADDING', (0, 0), (-1, 0), 12),
				('BACKGROUND', (0, 1), (-1, -1), colors.beige),
				('GRID', (0, 0), (-1, -1), 1, colors.black),
				('FONTSIZE', (0, 1), (-1, -1), 9),
				('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
			]))
			
			story.append(attendance_table)
			
			# Add statistics
			story.append(Spacer(1, 30))
			
			# Calculate statistics
			status_counts = {}
			for record in attendance_records:
				status_counts[record.status] = status_counts.get(record.status, 0) + 1
			
			stats_data = [['Status', 'Count', 'Percentage']]
			total_records = len(attendance_records)
			
			for status, count in status_counts.items():
				percentage = (count / total_records) * 100 if total_records > 0 else 0
				stats_data.append([status, str(count), f"{percentage:.1f}%"])
			
			stats_table = Table(stats_data, colWidths=[2*inch, 1*inch, 1.5*inch])
			stats_table.setStyle(TableStyle([
				('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
				('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
				('ALIGN', (0, 0), (-1, -1), 'CENTER'),
				('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
				('FONTSIZE', (0, 0), (-1, 0), 12),
				('BOTTOMPADDING', (0, 0), (-1, 0), 12),
				('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
				('GRID', (0, 0), (-1, -1), 1, colors.black),
				('FONTSIZE', (0, 1), (-1, -1), 10)
			]))
			
			story.append(Paragraph("Attendance Statistics", styles['Heading2']))
			story.append(stats_table)
		else:
			story.append(Paragraph("No attendance records found for the selected criteria.", styles['Normal']))
		
		# Build PDF
		doc.build(story)
		
		# Store the file path in session for download
		session['generated_report_path'] = pdf_path
		session['generated_report_filename'] = pdf_filename
		
		return jsonify({
			'success': True,
			'message': f'Report generated successfully! {len(attendance_records)} records processed.',
			'download_url': url_for('attendance.download_report'),
			'record_count': len(attendance_records)
		}), 200
		
	except Exception as e:
		return jsonify({
			'success': False,
			'message': f'Error generating report: {str(e)}'
		}), 500


@bp.get('/download-report')
@login_required
def download_report():
	"""Download the generated attendance report"""
	try:
		
		# Get file path from session
		report_path = session.get('generated_report_path')
		report_filename = session.get('generated_report_filename')
		
		if not report_path or not report_filename:
			flash('No report available for download. Please generate a report first.', 'error')
			return redirect(url_for('attendance.attendance_history'))
		
		# Check if file exists
		if not os.path.exists(report_path):
			flash('Report file not found. Please generate a new report.', 'error')
			return redirect(url_for('attendance.attendance_history'))
		
		# Send file for download
		return send_file(
			report_path,
			as_attachment=True,
			download_name=report_filename,
			mimetype='application/pdf'
		)
		
	except Exception as e:
		flash(f'Error downloading report: {str(e)}', 'error')
		return redirect(url_for('attendance.attendance_history'))


@bp.post('/update_attendance')
@login_required
def update_attendance():
	"""Update attendance status for a professor"""
	try:
		# Get form data
		professor_name = request.form.get('professor_name')
		status = request.form.get('status')
		
		# Validation
		if not professor_name or not status:
			return jsonify({'success': False, 'message': 'Missing required fields'}), 400
		
		# Validate status
		valid_statuses = ['Present', 'Absent', 'Late']
		if status not in valid_statuses:
			return jsonify({'success': False, 'message': 'Invalid status'}), 400
		
		# Use Philippine timezone for today's date
		today = get_ph_today()
		
		# Update or insert attendance checklist for today
		existing_checklist = AttendanceChecklist.query.filter_by(
			professor_name=professor_name,
			date=today
		).first()
		
		if existing_checklist:
			# Update existing record
			existing_checklist.status = status
			existing_checklist.created_at = get_ph_now()  # Use Philippine timezone
		else:
			# Create new record
			new_checklist = AttendanceChecklist(
				professor_name=professor_name,
				status=status,
				date=today
			)
			db.session.add(new_checklist)
		
		# Always add to history (for audit trail)
		new_history = AttendanceHistory(
			professor_name=professor_name,
			status=status,
			date=today
		)
		db.session.add(new_history)
		
		# Commit changes
		db.session.commit()
		
		# Log activity
		AuditLog.log_activity(
			action_type='Updated',
			description=f'Updated attendance for {professor_name} to {status} on {today}'
		)
		
		# Send notification to admin if current user is discipline committee
		from ...models import User, Notification
		current_user = User.query.get(session.get('user_id'))
		if current_user and current_user.role and current_user.role.name.lower() == 'user':
			# Discipline committee performed action - notify admin
			Notification.notify_admin_user_action(
				action_performed="Attendance Update",
				details=f"Marked {professor_name} as {status} on {today.strftime('%B %d, %Y')}",
				notification_type="attendance",
				redirect_url=url_for('attendance.list_checklists')
			)
		
		return jsonify({
			'success': True,
			'message': f'Attendance updated to {status} for {professor_name}'
		}), 200
		
	except Exception as e:
		db.session.rollback()
		return jsonify({
			'success': False,
			'message': f'Error updating attendance: {str(e)}'
		}), 500


@bp.post('/update_history_status')
@login_required
def update_history_status():
	"""Update attendance status in history records"""
	try:
		# Get form data
		record_id = request.form.get('record_id')
		new_status = request.form.get('new_status')
		
		safe_print(f"DEBUG: Received record_id: {record_id}, new_status: {new_status}")
		
		# Validation
		if not record_id or not new_status:
			safe_print(f"ERROR: Missing required fields - record_id: {record_id}, new_status: {new_status}")
			return jsonify({'success': False, 'error': 'Missing required fields'}), 400
		
		# Validate status
		valid_statuses = ['Present', 'Absent', 'Late']
		if new_status not in valid_statuses:
			safe_print(f"ERROR: Invalid status: {new_status}")
			return jsonify({'success': False, 'error': 'Invalid status'}), 400
		
		# Convert record_id to integer
		try:
			record_id = int(record_id)
		except ValueError:
			safe_print(f"ERROR: Invalid record_id format: {record_id}")
			return jsonify({'success': False, 'error': 'Invalid record ID format'}), 400
		
		# Find the attendance record
		attendance_record = AttendanceHistory.query.get(record_id)
		safe_print(f"DEBUG: Looking for record ID {record_id}")
		
		if not attendance_record:
			# List all available records for debugging
			all_records = AttendanceHistory.query.all()
			safe_print(f"ERROR: Record {record_id} not found. Available records:")
			for rec in all_records:
				safe_print(f"  Record {rec.id}: {rec.professor_name} - {rec.status}")
			return jsonify({'success': False, 'error': 'Attendance record not found'}), 404
		
		# Update the status
		old_status = attendance_record.status
		attendance_record.status = new_status
		db.session.commit()
		
		# Log the activity
		from ...models import ActivityLog
		ActivityLog.log_activity(
			user_id=session.get('user_id'),
			action="Attendance Status Updated",
			description=f"Changed attendance status from {old_status} to {new_status} for {attendance_record.professor_name}"
		)
		
		# Send notification to admin if current user is discipline committee
		from ...models import User, Notification
		current_user = User.query.get(session.get('user_id'))
		if current_user and current_user.role and current_user.role.name.lower() == 'user':
			# Discipline committee performed action - notify admin
			Notification.notify_admin_user_action(
				action_performed="Attendance History Update",
				details=f"Modified {attendance_record.professor_name}'s attendance from {old_status} to {new_status} on {attendance_record.date.strftime('%B %d, %Y')}",
				notification_type="attendance_history",
				redirect_url=url_for('attendance.attendance_history')
			)
		
		return jsonify({
			'success': True,
			'message': f'Status updated from {old_status} to {new_status}'
		}), 200
		
	except Exception as e:
		db.session.rollback()
		return jsonify({
			'success': False,
			'error': f'Error updating status: {str(e)}'
		}), 500


@bp.get('/api')
@login_required
def list_checklists_api():
	return jsonify([]), 200


@bp.post('/schedule-management/delete-all')
@login_required
def delete_all_schedules():
    """Delete all schedules (end-of-semester reset)."""
    try:
        total = Schedule.query.count()
        if total == 0:
            flash('No schedules to delete.', 'info')
            return redirect(url_for('attendance.schedule_management'))

        # Bulk delete all schedules
        Schedule.query.delete(synchronize_session=False)
        db.session.commit()

        AuditLog.log_activity(
            action_type='Deleted',
            description=f'Deleted all schedules (total {total}). End-of-semester reset.'
        )

        flash(f'Successfully deleted all schedules (total {total}).', 'success')
        return redirect(url_for('attendance.schedule_management'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting all schedules: {str(e)}', 'error')
        return redirect(url_for('attendance.schedule_management'))

