from flask import jsonify, render_template, request, flash, redirect, url_for, Response, session, current_app
from ...auth_utils import login_required, get_current_user
from ...models import Appointment, Notification, User, Role
from ...extensions import db, limiter
from ...services.email_service import EmailService
from ...services.notification_service import NotificationService
from ...utils.uploads import save_upload
from ...extensions import csrf
from datetime import datetime
import json
import time
import traceback
from . import bp


@bp.get('/appointments')
@login_required
def list_appointments():
	return render_template("complaints/appointments.html")


@bp.get('/api/appointments')
@login_required
def list_appointments_api():
	"""Get all appointments for the Discipline Officer"""
	try:
		appointments = Appointment.query.order_by(Appointment.appointment_date.asc()).all()
		
		appointments_data = []
		for apt in appointments:
			appointments_data.append({
				'id': apt.id,
				'full_name': apt.full_name,
				'email': apt.email,
				'appointment_date': apt.appointment_date.strftime('%Y-%m-%d %I:%M %p'),
				'appointment_type': apt.appointment_type,
				'appointment_description': getattr(apt, 'appointment_description', ''),
				'status': apt.status,
				'created_at': apt.created_at.strftime('%Y-%m-%d %I:%M %p')
			})
		
		return jsonify(appointments_data), 200
	except Exception as e:
		return jsonify({'error': str(e)}), 500


@bp.get('/test')
def test_route():
	"""Test route to verify complaints blueprint is working"""
	return jsonify({'message': 'Complaints blueprint is working!', 'status': 'success'}), 200

@bp.post('/test-post')
def test_post_route():
	"""Test POST route to verify POST requests work"""
	# print("DEBUG: Test POST route called!")
	return jsonify({'message': 'POST route is working!', 'status': 'success'}), 200

