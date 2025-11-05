"""
ENHANCED OCR Service for Narrative Text Extraction
UNIQUE FEATURE: Extracts data from handwritten/narrative complaint letters

This is the competitive advantage - works with:
- Handwritten letters (after OCR)
- Narrative complaint stories
- Unstructured text
- Natural language descriptions
"""

import re
from typing import Dict, Optional, Tuple
from datetime import datetime


class NarrativeOCRService:
    """Enhanced OCR that understands narrative/natural language text"""
    
    @staticmethod
    def extract_student_name_from_narrative(text: str) -> Tuple[str, str, str]:
        """
        Extract student name from narrative text using context clues
        
        Returns: (first_name, last_name, full_name)
        """
        # ENHANCED: Look for names in context, not just keywords
        patterns = [
            # "full name is X" or "Name: X" patterns (most common in forms)
            r"(?:full\s+name|name)\s*[:=]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})",
            r"(?:full\s+name|name)\s+(?:is|was|ng estudyante ay)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})",
            
            # "student X" where X is a proper name (2-4 words, capitalized)
            r"(?:student|estudyante|mag-aaral)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})\s+(?:was|is|enrolled|from|ng|,)",
            
            # After action verbs (found, caught, saw, reported)
            r"(?:found|caught|saw|reported|witnessed)\s+(?:the\s+student\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})",
            
            # Filipino pattern "si X" or "kay X" or "ni X"
            r"(?:si|kay|ni)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})",
            
            # Before action verbs
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})\s+(?:admitted|confessed|was caught|violated|committed)",
            
            # In formal sentence structure
            r"(?:name|pangalan|ngalan)\s+(?:is|ay|:)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})",
            
            # Standalone capitalized names (2-4 words) at sentence start
            r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})\s+(?:from|of|in|at|enrolled|studying)",
            
            # After "regarding" or "concerning"
            r"(?:regarding|concerning|about)\s+(?:student\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})",
        ]
        
        # Common false positives to exclude
        false_positives = [
            'Information Technology', 'Science In', 'Bachelor Of', 'Category A',
            'Smoking Inside', 'The Student', 'A Student', 'From Section',
            'Section From', 'The Janitor', 'De La', 'Inside Campus'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                full_name = match.group(1).strip()
                
                # Clean up the name
                full_name = re.sub(r'\s+', ' ', full_name)  # Remove extra spaces
                
                # Skip if it's a false positive
                if any(fp.lower() in full_name.lower() for fp in false_positives):
                    continue
                
                # Must have at least 2 words (first + last name)
                name_parts = full_name.split()
                if len(name_parts) < 2:
                    continue
                
                # Must be all capitalized words (proper nouns)
                if not all(part[0].isupper() for part in name_parts if len(part) > 0):
                    continue
                
                # Extract first and last name
                # For Filipino names (e.g., Juan Miguel De La Cruz)
                # First name = first 1-2 words, Last name = rest
                if len(name_parts) == 2:
                    first_name = name_parts[0]
                    last_name = name_parts[1]
                elif len(name_parts) == 3:
                    # Check if middle word is "De", "Dela", "Del" (Filipino particles)
                    if name_parts[1].lower() in ['de', 'dela', 'del', 'san', 'santa']:
                        first_name = name_parts[0]
                        last_name = ' '.join(name_parts[1:])
                    else:
                        # Otherwise, first 2 = first name, last = last name
                        first_name = ' '.join(name_parts[:2])
                        last_name = name_parts[2]
                elif len(name_parts) >= 4:
                    # Long names: first 1-2 words = first name, rest = last name
                    # Check for particles
                    if any(part.lower() in ['de', 'dela', 'del', 'san', 'santa'] for part in name_parts[1:]):
                        first_name = name_parts[0]
                        last_name = ' '.join(name_parts[1:])
                    else:
                        first_name = ' '.join(name_parts[:2])
                        last_name = ' '.join(name_parts[2:])
                else:
                    continue
                
                return first_name, last_name, full_name
        
        return '', '', ''
    
    @staticmethod
    def extract_program_from_narrative(text: str) -> str:
        """Extract program/course from narrative text"""
        patterns = [
            # "enrolled in the Bachelor of Science..."
            r"(?:enrolled in|taking|pursuing|studying)\s+(?:the\s+)?(Bachelor\s+of\s+Science\s+in\s+[A-Za-z\s&()]+)",
            r"(?:enrolled in|taking|pursuing|studying)\s+(?:the\s+)?(Bachelor\s+of\s+Arts\s+in\s+[A-Za-z\s&()]+)",
            
            # "program: X" or "course: X"
            r"(?:program|course|kurso|programa)\s*[:is]?\s*([A-Za-z\s&()]+(?:Technology|Science|Arts|Education|Business|Engineering))",
            
            # Acronyms
            r"(BS[A-Z]{2,4}|BA[A-Z]{2,4})\s+(?:program|course)?",
            
            # Full degree names
            r"(Bachelor\s+of\s+Science\s+in\s+Information\s+Technology)",
            r"(Bachelor\s+of\s+Science\s+in\s+Computer\s+Science)",
            r"(Bachelor\s+of\s+Science\s+in\s+Business\s+Administration)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                program = match.group(1).strip()
                # Remove trailing words
                program = re.sub(r'\s+(program|course|student|enrolled).*$', '', program, flags=re.IGNORECASE)
                return program
        
        return ''
    
    @staticmethod
    def extract_section_from_narrative(text: str) -> str:
        """Extract section from narrative text"""
        patterns = [
            # "Section 2B" or "section 3A"
            r"(?:section|seksyon|class|klase)\s+([A-Z]?\d{1,2}[A-Z]?)",
            r"(?:section|seksyon|class|klase)\s*[:is]?\s*([0-9]{1,2}[A-Z]|[A-Z][0-9]{1,2})",
            
            # Just the section code alone (2B, 3A, etc.)
            r"\b([0-9][A-Z])\b",  # 2B, 3A
            r"\b([A-Z][0-9])\b",  # A2, B3
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                section = match.group(1).strip().upper()
                return section
        
        return ''
    
    @staticmethod
    def extract_date_from_narrative(text: str) -> str:
        """Extract date from narrative text"""
        patterns = [
            # "October 28, 2025" or "October 28 2025"
            r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})",
            
            # "28 October 2025"
            r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
            
            # "10/28/2025" or "2025-10-28"
            r"(\d{1,2}/\d{1,2}/\d{4})",
            r"(\d{4}-\d{1,2}-\d{1,2})",
            
            # Filipino months
            r"((?:Enero|Pebrero|Marso|Abril|Mayo|Hunyo|Hulyo|Agosto|Setyembre|Oktubre|Nobyembre|Disyembre)\s+\d{1,2},?\s+\d{4})",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                # Try to parse it
                try:
                    # Try different formats
                    for fmt in ['%B %d, %Y', '%B %d %Y', '%d %B %Y', '%m/%d/%Y', '%Y-%m-%d']:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            return parsed_date.strftime('%Y-%m-%d')
                        except:
                            continue
                except:
                    pass
                
                return date_str
        
        return ''
    
    @staticmethod
    def extract_offense_from_narrative(text: str) -> Tuple[str, str]:
        """
        Extract offense category and type from narrative text
        Returns: (category, specific_offense)
        """
        # Common offenses in narrative form
        offense_mapping = {
            'smoking': ('Category A', 'Smoking Inside Campus'),
            'cheating': ('Category A', 'Cheating/Academic Dishonesty'),
            'fighting': ('Category A', 'Physical Violence/Fighting'),
            'stealing': ('Category A', 'Theft/Stealing'),
            'vandalism': ('Category B', 'Vandalism/Destruction of Property'),
            'disrespect': ('Category B', 'Disrespectful Behavior'),
            'tardiness': ('Category C', 'Excessive Tardiness'),
            'absent': ('Category C', 'Excessive Absences'),
            'uniform': ('Category C', 'Uniform Violation'),
            'phone': ('Category C', 'Improper Use of Mobile Phone'),
            'bullying': ('Category A', 'Bullying/Harassment'),
            'intoxicated': ('Category A', 'Under the Influence of Alcohol'),
        }
        
        text_lower = text.lower()
        
        for keyword, (category, offense) in offense_mapping.items():
            if keyword in text_lower:
                return category, offense
        
        # If no match, try to extract from "Category A" pattern
        category_match = re.search(r"Category\s+([A-C])", text, re.IGNORECASE)
        offense_match = re.search(r"(?:offense|violation|incident)\s+(?:is|was|:)\s+([A-Za-z\s/]+)", text, re.IGNORECASE)
        
        category = f"Category {category_match.group(1)}" if category_match else ''
        specific_offense = offense_match.group(1).strip() if offense_match else ''
        
        return category, specific_offense
    
    @staticmethod
    def extract_all_from_narrative(text: str, entity_type: str = 'student') -> Dict[str, str]:
        """
        MAIN METHOD: Extract all fields from narrative complaint letter
        
        This is the UNIQUE FEATURE that sets WATCH apart from other systems!
        Works with handwritten/narrative complaint letters.
        """
        result = {
            'first_name': '',
            'last_name': '',
            'full_name': '',
            'program_or_dept': '',
            'section': '',
            'date': '',
            'offense_category': '',
            'offense_type': '',
            'description': text[:500]  # Keep full description
        }
        
        # Extract name (context-aware, avoid false positives)
        first_name, last_name, full_name = NarrativeOCRService.extract_student_name_from_narrative(text)
        result['first_name'] = first_name
        result['last_name'] = last_name
        result['full_name'] = full_name
        
        # Extract program (narrative-aware)
        result['program_or_dept'] = NarrativeOCRService.extract_program_from_narrative(text)
        
        # Extract section (narrative-aware)
        result['section'] = NarrativeOCRService.extract_section_from_narrative(text)
        
        # Extract date (narrative-aware)
        result['date'] = NarrativeOCRService.extract_date_from_narrative(text)
        
        # Extract offense (context-aware)
        category, specific_offense = NarrativeOCRService.extract_offense_from_narrative(text)
        result['offense_category'] = category
        result['offense_type'] = specific_offense
        
        return result
    
    @staticmethod
    def validate_extraction(result: Dict[str, str]) -> Tuple[bool, list]:
        """
        Validate extraction results and provide feedback
        Returns: (is_valid, warnings)
        """
        warnings = []
        
        if not result.get('first_name') or not result.get('last_name'):
            warnings.append("⚠️ Name not found. Please enter manually.")
        
        if not result.get('program_or_dept'):
            warnings.append("⚠️ Program/Department not found. Please enter manually.")
        
        if not result.get('section') and 'student' in str(result.get('entity_type', '')).lower():
            warnings.append("⚠️ Section not found. Please enter manually.")
        
        if not result.get('date'):
            warnings.append("⚠️ Date not found. Please enter manually.")
        
        if not result.get('offense_type'):
            warnings.append("⚠️ Offense not found. Please select manually.")
        
        is_valid = len(warnings) == 0
        
        return is_valid, warnings

