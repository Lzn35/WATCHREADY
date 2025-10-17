#!/usr/bin/env python3
"""
OCR Service for extracting information from complaint letters
Supports English, Tagalog, and Taglish formats
"""

import re
import json
from typing import Dict, Optional, List, Tuple
from datetime import datetime, date

class OCRService:
    """Service for extracting structured data from complaint letters using OCR text"""
    
    # Common complaint templates and patterns
    COMPLAINT_PATTERNS = {
        'student_info': {
            'name_patterns': [
                r'(?:student|pupil|learner|mag-aaral|estudyante)\s*:?\s*([A-Za-z\s,\.]+)',
                r'(?:name|pangalan|ngalan)\s*:?\s*([A-Za-z\s,\.]+)',
                r'(?:last name|apelyido|surname)\s*:?\s*([A-Za-z\s,\.]+)',
                r'(?:first name|unang pangalan|given name)\s*:?\s*([A-Za-z\s,\.]+)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)',  # Simple name pattern
            ],
            'program_patterns': [
                r'(?:program|course|kurso|programa)\s*:?\s*([A-Za-z\s&()]+)',
                r'(?:major|specialization|espesyalisasyon)\s*:?\s*([A-Za-z\s&()]+)',
                r'(?:degree|antas|bachelor|master)\s*:?\s*([A-Za-z\s&()]+)',
                r'(?:BS|BA|BSCS|BSIT|BEED|BSTM|BSBA|BSPA|BSCE|BSEE|BSME)\s*([A-Za-z\s&()]*)',
                r'(?:ICT|IT|CS|Engineering|Business|Education|Tourism|Psychology|Criminology)',
            ],
            'section_patterns': [
                r'(?:section|seksyon|klase|class)\s*:?\s*([A-Za-z0-9\s]+)',
                r'(?:group|grupo|batch|batch)\s*:?\s*([A-Za-z0-9\s]+)',
                r'(?:year level|taong antas|grade level)\s*:?\s*([A-Za-z0-9\s]+)',
                r'(?:1st|2nd|3rd|4th|first|second|third|fourth)\s+year\s*([A-Za-z0-9]*)',
                r'([A-Z][0-9]{1,2})',  # Simple section pattern like A1, B2
                r'([0-9]{1,2}[A-Z])',  # Simple section pattern like 1A, 2B
            ]
        },
        'faculty_info': {
            'name_patterns': [
                r'(?:faculty|instructor|teacher|professor|guro|tagapagturo)\s*:?\s*([A-Za-z\s,\.]+)',
                r'(?:name|pangalan|ngalan)\s*:?\s*([A-Za-z\s,\.]+)',
                r'(?:last name|apelyido|surname)\s*:?\s*([A-Za-z\s,\.]+)',
                r'(?:first name|unang pangalan|given name)\s*:?\s*([A-Za-z\s,\.]+)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)',  # Simple name pattern
            ],
            'department_patterns': [
                r'(?:department|kagawaran|departamento)\s*:?\s*([A-Za-z\s&()]+)',
                r'(?:college|kolehiyo|school|paaralan)\s*:?\s*([A-Za-z\s&()]+)',
                r'(?:division|dibisyon|unit|yunit)\s*:?\s*([A-Za-z\s&()]+)',
                r'(?:ICT|Information Communications Technology|IT|Information Technology)',
                r'(?:GE|General Education|Gen Ed)',
                r'(?:BM|Business Management|Business)',
                r'(?:Engineering|Civil Engineering|Mechanical Engineering|Electrical Engineering)',
                r'(?:Education|Teacher Education|BEED|BSEd)',
                r'(?:Tourism|Hospitality|TSTM)',
                r'(?:Psychology|Criminology|Social Work)',
            ]
        },
        'staff_info': {
            'name_patterns': [
                r'(?:staff|employee|kawani|empleyado)\s*:?\s*([A-Za-z\s,\.]+)',
                r'(?:name|pangalan|ngalan)\s*:?\s*([A-Za-z\s,\.]+)',
                r'(?:last name|apelyido|surname)\s*:?\s*([A-Za-z\s,\.]+)',
                r'(?:first name|unang pangalan|given name)\s*:?\s*([A-Za-z\s,\.]+)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)',  # Simple name pattern
            ],
            'position_patterns': [
                r'(?:position|posisyon|tungkulin|role|papel)\s*:?\s*([A-Za-z\s&()]+)',
                r'(?:job title|pamagat ng trabaho|designation|tawag)\s*:?\s*([A-Za-z\s&()]+)',
                r'(?:secretary|sekretarya|clerk|klerk)',
                r'(?:admin|administrator|administrador)',
                r'(?:guard|bantay|security|seguridad)',
                r'(?:maintenance|pagpapanatili|utility|utilidad)',
                r'(?:librarian|tagapangasiwa ng aklatan)',
                r'(?:cashier|taga-ingat ng pera|bookkeeper|taga-ingat ng libro)',
                r'(?:registrar|tagatala|records keeper|taga-ingat ng talaan)',
                r'(?:IT support|suporta sa IT|technical support)',
                r'(?:janitor|tagalinis|cleaner|tagapaglinis)',
                r'(?:driver|tsuper|chauffeur)',
            ]
        },
        'offense_info': {
            'category_patterns': [
                r'(?:category|kategorya|klase|type)\s*:?\s*([A-D])',
                r'(?:offense category|kategorya ng kaso)\s*:?\s*([A-D])',
                r'(?:violation type|uri ng paglabag)\s*:?\s*([A-D])',
                r'(?:case type|uri ng kaso)\s*:?\s*([A-D])',
                r'Category\s+([A-D])',
                r'Kategorya\s+([A-D])',
            ],
            'specific_offense_patterns': [
                # Category A offenses
                r'(?:repeated minor offense|paulit-ulit na menor na paglabag)',
                r'(?:tampered or borrowed id|napinsala o hiniram na id)',
                r'(?:smoking inside campus|paninigarilyo sa loob ng campus)',
                r'(?:intoxication or liquor|pagkalasing o alak)',
                r'(?:unauthorized entry|hindi awtorisadong pagpasok)',
                r'(?:cheating|pandadaya)',
                
                # Category B offenses
                r'(?:vandalism|pagsira ng ari-arian)',
                r'(?:disrespectful online post|hindi magalang na online na post)',
                r'(?:privacy violation|paglabag sa privacy)',
                r'(?:ill repute places|lugaring may masamang reputasyon)',
                r'(?:false testimony|maling patotoo)',
                r'(?:grave insult|malubhang insulto)',
                
                # Category C offenses
                r'(?:hacking|paghack)',
                r'(?:forgery|pagpeke)',
                r'(?:theft|pagnanakaw)',
                r'(?:unauthorized material use|hindi awtorisadong paggamit ng materyal)',
                r'(?:embezzlement|pagnanakaw ng pondo)',
                r'(?:illegal assembly|hindi legal na pagpupulong)',
                r'(?:immorality|kawalang moralidad)',
                r'(?:bullying|pang-aapi)',
                r'(?:brawling|awayan)',
                r'(?:physical assault|pisikal na pag-atake)',
                r'(?:drug use|pagkonsumo ng droga)',
                r'(?:false alarm|maling alarma)',
                r'(?:fire equipment misuse|maling paggamit ng kagamitang pang-apoy)',
                
                # Category D offenses
                r'(?:drug possession|pagkakaroon ng droga)',
                r'(?:repeat drug use|paulit-ulit na pagkonsumo ng droga)',
                r'(?:possession of firearm|pagkakaroon ng baril)',
                r'(?:illegal fraternity|hindi legal na praternidad)',
                r'(?:hazing|hazing)',
                r'(?:crime involving morality|krimen na may kinalaman sa moralidad)',
                r'(?:sexual harassment|pang-aabuso sa sekswal)',
                r'(?:subversion or sedition|subversion o sedisyon)',
            ],
            'description_patterns': [
                r'(?:description|deskripsyon|paglalarawan)\s*:?\s*(.+?)(?:\n|$)',
                r'(?:details|mga detalye|particulars)\s*:?\s*(.+?)(?:\n|$)',
                r'(?:incident|pangyayari|event)\s*:?\s*(.+?)(?:\n|$)',
                r'(?:what happened|ano ang nangyari|nangyari)\s*:?\s*(.+?)(?:\n|$)',
                r'(?:narration|salaysay|story)\s*:?\s*(.+?)(?:\n|$)',
                r'(?:account|ulat|report)\s*:?\s*(.+?)(?:\n|$)',
                r'(?:complaint|reklamo|sumbong)\s*:?\s*(.+?)(?:\n|$)',
                r'(?:allegation|akusasyon|paratang)\s*:?\s*(.+?)(?:\n|$)',
            ]
        }
    }
    
    # Mapping for specific offenses to categories
    OFFENSE_CATEGORY_MAP = {
        # Category A
        'repeated minor offense': 'A',
        'tampered or borrowed id': 'A',
        'smoking inside campus': 'A',
        'intoxication or liquor': 'A',
        'unauthorized entry': 'A',
        'cheating': 'A',
        
        # Category B
        'vandalism': 'B',
        'disrespectful online post': 'B',
        'privacy violation': 'B',
        'ill repute places': 'B',
        'false testimony': 'B',
        'grave insult': 'B',
        
        # Category C
        'hacking': 'C',
        'forgery': 'C',
        'theft': 'C',
        'unauthorized material use': 'C',
        'embezzlement': 'C',
        'illegal assembly': 'C',
        'immorality': 'C',
        'bullying': 'C',
        'brawling': 'C',
        'physical assault': 'C',
        'drug use': 'C',
        'false alarm': 'C',
        'fire equipment misuse': 'C',
        
        # Category D
        'drug possession': 'D',
        'repeat drug use': 'D',
        'possession of firearm': 'D',
        'illegal fraternity': 'D',
        'hazing': 'D',
        'crime involving morality': 'D',
        'sexual harassment': 'D',
        'subversion or sedition': 'D',
    }
    
    @classmethod
    def extract_student_info(cls, text: str) -> Dict[str, Optional[str]]:
        """Extract student information from complaint text"""
        result = {
            'last_name': None,
            'first_name': None,
            'program': None,
            'section': None
        }
        
        # Clean and normalize text
        text = cls._clean_text(text)
        
        # Extract name
        name_info = cls._extract_name(text)
        if name_info:
            result['first_name'] = name_info.get('first_name')
            result['last_name'] = name_info.get('last_name')
        
        # Extract program
        result['program'] = cls._extract_program(text)
        
        # Extract section
        result['section'] = cls._extract_section(text)
        
        return result
    
    @classmethod
    def extract_faculty_info(cls, text: str) -> Dict[str, Optional[str]]:
        """Extract faculty information from complaint text"""
        result = {
            'last_name': None,
            'first_name': None,
            'department': None
        }
        
        # Clean and normalize text
        text = cls._clean_text(text)
        
        # Extract name using faculty patterns
        name_info = cls._extract_name_faculty(text)
        if name_info:
            result['first_name'] = name_info.get('first_name')
            result['last_name'] = name_info.get('last_name')
        
        # Extract department
        result['department'] = cls._extract_department(text)
        
        return result
    
    @classmethod
    def extract_staff_info(cls, text: str) -> Dict[str, Optional[str]]:
        """Extract staff information from complaint text"""
        result = {
            'last_name': None,
            'first_name': None,
            'position': None
        }
        
        # Clean and normalize text
        text = cls._clean_text(text)
        
        # Extract name using staff patterns
        name_info = cls._extract_name_staff(text)
        if name_info:
            result['first_name'] = name_info.get('first_name')
            result['last_name'] = name_info.get('last_name')
        
        # Extract position
        result['position'] = cls._extract_position(text)
        
        return result
    
    @classmethod
    def extract_offense_info(cls, text: str) -> Dict[str, Optional[str]]:
        """Extract offense information from complaint text"""
        result = {
            'category': None,
            'specific_offense': None,
            'description': None
        }
        
        # Clean and normalize text
        text = cls._clean_text(text)
        
        # Extract category
        result['category'] = cls._extract_category(text)
        
        # Extract specific offense
        result['specific_offense'] = cls._extract_specific_offense(text)
        
        # Extract description
        result['description'] = cls._extract_description(text)
        
        # If category is not found but specific offense is, map it
        if not result['category'] and result['specific_offense']:
            result['category'] = cls._map_offense_to_category(result['specific_offense'])
        
        return result
    
    @classmethod
    def extract_all_info(cls, text: str, entity_type: str = 'student') -> Dict[str, any]:
        """Extract all information from complaint text"""
        # Extract offense information (same for all entity types)
        offense_info = cls.extract_offense_info(text)
        
        # Extract entity-specific information
        if entity_type == 'faculty':
            entity_info = cls.extract_faculty_info(text)
        elif entity_type == 'staff':
            entity_info = cls.extract_staff_info(text)
        else:  # default to student
            entity_info = cls.extract_student_info(text)
        
        return {
            **entity_info,
            **offense_info,
            'extraction_confidence': cls._calculate_confidence(entity_info, offense_info),
            'extracted_at': datetime.now().isoformat()
        }
    
    @classmethod
    def _clean_text(cls, text: str) -> str:
        """Clean and normalize text for better pattern matching"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove special characters that might interfere
        text = re.sub(r'[^\w\s.,:;!?()-]', ' ', text)
        
        # Normalize common variations
        text = text.replace('&', 'and')
        
        return text
    
    @classmethod
    def _extract_name(cls, text: str) -> Optional[Dict[str, str]]:
        """Extract first and last name from text"""
        for pattern in cls.COMPLAINT_PATTERNS['student_info']['name_patterns']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                name_text = match.group(1).strip()
                if name_text and len(name_text) > 3:
                    # Try to split into first and last name
                    name_parts = name_text.split()
                    if len(name_parts) >= 2:
                        return {
                            'first_name': name_parts[0].strip(),
                            'last_name': name_parts[-1].strip()
                        }
                    elif len(name_parts) == 1:
                        return {
                            'first_name': name_parts[0].strip(),
                            'last_name': ''
                        }
        return None
    
    @classmethod
    def _extract_name_faculty(cls, text: str) -> Optional[Dict[str, str]]:
        """Extract first and last name from text for faculty"""
        for pattern in cls.COMPLAINT_PATTERNS['faculty_info']['name_patterns']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                name_text = match.group(1).strip()
                if name_text and len(name_text) > 3:
                    # Try to split into first and last name
                    name_parts = name_text.split()
                    if len(name_parts) >= 2:
                        return {
                            'first_name': name_parts[0].strip(),
                            'last_name': name_parts[-1].strip()
                        }
                    elif len(name_parts) == 1:
                        return {
                            'first_name': name_parts[0].strip(),
                            'last_name': ''
                        }
        return None
    
    @classmethod
    def _extract_name_staff(cls, text: str) -> Optional[Dict[str, str]]:
        """Extract first and last name from text for staff"""
        for pattern in cls.COMPLAINT_PATTERNS['staff_info']['name_patterns']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                name_text = match.group(1).strip()
                if name_text and len(name_text) > 3:
                    # Try to split into first and last name
                    name_parts = name_text.split()
                    if len(name_parts) >= 2:
                        return {
                            'first_name': name_parts[0].strip(),
                            'last_name': name_parts[-1].strip()
                        }
                    elif len(name_parts) == 1:
                        return {
                            'first_name': name_parts[0].strip(),
                            'last_name': ''
                        }
        return None
    
    @classmethod
    def _extract_program(cls, text: str) -> Optional[str]:
        """Extract program/course from text"""
        for pattern in cls.COMPLAINT_PATTERNS['student_info']['program_patterns']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                program = match.group(1).strip()
                if program and len(program) > 2:
                    # Clean up the program name
                    program = re.sub(r'\s+', ' ', program)
                    return program.title()
        return None
    
    @classmethod
    def _extract_section(cls, text: str) -> Optional[str]:
        """Extract section from text"""
        for pattern in cls.COMPLAINT_PATTERNS['student_info']['section_patterns']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                section = match.group(1).strip()
                if section and len(section) <= 10:  # Reasonable section length
                    return section.upper()
        return None
    
    @classmethod
    def _extract_department(cls, text: str) -> Optional[str]:
        """Extract department from text for faculty"""
        for pattern in cls.COMPLAINT_PATTERNS['faculty_info']['department_patterns']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                department = match.group(1).strip()
                if department and len(department) > 2:
                    # Clean up the department name
                    department = re.sub(r'\s+', ' ', department)
                    
                    # Map to standard department names
                    department_lower = department.lower()
                    if 'ict' in department_lower or 'information technology' in department_lower:
                        return 'Information Communications Technology (ICT)'
                    elif 'ge' in department_lower or 'general education' in department_lower:
                        return 'General Education (GE)'
                    elif 'bm' in department_lower or 'business' in department_lower:
                        return 'Business Management (BM)'
                    else:
                        return department.title()
        return None
    
    @classmethod
    def _extract_position(cls, text: str) -> Optional[str]:
        """Extract position from text for staff"""
        for pattern in cls.COMPLAINT_PATTERNS['staff_info']['position_patterns']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                position = match.group(1).strip()
                if position and len(position) > 2:
                    # Clean up the position name
                    position = re.sub(r'\s+', ' ', position)
                    return position.title()
        return None
    
    @classmethod
    def _extract_category(cls, text: str) -> Optional[str]:
        """Extract offense category from text"""
        for pattern in cls.COMPLAINT_PATTERNS['offense_info']['category_patterns']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                category = match.group(1).strip().upper()
                if category in ['A', 'B', 'C', 'D']:
                    return category
        return None
    
    @classmethod
    def _extract_specific_offense(cls, text: str) -> Optional[str]:
        """Extract specific offense from text"""
        text_lower = text.lower()
        
        # Check for each specific offense
        for offense, category in cls.OFFENSE_CATEGORY_MAP.items():
            if offense in text_lower:
                return offense.title()
        
        # If no specific offense found, try to extract from patterns
        for pattern in cls.COMPLAINT_PATTERNS['offense_info']['specific_offense_patterns']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                offense = match.group(0).strip()
                if offense:
                    return offense.title()
        return None
    
    @classmethod
    def _extract_description(cls, text: str) -> Optional[str]:
        """Extract description from text"""
        for pattern in cls.COMPLAINT_PATTERNS['offense_info']['description_patterns']:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                description = match.group(1).strip()
                if description and len(description) > 10:
                    # Clean up description
                    description = re.sub(r'\s+', ' ', description)
                    return description[:500]  # Limit length
        return None
    
    @classmethod
    def _map_offense_to_category(cls, offense: str) -> Optional[str]:
        """Map specific offense to category"""
        offense_lower = offense.lower()
        return cls.OFFENSE_CATEGORY_MAP.get(offense_lower)
    
    @classmethod
    def _calculate_confidence(cls, student_info: Dict, offense_info: Dict) -> float:
        """Calculate confidence score for extraction"""
        confidence = 0.0
        total_fields = 6
        
        # Student info fields
        if student_info.get('first_name'):
            confidence += 1.0
        if student_info.get('last_name'):
            confidence += 1.0
        if student_info.get('program'):
            confidence += 1.0
        if student_info.get('section'):
            confidence += 1.0
        
        # Offense info fields
        if offense_info.get('category'):
            confidence += 1.0
        if offense_info.get('specific_offense'):
            confidence += 1.0
        
        return round(confidence / total_fields, 2)
    
    @classmethod
    def validate_extraction(cls, extracted_data: Dict) -> Tuple[bool, List[str]]:
        """Validate extracted data and return validation results"""
        errors = []
        
        # Check required fields
        if not extracted_data.get('first_name'):
            errors.append("First name not found")
        if not extracted_data.get('last_name'):
            errors.append("Last name not found")
        if not extracted_data.get('program'):
            errors.append("Program not found")
        if not extracted_data.get('section'):
            errors.append("Section not found")
        if not extracted_data.get('category'):
            errors.append("Offense category not found")
        if not extracted_data.get('specific_offense'):
            errors.append("Specific offense not found")
        
        # Check confidence score
        confidence = extracted_data.get('extraction_confidence', 0)
        if confidence < 0.5:
            errors.append(f"Low confidence score: {confidence}")
        
        return len(errors) == 0, errors