@bp.post('/appointments')
@csrf.exempt
@limiter.limit('10 per minute')
def create_appointment():
	"""Create a new appointment from QR code scan"""
	try:
		# print(f"DEBUG: Request method: {request.method}")
		# print(f"DEBUG: Request content type: {request.content_type}")
		# print(f"DEBUG: Request data: {request.get_data()}")
		
		data = request.get_json()
		# print(f"DEBUG: Received appointment data: {data}")
		
		if not data:
			return jsonify({'error': 'No JSON data received'}), 400
		
		# Validate required fields
		required_fields = ['full_name', 'email', 'appointment_date', 'appointment_type']
		for field in required_fields:
			if not data.get(field):
				# print(f"DEBUG: Missing required field: {field}")
				return jsonify({'error': f'{field} is required'}), 400
		
		# Parse appointment date
		try:
			# print(f"DEBUG: Parsing date: {data['appointment_date']}")
			appointment_datetime = datetime.strptime(data['appointment_date'], '%Y-%m-%dT%H:%M')
			# print(f"DEBUG: Parsed datetime: {appointment_datetime}")
		except ValueError as e:
			# print(f"DEBUG: Date parsing error: {e}")
			return jsonify({'error': f'Invalid date format: {data["appointment_date"]}. Expected format: YYYY-MM-DDTHH:MM'}), 400
		
		# Validate appointment type
		valid_types = ['Complaint', 'Admission', 'Meeting']
		# print(f"DEBUG: Appointment type received: '{data['appointment_type']}'")
		# print(f"DEBUG: Valid types: {valid_types}")
		if data['appointment_type'] not in valid_types:
			# print(f"DEBUG: Invalid appointment type: '{data['appointment_type']}' not in {valid_types}")
			return jsonify({'error': f'Invalid appointment type: {data["appointment_type"]}. Must be one of: {", ".join(valid_types)}'}), 400
		
		# Check spam protection - max 2 appointments per email per day
		is_spam, today_count = Appointment.check_spam_protection(data['email'], max_appointments=2)
		if is_spam:
			return jsonify({
				'error': f'You have already submitted {today_count} appointment requests today. Maximum of 2 appointments per day is allowed. Please try again tomorrow.',
				'spam_protection': True,
				'daily_count': today_count
			}), 429  # Too Many Requests
		
		# Generate appointment number for today
		try:
			appointment_number = Appointment.generate_appointment_number()
		except Exception as e:
			print(f"⚠️ Error generating appointment number: {e}")
			appointment_number = None  # Will be set later or auto-generated
		
		# Create new appointment
		appointment = Appointment(
			appointment_number=appointment_number,
			full_name=data['full_name'],
			email=data['email'],
			appointment_date=appointment_datetime,
			appointment_type=data['appointment_type'],
			appointment_description=data.get('appointment_description', ''),
			status='Pending'
		)
		
		db.session.add(appointment)
		try:
			db.session.commit()
		except Exception as db_error:
			db.session.rollback()
			print(f"❌ Database commit error: {db_error}")
			traceback.print_exc()
			# Re-raise to be caught by outer exception handler
			raise
		
		# Send notification about new appointment (wrapped in try-except to prevent 502 errors)
		try:
			# Get current user safely (returns None if not authenticated - OK for QR scan form)
			try:
				user = get_current_user()
			except Exception:
				user = None  # Safe fallback - QR scan form doesn't require authentication
			
			action_user_name = "Student"  # Default for QR code appointments
			
			# Only send notifications for student appointments (QR code) or when admin creates
			# Don't send notifications when committee members create appointments
			should_notify = True
			if user and user.username != 'discipline_officer':
				# This is a committee member creating appointment - don't notify
				should_notify = False
				print(f"⚠️ Committee member created appointment - no notification sent")
			else:
				# This is a student (QR code) or admin creating appointment - notify
				if user and user.username == 'discipline_officer':
					# Use just the name without role prefix
					action_user_name = user.full_name or user.username
					# Remove role prefixes if present
					if action_user_name.startswith('Discipline Officer '):
						action_user_name = action_user_name.replace('Discipline Officer ', '')
					elif action_user_name.startswith('Discipline Committee '):
						action_user_name = action_user_name.replace('Discipline Committee ', '')
				
				# Prepare appointment details for enhanced notification
				appointment_details = {
					'full_name': appointment.full_name,
					'appointment_type': appointment.appointment_type,
					'appointment_date': appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')
				}
				
				NotificationService.notify_appointment_action(
					action='created',
					appointment_id=appointment.id,
					action_user_name=action_user_name,
					appointment_details=appointment_details
				)
				print(f"✅ Notification sent for appointment {appointment.id}")
		except Exception as e:
			print(f"❌ Notification error: {e}")
			traceback.print_exc()
		
		# Send acknowledgment email (wrapped in try-except to prevent 502 errors)
		# Email is sent asynchronously - failure shouldn't block appointment creation
		try:
			EmailService.send_appointment_created(appointment)
		except Exception as e:
			print(f"❌ Email sending error (non-critical): {e}")
			traceback.print_exc()
			# Don't fail the request if email fails - appointment was already created
		
		# Create persistent notification in database for ALL users (admin and discipline committee)
		# Get all users (both admin and discipline committee) - wrapped in try-except
		try:
			from ...models import Role
			all_users = User.query.join(User.role).filter(
				Role.name.in_(['admin', 'user'])
			).all()
			
			# Create notification for each user (admin and discipline committee)
			for user in all_users:
				try:
					Notification.create_notification(
						title='New Appointment Request',
						message=f'{appointment.full_name} requested a {appointment.appointment_type.lower()} appointment on {appointment.appointment_date.strftime("%b %d, %Y at %I:%M %p")}',
						notification_type='appointment',
						reference_id=appointment.id,
						redirect_url=url_for('complaints.list_appointments'),
						user_id=user.id  # Send to each user individually
					)
				except Exception as e:
					print(f"❌ Error creating notification for user {user.id}: {e}")
					# Continue with next user even if one fails
		except Exception as e:
			print(f"❌ Error fetching users for notifications: {e}")
			traceback.print_exc()
			# Don't fail the request if notification creation fails
		
		# Broadcast real-time notification (wrapped in try-except)
		try:
			notification_data = {
				'type': 'new_appointment',
				'title': 'New Appointment Request',
				'message': f'{appointment.full_name} requested a {appointment.appointment_type.lower()} appointment',
				'timestamp': appointment.created_at.isoformat(),
					'data': {
						'appointment_id': appointment.id,
						'full_name': appointment.full_name,
						'appointment_type': appointment.appointment_type,
						'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d %I:%M %p'),
						'appointment_description': getattr(appointment, 'appointment_description', '')
					}
			}
			broadcast_notification(notification_data)
		except Exception as e:
			print(f"❌ Error broadcasting notification: {e}")
			# Don't fail the request if broadcast fails
		
		return jsonify({
			'message': 'Appointment created successfully',
			'appointment_id': appointment.id
		}), 201
		
	except Exception as e:
		db.session.rollback()
		error_msg = str(e)
		print(f"❌ Error creating appointment: {error_msg}")
		traceback.print_exc()
		
		# Return user-friendly error message
		# Don't expose internal error details in production
		if current_app.debug:
			return jsonify({'error': f'Error creating appointment: {error_msg}'}), 500
		else:
			return jsonify({'error': 'An error occurred while creating your appointment. Please try again or contact support.'}), 500


