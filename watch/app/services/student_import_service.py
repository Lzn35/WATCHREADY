"""Student Import Service - CSV import/export functionality
Panel Recommendation: Import student data from exported CSV files
"""

import csv
import os
from datetime import datetime
from ..models import Person, Section, db
from ..extensions import db


class StudentImportService:
	"""Service for importing and exporting student data via CSV"""
	
	@staticmethod
	def validate_csv_format(file_path):
		"""
		Validate CSV has required columns
		
		Required columns: first_name, last_name, section, program
		Optional columns: year_level, section_name, academic_year
		"""
		required_columns = ['first_name', 'last_name', 'section', 'program']
		
		try:
			with open(file_path, 'r', encoding='utf-8') as f:
				reader = csv.DictReader(f)
				if not reader.fieldnames:
					return False, "CSV file is empty or invalid"
				
				headers = [h.lower().strip() for h in reader.fieldnames]
				
				missing_columns = [col for col in required_columns if col not in headers]
				
				if missing_columns:
					return False, f"Missing required columns: {', '.join(missing_columns)}"
				
				return True, "CSV format is valid"
		except Exception as e:
			return False, f"Error reading CSV: {str(e)}"
	
	@staticmethod
	def import_students_from_csv(file_path, academic_year, create_sections=True):
		"""
		Import students from CSV file
		
		Expected CSV format:
		first_name, last_name, section, program, [year_level], [section_name]
		
		Args:
			file_path: Path to CSV file
			academic_year: Academic year (e.g., "2024-2025")
			create_sections: If True, create sections that don't exist
		
		Returns:
			tuple: (imported_count, skipped_count, errors_list)
		"""
		imported_count = 0
		skipped_count = 0
		errors = []
		
		try:
			with open(file_path, 'r', encoding='utf-8') as f:
				reader = csv.DictReader(f)
				
				for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
					try:
						# Extract data
						first_name = row.get('first_name', '').strip()
						last_name = row.get('last_name', '').strip()
						section_code = row.get('section', '').strip()
						program = row.get('program', '').strip()
						year_level = row.get('year_level', '').strip() or 'N/A'
						section_name = row.get('section_name', '').strip()
						
						# Validation
						if not all([first_name, last_name, section_code, program]):
							errors.append(f"Row {row_num}: Missing required fields (first_name, last_name, section, or program)")
							skipped_count += 1
							continue
						
						# Parse section name from section code if not provided
						if not section_name and '-' in section_code:
							section_name = section_code.split('-')[-1]
						elif not section_name:
							section_name = 'A'
						
						# Check if section exists
						section = Section.query.filter_by(section_code=section_code).first()
						
						if not section and create_sections:
							# Create section if it doesn't exist
							section = Section(
								section_code=section_code,
								program=program,
								year_level=year_level,
								section_name=section_name,
								academic_year=academic_year,
								is_active=True,
								is_graduated=False
							)
							db.session.add(section)
							db.session.flush()  # Get section ID
						elif not section:
							errors.append(f"Row {row_num}: Section '{section_code}' does not exist")
							skipped_count += 1
							continue
						
						# Check if student already exists
						full_name = f"{first_name} {last_name}"
						existing_student = Person.query.filter_by(
							full_name=full_name,
							role='student'
						).first()
						
						if existing_student:
							errors.append(f"Row {row_num}: Student '{full_name}' already exists")
							skipped_count += 1
							continue
						
						# Create new student
						new_student = Person(
							full_name=full_name,
							first_name=first_name,
							last_name=last_name,
							role='student',
							program_or_dept=program,
							section_id=section.id,
							section=section_code  # Also set old field for compatibility
						)
						
						db.session.add(new_student)
						imported_count += 1
					
					except Exception as e:
						errors.append(f"Row {row_num}: {str(e)}")
						skipped_count += 1
				
				# Commit all changes
				db.session.commit()
		
		except Exception as e:
			db.session.rollback()
			return 0, 0, [f"Fatal error: {str(e)}"]
		
		return imported_count, skipped_count, errors
	
	@staticmethod
	def export_students_to_csv(output_path=None, role_filter='student', include_graduated=False):
		"""
		Export students to CSV file
		
		Args:
			output_path: Path to save CSV file (if None, creates in instance/exports/)
			role_filter: Filter by role ('student', 'faculty', 'staff', or None for all)
			include_graduated: Include graduated students
		
		Returns:
			tuple: (count, file_path)
		"""
		# Create export directory if needed
		if output_path is None:
			export_dir = os.path.join('instance', 'exports')
			os.makedirs(export_dir, exist_ok=True)
			timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
			output_path = os.path.join(export_dir, f'students_export_{timestamp}.csv')
		
		# Query persons
		query = Person.query
		if role_filter:
			query = query.filter_by(role=role_filter)
		
		persons = query.order_by(Person.full_name).all()
		
		# Filter out graduated students if needed
		if not include_graduated:
			persons = [p for p in persons if not p.is_graduated()]
		
		# Write to CSV
		with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
			fieldnames = ['first_name', 'last_name', 'full_name', 'section', 'program', 
						 'year_level', 'section_name', 'academic_year', 'is_graduated']
			writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
			
			writer.writeheader()
			for person in persons:
				# Get section info
				section_info = person.section_ref if person.section_ref else None
				
				writer.writerow({
					'first_name': person.get_first_name(),
					'last_name': person.get_last_name(),
					'full_name': person.full_name,
					'section': person.get_section_display(),
					'program': person.program_or_dept or 'N/A',
					'year_level': section_info.year_level if section_info else 'N/A',
					'section_name': section_info.section_name if section_info else 'N/A',
					'academic_year': section_info.academic_year if section_info else 'N/A',
					'is_graduated': 'Yes' if person.is_graduated() else 'No'
				})
		
		return len(persons), output_path
	
	@staticmethod
	def generate_csv_template(output_path=None):
		"""
		Generate a CSV template for student import
		
		Returns:
			str: Path to generated template
		"""
		if output_path is None:
			export_dir = os.path.join('instance', 'exports')
			os.makedirs(export_dir, exist_ok=True)
			output_path = os.path.join(export_dir, 'student_import_template.csv')
		
		# Create template with sample data
		with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
			fieldnames = ['first_name', 'last_name', 'section', 'program', 'year_level', 'section_name']
			writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
			
			writer.writeheader()
			# Add sample rows
			writer.writerow({
				'first_name': 'Juan',
				'last_name': 'Dela Cruz',
				'section': 'BSIT-3A',
				'program': 'BSIT',
				'year_level': '3rd Year',
				'section_name': 'A'
			})
			writer.writerow({
				'first_name': 'Maria',
				'last_name': 'Santos',
				'section': 'BSCS-2B',
				'program': 'BSCS',
				'year_level': '2nd Year',
				'section_name': 'B'
			})
		
		return output_path





