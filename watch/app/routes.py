from flask import Blueprint, render_template, redirect, url_for, session, request, flash, jsonify
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from .models import AuditLog, User, ActivityLog
from .auth_utils import login_required, is_authenticated, get_current_user
from .extensions import db
from .utils.validation import (
    validate_name, validate_email, validate_phone,
    sanitize_and_validate_text
)


core_bp = Blueprint("core", __name__)


## Removed test CSRF routes for production cleanliness


@core_bp.get("/")
def index():
	"""Root route - Always check authentication first"""
	# SECURITY: Always redirect unauthenticated users to login
	if not is_authenticated():
		return redirect(url_for('auth.login'))
	
	# Only authenticated users can access dashboard
	return redirect(url_for('core.dashboard'))




@core_bp.get("/dashboard")
@login_required
def dashboard():
	from datetime import date, datetime
	from sqlalchemy import func, desc
	from .models import AttendanceChecklist, Appointment, Case, Person, MinorCase, MajorCase
	
	# Get recent audit logs (5 most recent)
	audit_logs = AuditLog.get_recent_logs(limit=5)
	
	# Get today's attendance - count absent records
	today = date.today()
	attendance_today = AttendanceChecklist.query.filter(
		AttendanceChecklist.date == today,
		AttendanceChecklist.status == 'Absent'
	).count()
	
	# Get appointments data
	appointments_total = Appointment.query.count()
	appointments_pending = Appointment.query.filter_by(status='Pending').count()
	
	# Get cases data from the new Case model
	active_cases_total = Case.query.count()
	major_cases = Case.query.filter_by(case_type='major').count()
	minor_cases = Case.query.filter_by(case_type='minor').count()
	
	# Get top offenses from offense_type field - specific offense types
	top_offenses_data = db.session.query(
		func.count(Case.id).label('count'),
		Case.offense_type.label('offense_type')
	).filter(
		Case.offense_type.isnot(None),
		Case.offense_type != ''
	).group_by(Case.offense_type).order_by(desc('count')).limit(5).all()
	
	# Process top offenses
	offenses_labels = []
	offenses_counts = []
	
	if top_offenses_data:
		for offense in top_offenses_data:
			# Use the specific offense type for display
			offense_type = offense.offense_type.strip()
			if len(offense_type) > 30:
				offense_type = offense_type[:30] + "..."
			offenses_labels.append(offense_type)
			offenses_counts.append(offense.count)
	else:
		# Fallback to sample data if no real data
		offenses_labels = ['No cases reported', 'No data available']
		offenses_counts = [1, 1]
	
	dashboard_data = {
		'attendance_today': attendance_today,
		'appointments_total': appointments_total,
		'appointments_pending': appointments_pending,
		'active_cases_total': active_cases_total,
		'major_cases': major_cases,
		'minor_cases': minor_cases,
		'offenses_labels': offenses_labels,
		'offenses_counts': offenses_counts,
		'audit_logs': audit_logs
	}
	return render_template("dashboard.html", **dashboard_data)


@core_bp.get("/profile")
@login_required
def profile():
	# Get current user
	user_id = session.get('user_id')
	user = User.query.get_or_404(user_id)
	
	# Get last 10 activity logs for the current user (LIFO order)
	activity_logs = ActivityLog.get_user_logs(user_id, limit=10)
	
	# Get email settings (use get_settings() to ensure it exists)
	from .models import EmailSettings
	email_settings = EmailSettings.get_settings()
	
	return render_template("profile.html", user=user, activity_logs=activity_logs, email_settings=email_settings)