@bp.put('/appointments/<int:appointment_id>/confirm')
@csrf.exempt
@login_required
def confirm_appointment(appointment_id):
	"""Confirm an appointment and send email notification"""
	try:
		appointment = Appointment.query.get_or_404(appointment_id)
		
		# Get current user (the one confirming the appointment)
		current_user = get_current_user()
		
		# Update status to scheduled
		appointment.status = 'Scheduled'
		db.session.commit()
		
		# Send notification about appointment confirmation
		user = get_current_user()
		if user and user.username != 'discipline_officer':
			# This is a committee member confirming appointment - notify admin only
			try:
				# Create admin notification directly (not the full appointment notification)
				from ...services.notification_service import NotificationService
				# Prepare appointment details for enhanced notification
				appointment_details = {
					'full_name': appointment.full_name,
					'appointment_type': appointment.appointment_type,
					'appointment_date': appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')
				}
				
				# Clean action user name (remove role prefixes)
				action_user_name = user.full_name or user.username
				if action_user_name.startswith('Discipline Officer '):
					action_user_name = action_user_name.replace('Discipline Officer ', '')
				elif action_user_name.startswith('Discipline Committee '):
					action_user_name = action_user_name.replace('Discipline Committee ', '')
				
				NotificationService.notify_appointment_action(
					action='confirmed',
					appointment_id=appointment.id,
					action_user_name=action_user_name,
					appointment_details=appointment_details
				)
				print(f"✅ Admin notification sent for appointment confirmation")
			except Exception as e:
				print(f"❌ Notification error: {e}")
		
		# Send confirmation email with sender information
		EmailService.send_appointment_confirmation(appointment, sender_user=current_user)
		
		# Delete related notifications
		deleted_count = Notification.delete_by_reference('appointment', appointment_id)
		# print(f"DEBUG: Deleted {deleted_count} notifications for appointment {appointment_id}")
		
		# Send notification to admin if current user is discipline committee
		if current_user and current_user.role and current_user.role.name.lower() == 'user':
			Notification.notify_admin_user_action(
				action_performed="Appointment Confirmation",
				details=f"Confirmed appointment for {appointment.full_name} scheduled on {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')}",
				notification_type="appointment_management",
				redirect_url=url_for('complaints.list_appointments')
			)
		
		return jsonify({
			'message': 'Appointment confirmed successfully',
			'status': appointment.status
		}), 200
		
	except Exception as e:
		db.session.rollback()
		return jsonify({'error': str(e)}), 500


@bp.put('/appointments/<int:appointment_id>/reschedule')
@csrf.exempt
@login_required
def reschedule_appointment(appointment_id):
	"""Reschedule an appointment and send email notification"""
	try:
		appointment = Appointment.query.get_or_404(appointment_id)
		
		# Get current user (the one rescheduling the appointment)
		current_user = get_current_user()
		
		# Get custom message from request (if provided)
		custom_message = request.json.get('custom_message', '') if request.is_json else request.form.get('custom_message', '')
		
		# Update status to cancelled (for rescheduling)
		appointment.status = 'Cancelled'
		db.session.commit()
		
		# Send reschedule email notification with sender information and custom message
		EmailService.send_appointment_reschedule(
			appointment, 
			sender_user=current_user,
			custom_message=custom_message
		)
		
		# Delete related notifications
		deleted_count = Notification.delete_by_reference('appointment', appointment_id)
		# print(f"DEBUG: Deleted {deleted_count} notifications for appointment {appointment_id}")
		
		# Send notification to admin if current user is discipline committee
		if current_user and current_user.role and current_user.role.name.lower() == 'user':
			Notification.notify_admin_user_action(
				action_performed="Appointment Rescheduling",
				details=f"Rescheduled appointment for {appointment.full_name} originally scheduled on {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')}",
				notification_type="appointment_management",
				redirect_url=url_for('complaints.list_appointments')
			)
		
		return jsonify({
			'message': 'Appointment marked for rescheduling and email notification sent',
			'status': appointment.status
		}), 200
		
	except Exception as e:
		db.session.rollback()
		return jsonify({'error': str(e)}), 500


