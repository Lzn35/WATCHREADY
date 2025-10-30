from flask import jsonify, request, render_template, redirect, url_for, flash, session, make_response
from ...models import User
from ...auth_utils import login_user, logout_user, is_authenticated
from ...extensions import db, limiter, csrf
from . import bp


@bp.get('/login')
def login():
	# If user is already logged in, redirect to dashboard
	if is_authenticated():
		return redirect(url_for('core.dashboard'))
	return render_template("login.html")


@bp.post('/login')
def login_post():
	# If user is already logged in, redirect to dashboard
	if is_authenticated():
		return redirect(url_for('core.dashboard'))
	
	username = request.form.get('username', '').strip()
	password = request.form.get('password', '')
	selected_role = request.form.get('role', 'discipline_officer')  # Get selected role
	
	# Validate input
	if not username or not password:
		flash('Please enter both username and password.', 'error')
		return render_template("login.html")
	
	# Authenticate user
	user = User.authenticate(username, password)
	
	if user:
		# Validate role selection
		user_role_name = user.role.name.lower() if user.role else ''
		selected_role_mapping = {
			'discipline_officer': 'admin',
			'discipline_committee': 'user'
		}
		
		expected_role = selected_role_mapping.get(selected_role, 'admin')
		
		if user_role_name != expected_role:
			flash(f'Invalid role selection. Please select the correct role for your account.', 'error')
			return render_template("login.html")
		
		# Check if user is active
		if not user.is_active:
			flash('Your account has been deactivated. Please contact an administrator.', 'error')
			return render_template("login.html")
		
		# Login successful
		login_user(user)
		flash(f'Welcome back, {user.full_name or user.username}!', 'success')
		
		# Redirect to dashboard
		return redirect(url_for('core.dashboard'))
	else:
		flash('Invalid username, password, or role. Please try again.', 'error')
		return render_template("login.html")


@bp.post('/logout')
def logout():
	"""Logout user and clear session"""
	if is_authenticated():
		logout_user()
		flash('You have been logged out successfully.', 'info')
	return redirect(url_for('auth.login'))


@bp.get('/logout')
def logout_get():
	"""Logout user and clear session (GET request)"""
	if is_authenticated():
		logout_user()
		flash('You have been logged out successfully.', 'info')
	return redirect(url_for('auth.login'))


@bp.get('/profile')
def profile():
	"""User profile page"""
	if not is_authenticated():
		flash('Please log in to access this page.', 'error')
		return redirect(url_for('auth.login'))
	
	user = User.query.get(session.get('user_id'))
	if not user:
		flash('User not found.', 'error')
		return redirect(url_for('auth.login'))
	
	return render_template('profile.html', user=user)


@bp.post('/profile')
def update_profile():
	"""Update user profile"""
	if not is_authenticated():
		flash('Please log in to access this page.', 'error')
		return redirect(url_for('auth.login'))
	
	user = User.query.get(session.get('user_id'))
	if not user:
		flash('User not found.', 'error')
		return redirect(url_for('auth.login'))
	
	# Get form data
	full_name = request.form.get('full_name', '').strip()
	email = request.form.get('email', '').strip()
	phone = request.form.get('phone', '').strip()
	title = request.form.get('title', '').strip()
	gender = request.form.get('gender', '').strip()
	
	# Update user profile
	user.full_name = full_name if full_name else user.full_name
	user.email = email if email else user.email
	user.phone = phone if phone else user.phone
	user.title = title if title else user.title
	user.gender = gender if gender else user.gender
	
	try:
		db.session.commit()
		flash('Profile updated successfully!', 'success')
	except Exception as e:
		db.session.rollback()
		flash('Error updating profile. Please try again.', 'error')
	
	return redirect(url_for('auth.profile'))


@bp.post('/change-password')
def change_password():
	"""Change user password"""
	if not is_authenticated():
		flash('Please log in to access this page.', 'error')
		return redirect(url_for('auth.login'))
	
	user = User.query.get(session.get('user_id'))
	if not user:
		flash('User not found.', 'error')
		return redirect(url_for('auth.login'))
	
	# Get form data
	current_password = request.form.get('current_password', '')
	new_password = request.form.get('new_password', '')
	confirm_password = request.form.get('confirm_password', '')
	
	# Validate input
	if not current_password or not new_password or not confirm_password:
		flash('Please fill in all password fields.', 'error')
		return redirect(url_for('auth.profile'))
	
	# Verify current password
	if not user.check_password(current_password):
		flash('Current password is incorrect.', 'error')
		return redirect(url_for('auth.profile'))
	
	# Validate new password
	if new_password != confirm_password:
		flash('New passwords do not match.', 'error')
		return redirect(url_for('auth.profile'))
	
	if len(new_password) < 6:
		flash('New password must be at least 6 characters long.', 'error')
		return redirect(url_for('auth.profile'))
	
	# Update password
	user.set_password(new_password)
	
	try:
		db.session.commit()
		flash('Password changed successfully!', 'success')
	except Exception as e:
		db.session.rollback()
		flash('Error changing password. Please try again.', 'error')
	
	return redirect(url_for('auth.profile'))


@bp.get('/api/user-info')
def get_user_info():
	"""Get current user information for API"""
	if not is_authenticated():
		return jsonify({'error': 'Not authenticated'}), 401
	
	user = User.query.get(session.get('user_id'))
	if not user:
		return jsonify({'error': 'User not found'}), 404
	
	return jsonify({
		'id': user.id,
		'username': user.username,
		'full_name': user.full_name,
		'email': user.email,
		'role': user.role.name if user.role else None,
		'is_active': user.is_active
	})


@bp.get('/api/check-auth')
def check_auth():
	"""Check if user is authenticated"""
	if is_authenticated():
		user = User.query.get(session.get('user_id'))
		return jsonify({
			'authenticated': True,
			'user': {
				'id': user.id,
				'username': user.username,
				'full_name': user.full_name,
				'role': user.role.name if user.role else None
			}
		})
	else:
		return jsonify({'authenticated': False})