from flask import jsonify, request, render_template, redirect, url_for, flash, session, make_response
from ...models import User
from ...auth_utils import login_user, logout_user, is_authenticated, login_required
from ...extensions import db, limiter, csrf
from . import bp


@bp.get('/login')
def login():
	# If user is already logged in, redirect to dashboard
	if is_authenticated():
		return redirect(url_for('core.dashboard'))
	return render_template("login.html")


@bp.post('/login')
@limiter.limit('5 per 5 minutes')
def login_post():
	"""
	Unified login with automatic role detection
	Panel Recommendation: No need for separate role buttons
	"""
	# If user is already logged in, redirect to dashboard
	if is_authenticated():
		return redirect(url_for('core.dashboard'))
	
	username = request.form.get('username', '').strip()
	password = request.form.get('password', '')
	
	# Validate input
	if not username or not password:
		flash('Please enter both username and password.', 'error')
		return render_template("login.html")
	
	# Authenticate user
	user = User.authenticate(username, password)
	
	if user:
		# Check if user is active
		if not user.is_active:
			flash('Your account has been deactivated. Please contact the administrator.', 'error')
			return render_template("login.html")
		
		# Login successful - role is automatically detected from user.role
		# Check if "Remember Me" checkbox was checked
		remember = request.form.get('remember', '').lower() in ('on', 'true', '1', 'yes')
		# Default: remember=False means session expires when browser/tab closes
		login_user(user, remember=remember)
		
		# Determine user role display name
		role_display = 'Administrator' if user.is_admin() else 'Discipline Committee'
		
		# Log the login activity
		from ...models import AuditLog
		AuditLog.log_activity(
			action_type='Login',
			description=f'User {username} logged in successfully as {user.role.name} ({role_display})',
			user_id=user.id,
			ip_address=request.remote_addr,
			user_agent=request.headers.get('User-Agent')
		)
		
		# Welcome message with role indication
		flash(f'Welcome back, {user.full_name or user.username} ({role_display})!', 'success')
		
		# Redirect to the page they were trying to access, or dashboard
		next_url = session.pop('next_url', None)
		return redirect(next_url or url_for('core.dashboard'))
	else:
		# Login failed
		flash('Invalid username or password. Please try again.', 'error')
		
		# Log the failed login attempt
		from ...models import AuditLog
		AuditLog.log_activity(
			action_type='Failed Login',
			description=f'Failed login attempt for username: {username}',
			ip_address=request.remote_addr,
			user_agent=request.headers.get('User-Agent')
		)
		
		return render_template("login.html")


@bp.get('/register')
def register():
	return render_template("register.html")


@bp.get('/forgot-password')
def forgot_password():
	return render_template("deskapp/forgot-password.html")


@bp.get('/logout')
@bp.post('/logout')
def logout():
	# Log the logout activity if user is logged in
	if is_authenticated():
		from ...models import AuditLog
		username = session.get('username', 'Unknown')
		user_id = session.get('user_id')
		
		AuditLog.log_activity(
			action_type='Logout',
			description=f'User {username} logged out',
			user_id=user_id,
			ip_address=request.remote_addr,
			user_agent=request.headers.get('User-Agent')
		)
	
	# Clear the session using logout_user
	logout_user()
	
	flash('You have been logged out successfully.', 'info')
	
	# Create response with explicit redirect and clear session cookie
	resp = make_response(redirect(url_for('auth.login')))
	
	# Clear all session-related cookies (Flask default session cookie name is 'session')
	resp.set_cookie('session', '', expires=0, max_age=0, path='/')
	
	# Additional cache control headers (belt and suspenders approach)
	resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
	resp.headers['Pragma'] = 'no-cache'
	resp.headers['Expires'] = '0'
	
	return resp


@bp.post('/auto-logout')
@csrf.exempt  # Exempt from CSRF as this is called via sendBeacon on page unload
def auto_logout():
	"""Handle automatic logout when browser/tab closes or idle timeout"""
	# Log the auto logout activity if user is logged in
	if is_authenticated():
		from ...models import AuditLog
		username = session.get('username', 'Unknown')
		user_id = session.get('user_id')
		
		# Determine logout reason
		logout_reason = request.form.get('reason', 'browser/tab closed')
		
		AuditLog.log_activity(
			action_type='Auto Logout',
			description=f'User {username} automatically logged out ({logout_reason})',
			user_id=user_id,
			ip_address=request.remote_addr,
			user_agent=request.headers.get('User-Agent')
		)
	
	# Clear the session
	logout_user()
	
	# Return success response (no redirect needed for beacon)
	return '', 204  # 204 No Content


@bp.post('/session-heartbeat')
@csrf.exempt  # Allow heartbeat without CSRF for convenience
def session_heartbeat():
	"""Reset session timeout on user activity - called by client-side inactivity timer"""
	try:
		# Check if user is authenticated
		if not is_authenticated():
			return jsonify({'success': False, 'message': 'Not authenticated'}), 401
		
		# Refresh session by touching it - this resets the session expiration time
		# But DON'T change session.permanent - respect the user's original choice
		user_id = session.get('user_id')
		if user_id:
			# Touch session by modifying it slightly (keeps current permanent setting)
			# Don't force permanent=True - let the session expire when browser closes if user chose that
			session['last_activity'] = request.headers.get('User-Agent', '')
			# Return success
			return jsonify({'success': True, 'message': 'Session refreshed'}), 200
		else:
			return jsonify({'success': False, 'message': 'Not authenticated'}), 401
	except Exception as e:
		return jsonify({'success': False, 'message': 'Error refreshing session'}), 500




@bp.get('/me')
def me():
	if is_authenticated():
		user_id = session.get('user_id')
		user = User.query.get(user_id) if user_id else None
		if user:
			return jsonify({
				"user": {
					"id": user.id,
					"username": user.username,
					"role": user.role.name if user.role else None
				}
			}), 200
	return jsonify({"user": None}), 200


@bp.post('/forgot-password')
@limiter.limit('3 per minute')
def forgot_password_post():
	"""Handle forgot password requests"""
	try:
		data = request.get_json()
		username = data.get('username', '').strip()
		email = data.get('email', '').strip()
		
		if not username or not email:
			return jsonify({'success': False, 'error': 'Please provide both username and email address'}), 400
		
		# Find user by username and email
		user = User.query.filter_by(username=username, email=email).first()
		
		if not user:
			return jsonify({'success': False, 'error': 'No account found with that username and email combination'}), 404
		
		# Check if user is active
		if not user.is_active:
			return jsonify({'success': False, 'error': 'Account is deactivated. Please contact the administrator'}), 403
		
		# Generate temporary password
		import secrets
		import string
		temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
		
		# Update user password
		user.set_password(temp_password)
		db.session.commit()
		
		# Log the password reset
		from ...models import AuditLog
		AuditLog.log_activity(
			action_type='Password Reset',
			description=f'Password reset for user {username}',
			user_id=user.id,
			ip_address=request.remote_addr,
			user_agent=request.headers.get('User-Agent')
		)
		
		return jsonify({
			'success': True, 
			'message': f'Password reset successful! Your new temporary password is: {temp_password}. Please log in and change it immediately.',
			'temp_password': temp_password
		}), 200
		
	except Exception as e:
		return jsonify({'success': False, 'error': f'An error occurred: {str(e)}'}), 500