@bp.delete('/appointments/<int:appointment_id>')
@csrf.exempt
@login_required
def delete_appointment(appointment_id):
	"""Delete a specific appointment"""
	try:
		appointment = Appointment.query.get_or_404(appointment_id)
		
		# Store appointment details for logging
		appointment_name = appointment.full_name
		appointment_type = appointment.appointment_type
		appointment_date = appointment.appointment_date
		
		# Get current user (the one deleting the appointment)
		current_user = get_current_user()
		
		# Delete related notifications first
		deleted_count = Notification.delete_by_reference('appointment', appointment_id)
		# print(f"DEBUG: Deleted {deleted_count} notifications for appointment {appointment_id}")
		
		# Delete the appointment
		db.session.delete(appointment)
		db.session.commit()
		
		# Send notification to admin if current user is discipline committee
		if current_user and current_user.role and current_user.role.name.lower() == 'user':
			Notification.notify_admin_user_action(
				action_performed="Appointment Deletion",
				details=f"Deleted appointment for {appointment_name} ({appointment_type}) scheduled on {appointment_date.strftime('%B %d, %Y at %I:%M %p')}",
				notification_type="appointment_management",
				redirect_url=url_for('complaints.list_appointments')
			)
		
		return jsonify({
			'message': f'Appointment for {appointment_name} ({appointment_type}) deleted successfully'
		}), 200
		
	except Exception as e:
		db.session.rollback()
		return jsonify({'error': str(e)}), 500


@bp.delete('/appointments/all')
@login_required
def delete_all_appointments():
	"""Delete all appointments"""
	try:
		# Get count of appointments before deletion
		appointment_count = Appointment.query.count()
		
		if appointment_count == 0:
			return jsonify({
				'message': 'No appointments to delete'
			}), 200
		
		# Delete all appointments
		Appointment.query.delete()
		db.session.commit()
		
		return jsonify({
			'message': f'All {appointment_count} appointments deleted successfully'
		}), 200
		
	except Exception as e:
		db.session.rollback()
		return jsonify({'error': str(e)}), 500


@bp.get('/qr-scan')
def qr_scan_form():
	"""Display the QR scan appointment form"""
	return render_template("complaints/qr_scan_form.html")


@bp.get('/qr-generator')
@login_required
def qr_generator():
	"""Display the QR code generator page"""
	return render_template("complaints/qr_generator.html")


@bp.get('/qr-code')
def generate_qr_code():
	"""Generate QR code for appointment scheduling"""
	from flask import url_for
	
	# Get the QR scan URL
	qr_scan_url = url_for('complaints.qr_scan_form', _external=True)
	
	# For now, return the URL that can be used to generate QR codes
	# In production, you would use a QR code library like qrcode to generate the actual QR code image
	return jsonify({
		'qr_url': qr_scan_url,
		'message': 'QR Code URL generated. Use this URL to create a QR code that students can scan.'
	}), 200


# Global variable to store connected clients for real-time notifications
connected_clients = []

@bp.get('/notifications/stream')
@login_required
def notification_stream():
	"""Server-Sent Events endpoint for real-time notifications"""
	def event_stream():
		# Add this client to the connected clients list
		client_id = id(event_stream)
		connected_clients.append(client_id)
		
		try:
			# Send initial connection message
			yield f"data: {json.dumps({'type': 'connected', 'message': 'Connected to notification stream'})}\n\n"
			
			# Keep connection alive and send periodic heartbeats
			while True:
				time.sleep(30)  # Send heartbeat every 30 seconds
				yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"
				
		except GeneratorExit:
			# Client disconnected, remove from connected clients
			if client_id in connected_clients:
				connected_clients.remove(client_id)
	
	return Response(event_stream(), mimetype='text/event-stream', headers={
		'Cache-Control': 'no-cache',
		'Connection': 'keep-alive',
		'Access-Control-Allow-Origin': '*',
		'Access-Control-Allow-Headers': 'Cache-Control'
	})


def broadcast_notification(notification_data):
	"""Broadcast notification to all connected clients"""
	# Store notification in a simple in-memory list for now
	# In production, you'd use Redis or a proper message queue
	global connected_clients
	# For now, we'll just log it - the client will poll for updates
	print(f"Broadcasting notification: {notification_data}")


