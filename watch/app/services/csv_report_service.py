"""CSV Report Generation Service
Panel Recommendation: Use CSV for generating reports with proper templates
"""

import csv
import os
import tempfile
from datetime import datetime
from ..models import AttendanceHistory, Case, Person, Appointment, Schedule


class CSVReportService:
	"""Generate CSV reports with proper templates for export"""
	
	@staticmethod
	def generate_attendance_report(start_date, end_date, faculty_filter=None, status_filter=None):
		"""
		Generate attendance report in CSV format
		
		Args:
			start_date: Start date for report
			end_date: End date for report
			faculty_filter: Optional faculty name filter
			status_filter: Optional status filter (Present, Absent, Late)
		
		Returns:
			tuple: (filepath, filename)
		"""
		# Query attendance data
		query = AttendanceHistory.query.filter(
			AttendanceHistory.date >= start_date,
			AttendanceHistory.date <= end_date
		)
		
		if faculty_filter:
			query = query.filter(AttendanceHistory.professor_name == faculty_filter)
		
		if status_filter:
			query = query.filter(AttendanceHistory.status == status_filter)
		
		records = query.order_by(AttendanceHistory.date.desc()).all()
		
		# Create CSV file
		temp_dir = tempfile.gettempdir()
		filename = f'attendance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
		filepath = os.path.join(temp_dir, filename)
		
		with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
			writer = csv.writer(csvfile)
			
			# Header section
			writer.writerow(['WATCHREADY - Attendance Report'])
			writer.writerow(['Web-based Attendance Tracking and Case Handling System'])
			writer.writerow([])
			writer.writerow(['Report Period:', f'{start_date} to {end_date}'])
			writer.writerow(['Generated On:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
			writer.writerow(['Total Records:', len(records)])
			if faculty_filter:
				writer.writerow(['Faculty Filter:', faculty_filter])
			if status_filter:
				writer.writerow(['Status Filter:', status_filter])
			writer.writerow([])
			
			# Data section
			writer.writerow(['Date', 'Faculty Name', 'Status', 'Time Recorded'])
			
			for record in records:
				writer.writerow([
					record.date.strftime('%Y-%m-%d'),
					record.professor_name,
					record.status,
					record.created_at.strftime('%I:%M %p')
				])
			
			# Summary statistics
			writer.writerow([])
			writer.writerow(['Summary Statistics'])
			writer.writerow([])
			
			status_counts = {}
			for record in records:
				status_counts[record.status] = status_counts.get(record.status, 0) + 1
			
			writer.writerow(['Status', 'Count', 'Percentage'])
			for status, count in status_counts.items():
				percentage = (count / len(records) * 100) if records else 0
				writer.writerow([status, count, f'{percentage:.1f}%'])
		
		return filepath, filename
	
	@staticmethod
	def generate_cases_report(case_type=None, entity_type=None, start_date=None, end_date=None):
		"""
		Generate cases report in CSV format
		
		Args:
			case_type: Filter by case type ('minor' or 'major')
			entity_type: Filter by entity type ('student', 'faculty', 'staff')
			start_date: Optional start date
			end_date: Optional end date
		
		Returns:
			tuple: (filepath, filename)
		"""
		# Query cases
		query = Case.query
		
		if case_type:
			query = query.filter(Case.case_type == case_type)
		
		if start_date:
			query = query.filter(Case.date_reported >= start_date)
		
		if end_date:
			query = query.filter(Case.date_reported <= end_date)
		
		cases = query.order_by(Case.created_at.desc()).all()
		
		# Filter by entity type (requires joining with Person)
		if entity_type:
			cases = [c for c in cases if c.person and c.person.role == entity_type]
		
		# Create CSV file
		temp_dir = tempfile.gettempdir()
		filename = f'cases_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
		filepath = os.path.join(temp_dir, filename)
		
		with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
			writer = csv.writer(csvfile)
			
			# Header section
			writer.writerow(['WATCHREADY - Cases Report'])
			writer.writerow(['Web-based Attendance Tracking and Case Handling System'])
			writer.writerow([])
			writer.writerow(['Generated On:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
			writer.writerow(['Total Cases:', len(cases)])
			if case_type:
				writer.writerow(['Case Type Filter:', case_type.capitalize()])
			if entity_type:
				writer.writerow(['Entity Type Filter:', entity_type.capitalize()])
			if start_date or end_date:
				period = f"{start_date or 'Start'} to {end_date or 'End'}"
				writer.writerow(['Date Range:', period])
			writer.writerow([])
			
			# Data section
			writer.writerow([
				'Case ID', 'Full Name', 'Role', 'Program/Dept', 'Section',
				'Case Type', 'Offense Category', 'Offense Type',
				'Date Reported', 'Status', 'Remarks'
			])
			
			for case in cases:
				writer.writerow([
					case.id,
					case.person.full_name if case.person else 'N/A',
					case.person.role if case.person else 'N/A',
					case.person.program_or_dept if case.person else 'N/A',
					case.person.get_section_display() if case.person else 'N/A',
					case.case_type.capitalize(),
					case.offense_category or 'N/A',
					case.offense_type or 'N/A',
					case.date_reported.strftime('%Y-%m-%d'),
					case.status,
					case.remarks or 'N/A'
				])
			
			# Summary statistics
			writer.writerow([])
			writer.writerow(['Summary Statistics'])
			writer.writerow([])
			
			# Count by case type
			type_counts = {}
			for case in cases:
				type_counts[case.case_type] = type_counts.get(case.case_type, 0) + 1
			
			writer.writerow(['Case Type', 'Count'])
			for case_type, count in type_counts.items():
				writer.writerow([case_type.capitalize(), count])
			
			writer.writerow([])
			
			# Count by status
			status_counts = {}
			for case in cases:
				status_counts[case.status] = status_counts.get(case.status, 0) + 1
			
			writer.writerow(['Status', 'Count'])
			for status, count in status_counts.items():
				writer.writerow([status, count])
		
		return filepath, filename
	
	@staticmethod
	def generate_appointments_report(start_date=None, end_date=None, status_filter=None, type_filter=None):
		"""
		Generate appointments report in CSV format
		
		Args:
			start_date: Optional start date
			end_date: Optional end date
			status_filter: Optional status filter
			type_filter: Optional appointment type filter
		
		Returns:
			tuple: (filepath, filename)
		"""
		# Query appointments
		query = Appointment.query
		
		if start_date:
			query = query.filter(Appointment.appointment_date >= start_date)
		
		if end_date:
			query = query.filter(Appointment.appointment_date <= end_date)
		
		if status_filter:
			query = query.filter(Appointment.status == status_filter)
		
		if type_filter:
			query = query.filter(Appointment.appointment_type == type_filter)
		
		appointments = query.order_by(Appointment.appointment_date.asc()).all()
		
		# Create CSV file
		temp_dir = tempfile.gettempdir()
		filename = f'appointments_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
		filepath = os.path.join(temp_dir, filename)
		
		with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
			writer = csv.writer(csvfile)
			
			# Header section
			writer.writerow(['WATCHREADY - Appointments Report'])
			writer.writerow(['Web-based Attendance Tracking and Case Handling System'])
			writer.writerow([])
			writer.writerow(['Generated On:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
			writer.writerow(['Total Appointments:', len(appointments)])
			if status_filter:
				writer.writerow(['Status Filter:', status_filter])
			if type_filter:
				writer.writerow(['Type Filter:', type_filter])
			if start_date or end_date:
				period = f"{start_date or 'Start'} to {end_date or 'End'}"
				writer.writerow(['Date Range:', period])
			writer.writerow([])
			
			# Data section
			writer.writerow([
				'Appointment Number', 'Full Name', 'Email', 
				'Appointment Date', 'Type', 'Description', 'Status', 'Created At'
			])
			
			for apt in appointments:
				writer.writerow([
					apt.appointment_number or 'N/A',
					apt.full_name,
					apt.email,
					apt.appointment_date.strftime('%Y-%m-%d %H:%M'),
					apt.appointment_type,
					apt.appointment_description or 'N/A',
					apt.status,
					apt.created_at.strftime('%Y-%m-%d %H:%M:%S')
				])
			
			# Summary statistics
			writer.writerow([])
			writer.writerow(['Summary Statistics'])
			writer.writerow([])
			
			# Count by status
			status_counts = {}
			for apt in appointments:
				status_counts[apt.status] = status_counts.get(apt.status, 0) + 1
			
			writer.writerow(['Status', 'Count'])
			for status, count in status_counts.items():
				writer.writerow([status, count])
			
			writer.writerow([])
			
			# Count by type
			type_counts = {}
			for apt in appointments:
				type_counts[apt.appointment_type] = type_counts.get(apt.appointment_type, 0) + 1
			
			writer.writerow(['Type', 'Count'])
			for apt_type, count in type_counts.items():
				writer.writerow([apt_type, count])
		
		return filepath, filename
	
	@staticmethod
	def generate_schedule_report():
		"""
		Generate current schedules report in CSV format
		
		Returns:
			tuple: (filepath, filename)
		"""
		schedules = Schedule.query.order_by(
			Schedule.day_of_week, 
			Schedule.start_time
		).all()
		
		# Create CSV file
		temp_dir = tempfile.gettempdir()
		filename = f'schedules_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
		filepath = os.path.join(temp_dir, filename)
		
		with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
			writer = csv.writer(csvfile)
			
			# Header section
			writer.writerow(['WATCHREADY - Faculty Schedules Report'])
			writer.writerow(['Web-based Attendance Tracking and Case Handling System'])
			writer.writerow([])
			writer.writerow(['Generated On:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
			writer.writerow(['Total Schedules:', len(schedules)])
			writer.writerow([])
			
			# Data section
			writer.writerow([
				'Professor Name', 'Subject', 'Day', 
				'Start Time', 'End Time', 'Room'
			])
			
			for schedule in schedules:
				writer.writerow([
					schedule.professor_name,
					schedule.subject,
					schedule.day_of_week,
					schedule.start_time.strftime('%H:%M'),
					schedule.end_time.strftime('%H:%M'),
					schedule.get_room_display() if hasattr(schedule, 'get_room_display') else (schedule.room or 'TBA')
				])
		
		return filepath, filename