@core_bp.post("/update-profile")
@login_required
def update_profile():
	# Get current user
	user_id = session.get('user_id')
	user = User.query.get_or_404(user_id)
	
	try:
		# Validate and update user fields from form data
		full_name = request.form.get('full_name', '').strip()
		if full_name:
			full_name_valid, full_name_error, full_name = sanitize_and_validate_text(
				full_name, validate_name, "Full Name"
			)
			if not full_name_valid:
				flash(full_name_error, 'error')
				return redirect(url_for('core.profile'))
			user.full_name = full_name
		else:
			user.full_name = None
		
		title = request.form.get('title', '').strip()
		if title:
			title_valid, title_error, title = sanitize_and_validate_text(
				title, validate_name, "Title"
			)
			if not title_valid:
				flash(title_error, 'error')
				return redirect(url_for('core.profile'))
			user.title = title
		else:
			user.title = None
		
		# Handle personal email (user-specific, not system-wide)
		user_email = request.form.get('email', '').strip()
		if user_email:
			user_email_valid, user_email_error, user_email = sanitize_and_validate_text(
				user_email, validate_email, "Email Address"
			)
			if not user_email_valid:
				flash(user_email_error, 'error')
				return redirect(url_for('core.profile'))
			user.email = user_email
		else:
			# Allow clearing email (empty string means no email)
			user.email = None
		
		phone = request.form.get('phone', '').strip()
		if phone:
			phone_valid, phone_error, phone = sanitize_and_validate_text(
				phone, validate_phone, "Phone"
			)
			if not phone_valid:
				flash(phone_error, 'error')
				return redirect(url_for('core.profile'))
			user.phone = phone
		else:
			user.phone = None
		
		user.gender = request.form.get('gender', '').strip() or None
		user.gmail = request.form.get('gmail', '').strip() or None
		user.outlook = request.form.get('outlook', '').strip() or None
		
		# Handle email configuration settings with validation - ADMIN ONLY
		from .models import EmailSettings
		# Only allow admin to update system email settings
		if user.is_admin():
			enabled = request.form.get('enabled') == 'true'
			provider = request.form.get('provider', 'gmail')
			
			sender_email = request.form.get('sender_email', '').strip()
			if sender_email:
				sender_email_valid, sender_email_error, sender_email = sanitize_and_validate_text(
					sender_email, validate_email, "Sender Email"
				)
				if not sender_email_valid:
					flash(sender_email_error, 'error')
					return redirect(url_for('core.profile'))
			
			sender_name = request.form.get('sender_name', '').strip()
			if sender_name:
				sender_name_valid, sender_name_error, sender_name = sanitize_and_validate_text(
					sender_name, validate_name, "Sender Name"
				)
				if not sender_name_valid:
					flash(sender_name_error, 'error')
					return redirect(url_for('core.profile'))
			
			sender_password = request.form.get('sender_password', '').strip()
			
			# Update email settings (admin only)
			EmailSettings.update_settings(
				enabled=enabled,
				provider=provider,
				sender_email=sender_email,
				sender_password=sender_password,
				sender_name=sender_name
			)
		else:
			# Non-admin users cannot update system email settings
			# Log if they try (for security monitoring)
			current_app.logger.warning(
				f"Non-admin user {user.username} (ID: {user.id}) attempted to update system email settings"
			)
		
		# Save changes to database
		db.session.commit()
		
		# Create audit log entry
		AuditLog.log_activity(
			action_type="Updated",
			description="Updated profile information",
			user_id=user.id,
			ip_address=request.remote_addr,
			user_agent=request.headers.get('User-Agent')
		)
		
		flash('Profile updated successfully!', 'success')
		
	except Exception as e:
		db.session.rollback()
		flash('An error occurred while updating your profile. Please try again.', 'error')
	
	return redirect(url_for('core.profile'))


@core_bp.post("/update-profile-ajax")
@login_required
def update_profile_ajax():
	"""AJAX endpoint for updating profile without page reload"""
	user_id = session.get('user_id')
	user = User.query.get_or_404(user_id)
	
	try:
		# Update user fields from form data
		user.full_name = request.form.get('full_name', '').strip() or None
		user.title = request.form.get('title', '').strip() or None
		user.email = request.form.get('email', '').strip() or None
		user.phone = request.form.get('phone', '').strip() or None
		user.gender = request.form.get('gender', '').strip() or None
		
		
		# Save changes to database
		db.session.commit()
		
		# Create activity log entry
		ActivityLog.log_activity(
			user_id=user.id,
			action="Profile Updated",
			description="Updated profile information"
		)
		
		# Return updated user data
		user_data = {
			'full_name': user.full_name,
			'title': user.title,
			'email': user.email,
			'phone': user.phone,
			'username': user.username
		}
		
		return jsonify({'success': True, 'user': user_data})
		
	except Exception as e:
		db.session.rollback()
		return jsonify({'success': False, 'error': 'An error occurred while updating your profile.'})


@core_bp.post("/upload-profile-picture")
@login_required
def upload_profile_picture():
	"""AJAX endpoint for uploading profile pictures"""
	user_id = session.get('user_id')
	user = User.query.get_or_404(user_id)
	
	if 'profile_picture' not in request.files:
		return jsonify({'success': False, 'error': 'No file selected'})
	
	file = request.files['profile_picture']
	if file.filename == '':
		return jsonify({'success': False, 'error': 'No file selected'})
	
	# Check file extension
	allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
	if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
		return jsonify({'success': False, 'error': 'Invalid file type. Please upload PNG, JPG, JPEG, or GIF files only.'})
	
	try:
		# Create uploads directory if it doesn't exist
		upload_dir = os.path.join('watch', 'app', 'static', 'uploads', 'profiles')
		os.makedirs(upload_dir, exist_ok=True)
		
		# Generate secure filename
		filename = secure_filename(file.filename)
		# Add user ID to filename to avoid conflicts
		name, ext = os.path.splitext(filename)
		filename = f"user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
		
		# Save file
		file_path = os.path.join(upload_dir, filename)
		file.save(file_path)
		
		# Delete old profile picture if it exists
		if user.profile_picture:
			old_file_path = os.path.join(upload_dir, user.profile_picture)
			if os.path.exists(old_file_path):
				os.remove(old_file_path)
		
		# Update user profile picture in database
		user.profile_picture = filename
		db.session.commit()
		
		# Create activity log entry
		ActivityLog.log_activity(
			user_id=user.id,
			action="Profile Picture Updated",
			description="Changed profile picture"
		)
		
		# Return success with image URL
		image_url = url_for('static', filename=f'uploads/profiles/{filename}')
		return jsonify({'success': True, 'image_url': image_url})
		
	except Exception as e:
		db.session.rollback()
		return jsonify({'success': False, 'error': 'Failed to upload image. Please try again.'})


