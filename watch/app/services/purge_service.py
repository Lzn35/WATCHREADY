"""Data Purging Service with CSV Archiving
Panel Recommendation: Purge old data with CSV archives for record keeping
"""

import csv
import os
import shutil
from datetime import datetime, timedelta, date
from ..models import (
	AuditLog, ActivityLog, Notification, Appointment, 
	AttendanceChecklist, AttendanceHistory, Person, Case, Section, db
)


class PurgeService:
	"""Service for managing database purging operations with CSV archiving"""
	
	ARCHIVE_BASE_DIR = os.path.join('instance', 'archives')
	
	@staticmethod
	def create_backup_before_purge():
		"""Create database backup before purging"""
		db_path = 'instance/watch_db.sqlite'
		if not os.path.exists(db_path):
			return None
		
		backup_dir = os.path.join('instance', 'backups')
		os.makedirs(backup_dir, exist_ok=True)
		
		backup_filename = f'watch_db.sqlite.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}'
		backup_path = os.path.join(backup_dir, backup_filename)
		
		shutil.copy2(db_path, backup_path)
		return backup_path
	
	@staticmethod
	def purge_audit_logs(days_to_keep=90, archive=True):
		"""Purge audit logs older than specified days with CSV archiving"""
		from datetime import datetime, timedelta
		
		archive_dir = os.path.join(PurgeService.ARCHIVE_BASE_DIR, 'audit_logs')
		cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
		old_logs = AuditLog.query.filter(AuditLog.timestamp < cutoff_date).all()
		
		if not old_logs:
			return 0, "No logs to purge", None
		
		csv_path = None
		if archive:
			os.makedirs(archive_dir, exist_ok=True)
			csv_filename = f'audit_logs_archive_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
			csv_path = os.path.join(archive_dir, csv_filename)
			
			# Write to CSV
			with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
				fieldnames = ['ID', 'Timestamp', 'Action Type', 'Description', 'User ID', 
							 'IP Address', 'User Agent']
				writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
				
				writer.writeheader()
				for log in old_logs:
					writer.writerow({
						'ID': log.id,
						'Timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
						'Action Type': log.action_type,
						'Description': log.description,
						'User ID': log.user_id or 'N/A',
						'IP Address': log.ip_address or 'N/A',
						'User Agent': log.user_agent or 'N/A'
					})
		
		# Delete from database
		count = len(old_logs)
		AuditLog.query.filter(AuditLog.timestamp < cutoff_date).delete()
		db.session.commit()
		
		return count, f"Purged {count} audit log(s)", csv_path
	
	@staticmethod
	def purge_notifications(days_to_keep=30, read_only=True, archive=True):
		"""Purge notifications with CSV archiving"""
		archive_dir = os.path.join(PurgeService.ARCHIVE_BASE_DIR, 'notifications')
		cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
		
		query = Notification.query.filter(Notification.created_at < cutoff_date)
		if read_only:
			query = query.filter(Notification.is_read == True)
		
		old_notifications = query.all()
		
		if not old_notifications:
			return 0, "No notifications to purge", None
		
		csv_path = None
		if archive:
			os.makedirs(archive_dir, exist_ok=True)
			csv_filename = f'notifications_archive_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
			csv_path = os.path.join(archive_dir, csv_filename)
			
			with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
				fieldnames = ['ID', 'User ID', 'Title', 'Message', 'Type', 'Reference ID', 
							 'Is Read', 'Redirect URL', 'Created At']
				writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
				
				writer.writeheader()
				for notif in old_notifications:
					writer.writerow({
						'ID': notif.id,
						'User ID': notif.user_id or 'Admin',
						'Title': notif.title,
						'Message': notif.message,
						'Type': notif.notification_type,
						'Reference ID': notif.reference_id or 'N/A',
						'Is Read': 'Yes' if notif.is_read else 'No',
						'Redirect URL': notif.redirect_url or 'N/A',
						'Created At': notif.created_at.strftime('%Y-%m-%d %H:%M:%S')
					})
		
		count = len(old_notifications)
		query.delete()
		db.session.commit()
		
		return count, f"Purged {count} notification(s)", csv_path
	
	@staticmethod
	def purge_appointments(days_to_keep=180, status_filter='Cancelled', archive=True):
		"""Purge old appointments with CSV archiving"""
		archive_dir = os.path.join(PurgeService.ARCHIVE_BASE_DIR, 'appointments')
		cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
		
		query = Appointment.query.filter(Appointment.created_at < cutoff_date)
		if status_filter:
			query = query.filter(Appointment.status == status_filter)
		
		old_appointments = query.all()
		
		if not old_appointments:
			return 0, "No appointments to purge", None
		
		csv_path = None
		if archive:
			os.makedirs(archive_dir, exist_ok=True)
			csv_filename = f'appointments_archive_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
			csv_path = os.path.join(archive_dir, csv_filename)
			
			with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
				fieldnames = ['ID', 'Appointment Number', 'Full Name', 'Email', 
							 'Appointment Date', 'Type', 'Description', 'Status', 
							 'QR Code Data', 'Created At']
				writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
				
				writer.writeheader()
				for apt in old_appointments:
					writer.writerow({
						'ID': apt.id,
						'Appointment Number': apt.appointment_number or 'N/A',
						'Full Name': apt.full_name,
						'Email': apt.email,
						'Appointment Date': apt.appointment_date.strftime('%Y-%m-%d %H:%M:%S'),
						'Type': apt.appointment_type,
						'Description': apt.appointment_description or 'N/A',
						'Status': apt.status,
						'QR Code Data': apt.qr_code_data or 'N/A',
						'Created At': apt.created_at.strftime('%Y-%m-%d %H:%M:%S')
					})
		
		count = len(old_appointments)
		query.delete()
		db.session.commit()
		
		return count, f"Purged {count} appointment(s)", csv_path
	
	@staticmethod
	def purge_graduated_students(academic_year, archive=True):
		"""
		Purge graduated students with CSV archiving
		Panel Recommendation: Detect and purge students after graduation
		"""
		archive_dir = os.path.join(PurgeService.ARCHIVE_BASE_DIR, 'graduated_students')
		
		# Get graduated sections for this academic year
		graduated_sections = Section.query.filter_by(
			academic_year=academic_year,
			is_graduated=True
		).all()
		
		if not graduated_sections:
			return 0, "No graduated sections found", None
		
		# Collect student data
		student_data = []
		students_to_delete = []
		
		for section in graduated_sections:
			students = Person.query.filter_by(
				role='student',
				section_id=section.id
			).all()
			
			for student in students:
				# Get their cases
				cases = Case.get_cases_by_person(student.id)
				
				student_data.append({
					'ID': student.id,
					'Full Name': student.full_name,
					'First Name': student.first_name or '',
					'Last Name': student.last_name or '',
					'Section': section.section_code,
					'Program': student.program_or_dept,
					'Academic Year': section.academic_year,
					'Graduation Date': section.graduation_date.strftime('%Y-%m-%d') if section.graduation_date else 'N/A',
					'Minor Cases': len([c for c in cases if c.case_type == 'minor']),
					'Major Cases': len([c for c in cases if c.case_type == 'major']),
					'Total Cases': len(cases)
				})
				students_to_delete.append(student)
		
		if not student_data:
			return 0, "No students found in graduated sections", None
		
		csv_path = None
		if archive:
			os.makedirs(archive_dir, exist_ok=True)
			csv_filename = f'graduated_students_{academic_year.replace("-", "_")}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
			csv_path = os.path.join(archive_dir, csv_filename)
			
			with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
				fieldnames = ['ID', 'Full Name', 'First Name', 'Last Name', 'Section', 
							 'Program', 'Academic Year', 'Graduation Date', 
							 'Minor Cases', 'Major Cases', 'Total Cases']
				writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
				
				writer.writeheader()
				writer.writerows(student_data)
		
		# Delete students and their cases
		for student in students_to_delete:
			# Delete their cases first (cascade should handle this, but be explicit)
			Case.query.filter_by(person_id=student.id).delete()
			db.session.delete(student)
		
		db.session.commit()
		
		return len(students_to_delete), f"Purged {len(students_to_delete)} graduated students", csv_path
	
	@staticmethod
	def purge_all_with_archive(dry_run=False):
		"""
		Execute complete purge with CSV archiving
		Panel Recommendation: Comprehensive data purging
		"""
		results = {
			'audit_logs': {'count': 0, 'csv': None},
			'notifications_read': {'count': 0, 'csv': None},
			'notifications_old': {'count': 0, 'csv': None},
			'appointments': {'count': 0, 'csv': None},
			'total_purged': 0,
			'dry_run': dry_run,
			'backup_path': None,
			'csv_files': []
		}
		
		if dry_run:
			# Just count what would be purged
			cutoff_90 = datetime.utcnow() - timedelta(days=90)
			cutoff_30 = datetime.utcnow() - timedelta(days=30)
			cutoff_180 = datetime.utcnow() - timedelta(days=180)
			
			results['audit_logs']['count'] = AuditLog.query.filter(
				AuditLog.timestamp < cutoff_90
			).count()
			
			results['notifications_read']['count'] = Notification.query.filter(
				Notification.is_read == True,
				Notification.created_at < cutoff_30
			).count()
			
			results['notifications_old']['count'] = Notification.query.filter(
				Notification.created_at < cutoff_90
			).count()
			
			results['appointments']['count'] = Appointment.query.filter(
				Appointment.created_at < cutoff_180,
				Appointment.status == 'Cancelled'
			).count()
			
			results['total_purged'] = sum([
				results['audit_logs']['count'],
				results['notifications_read']['count'],
				results['notifications_old']['count'],
				results['appointments']['count']
			])
		else:
			# Create backup first
			results['backup_path'] = PurgeService.create_backup_before_purge()
			
			# Execute purges with archiving
			count, msg, csv_path = PurgeService.purge_audit_logs(days_to_keep=90, archive=True)
			results['audit_logs'] = {'count': count, 'csv': csv_path}
			if csv_path:
				results['csv_files'].append(csv_path)
			
			count, msg, csv_path = PurgeService.purge_notifications(
				days_to_keep=30, read_only=True, archive=True
			)
			results['notifications_read'] = {'count': count, 'csv': csv_path}
			if csv_path:
				results['csv_files'].append(csv_path)
			
			count, msg, csv_path = PurgeService.purge_notifications(
				days_to_keep=90, read_only=False, archive=True
			)
			results['notifications_old'] = {'count': count, 'csv': csv_path}
			if csv_path:
				results['csv_files'].append(csv_path)
			
			count, msg, csv_path = PurgeService.purge_appointments(
				days_to_keep=180, status_filter='Cancelled', archive=True
			)
			results['appointments'] = {'count': count, 'csv': csv_path}
			if csv_path:
				results['csv_files'].append(csv_path)
			
			results['total_purged'] = sum([
				results['audit_logs']['count'],
				results['notifications_read']['count'],
				results['notifications_old']['count'],
				results['appointments']['count']
			])
		
		return results
	
	@staticmethod
	def get_archive_summary():
		"""Get summary of all archived CSV files"""
		archives = []
		
		if not os.path.exists(PurgeService.ARCHIVE_BASE_DIR):
			return archives
		
		for root, dirs, files in os.walk(PurgeService.ARCHIVE_BASE_DIR):
			for file in files:
				if file.endswith('.csv'):
					file_path = os.path.join(root, file)
					file_size = os.path.getsize(file_path)
					file_date = datetime.fromtimestamp(os.path.getmtime(file_path))
					
					archives.append({
						'filename': file,
						'path': file_path,
						'size': file_size,
						'size_mb': round(file_size / (1024 * 1024), 2),
						'date': file_date.strftime('%Y-%m-%d %H:%M:%S'),
						'category': os.path.basename(os.path.dirname(file_path))
					})
		
		# Sort by date (newest first)
		archives.sort(key=lambda x: x['date'], reverse=True)
		return archives