@bp.get('/api/notifications')
@login_required
def get_notifications_api():
	"""Get notifications for current user based on role"""
	try:
		# Get current user
		from ...auth_utils import get_current_user
		user = get_current_user()
		
		if not user:
			return jsonify({'notifications': [], 'unread_count': 0}), 200
		
		# Only admin (discipline officer) should see user action notifications
		# Discipline committee (user) should not see these notifications
		if user.role and user.role.name.lower() == 'admin':
			# Admin sees all notifications (including user action notifications)
			notifications = Notification.get_unread_notifications(user_id=None, limit=50)
			unread_count = Notification.get_unread_count(user_id=None)
		else:
			# Discipline committee sees only their own notifications (not user action notifications)
			notifications = Notification.get_unread_notifications(user_id=user.id, limit=50)
			unread_count = Notification.get_unread_count(user_id=user.id)
		
		notifications_data = []
		for notif in notifications:
			notifications_data.append({
				'id': notif.id,
				'title': notif.title,
				'message': notif.message,
				'notification_type': notif.notification_type,
				'reference_id': notif.reference_id,
				'redirect_url': notif.redirect_url,
				'is_read': notif.is_read,
				'created_at': notif.created_at.isoformat(),
				'time_ago': get_time_ago(notif.created_at)
			})
		
		return jsonify({
			'notifications': notifications_data,
			'unread_count': unread_count
		}), 200
		
	except Exception as e:
		return jsonify({'error': str(e)}), 500


@bp.post('/api/notifications/<int:notification_id>/mark-read')
@login_required
def mark_notification_read(notification_id):
	"""Mark a specific notification as read"""
	try:
		# Get current user
		from ...auth_utils import get_current_user
		user = get_current_user()
		
		if not user:
			return jsonify({'error': 'User not found'}), 401
		
		# Check if user can access this notification
		notification = Notification.query.get(notification_id)
		if not notification:
			return jsonify({'error': 'Notification not found'}), 404
		
		# Only admin can mark all notifications as read, discipline committee can only mark their own
		if user.role and user.role.name.lower() == 'admin':
			# Admin can mark any notification as read
			success = Notification.mark_as_read(notification_id)
		else:
			# Discipline committee can only mark their own notifications as read
			if notification.user_id == user.id:
				success = Notification.mark_as_read(notification_id)
			else:
				return jsonify({'error': 'Access denied'}), 403
		if success:
			return jsonify({'message': 'Notification marked as read'}), 200
		else:
			return jsonify({'error': 'Notification not found'}), 404
	except Exception as e:
		return jsonify({'error': str(e)}), 500


@bp.post('/api/notifications/mark-all-read')
@login_required
def mark_all_notifications_read():
	"""Mark all notifications as read"""
	try:
		# Get current user
		from ...auth_utils import get_current_user
		user = get_current_user()
		
		if not user:
			return jsonify({'error': 'User not found'}), 401
		
		# Only admin can mark all notifications as read, discipline committee can only mark their own
		if user.role and user.role.name.lower() == 'admin':
			# Admin can mark all notifications as read
			Notification.mark_all_as_read(user_id=None)
		else:
			# Discipline committee can only mark their own notifications as read
			Notification.mark_all_as_read(user_id=user.id)
		return jsonify({'message': 'All notifications marked as read'}), 200
	except Exception as e:
		return jsonify({'error': str(e)}), 500


def get_time_ago(timestamp):
	"""Convert timestamp to human-readable time ago format"""
	from datetime import datetime
	now = datetime.utcnow()
	diff = now - timestamp
	
	seconds = diff.total_seconds()
	if seconds < 60:
		return 'just now'
	elif seconds < 3600:
		minutes = int(seconds / 60)
		return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
	elif seconds < 86400:
		hours = int(seconds / 3600)
		return f'{hours} hour{"s" if hours != 1 else ""} ago'
	else:
		days = int(seconds / 86400)
		return f'{days} day{"s" if days != 1 else ""} ago'


@bp.post('/upload')
@login_required
def upload_complaint():
	"""Handle secure file uploads for complaints"""
	file = request.files.get('file')
	if not file:
		return jsonify({"error": "No file uploaded"}), 400
	try:
		path = save_upload(file, current_app.config['UPLOAD_FOLDER'])
		return jsonify({"message": "File uploaded successfully", "path": path}), 200
	except Exception as e:
		return jsonify({"error": str(e)}), 400


