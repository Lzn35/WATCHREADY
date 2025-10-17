import re
from typing import Dict, List, Tuple

class CaseDetector:
    """Detects and highlights case types in disciplinary descriptions"""
    
    def __init__(self):
        # Define case type patterns with keywords and their severity
        self.case_patterns = {
            'academic_dishonesty': {
                'keywords': ['cheating', 'plagiarism', 'copying', 'crib notes', 'unauthorized materials', 'exam violation', 'academic fraud'],
                'icon': '',
                'severity': 'high',
                'color': '#dc3545'  # Red
            },
            'physical_altercation': {
                'keywords': ['fight', 'fighting', 'physical', 'assault', 'violence', 'punch', 'hit', 'strike', 'attack'],
                'icon': '',
                'severity': 'high',
                'color': '#dc3545'  # Red
            },
            'theft': {
                'keywords': ['steal', 'stealing', 'theft', 'stolen', 'robbery', 'burglary', 'taking without permission'],
                'icon': '',
                'severity': 'high',
                'color': '#dc3545'  # Red
            },
            'vandalism': {
                'keywords': ['vandalism', 'vandalizing', 'graffiti', 'damage', 'destruction', 'defacing', 'property damage'],
                'icon': '',
                'severity': 'medium',
                'color': '#fd7e14'  # Orange
            },
            'disrespectful_behavior': {
                'keywords': ['disrespectful', 'rude', 'inappropriate language', 'profanity', 'cursing', 'defiant', 'insolent'],
                'icon': '',
                'severity': 'medium',
                'color': '#fd7e14'  # Orange
            },
            'substance_abuse': {
                'keywords': ['smoking', 'drinking', 'alcohol', 'drugs', 'intoxicated', 'substance', 'illegal substances'],
                'icon': '',
                'severity': 'high',
                'color': '#dc3545'  # Red
            },
            'technology_misuse': {
                'keywords': ['phone', 'mobile', 'device', 'unauthorized use', 'technology', 'gadget', 'electronic'],
                'icon': '',
                'severity': 'low',
                'color': '#ffc107'  # Yellow
            },
            'attendance_violation': {
                'keywords': ['absent', 'tardiness', 'late', 'skipping', 'truancy', 'attendance', 'cutting class'],
                'icon': '',
                'severity': 'low',
                'color': '#ffc107'  # Yellow
            },
            'dress_code_violation': {
                'keywords': ['dress code', 'inappropriate clothing', 'uniform', 'attire', 'clothing violation'],
                'icon': '',
                'severity': 'low',
                'color': '#ffc107'  # Yellow
            },
            'disruption': {
                'keywords': ['disrupting', 'disturbing', 'noise', 'talking', 'interrupting', 'classroom disruption'],
                'icon': '',
                'severity': 'low',
                'color': '#ffc107'  # Yellow
            }
        }
    
    def detect_case_type(self, description: str) -> Dict:
        """
        Analyze description and detect case type with highlighting
        
        Args:
            description: The incident description text
            
        Returns:
            Dict containing case analysis with highlighting
        """
        if not description or not description.strip():
            return {
                'case_type': 'unknown',
                'confidence': 0.0,
                'detected_keywords': [],
                'highlighted_text': description,
                'icon': '[?]',
                'severity': 'unknown',
                'color': '#6c757d'
            }
        
        description_lower = description.lower()
        detected_cases = []
        highlighted_text = description
        
        # Check each case pattern
        for case_type, pattern_info in self.case_patterns.items():
            keywords_found = []
            confidence = 0.0
            
            for keyword in pattern_info['keywords']:
                if keyword.lower() in description_lower:
                    keywords_found.append(keyword)
                    confidence += 1.0
            
            if keywords_found:
                # Calculate confidence based on keyword matches
                confidence = min(confidence / len(pattern_info['keywords']), 1.0)
                detected_cases.append({
                    'case_type': case_type,
                    'confidence': confidence,
                    'keywords': keywords_found,
                    'icon': pattern_info['icon'],
                    'severity': pattern_info['severity'],
                    'color': pattern_info['color']
                })
        
        if not detected_cases:
            return {
                'case_type': 'general_violation',
                'confidence': 0.1,
                'detected_keywords': [],
                'highlighted_text': description,
                'icon': '[WARNING]',
                'severity': 'unknown',
                'color': '#6c757d'
            }
        
        # Get the case with highest confidence
        best_case = max(detected_cases, key=lambda x: x['confidence'])
        
        # Create highlighted text
        highlighted_text = self._highlight_keywords(description, best_case['keywords'], best_case['color'])
        
        return {
            'case_type': best_case['case_type'],
            'confidence': best_case['confidence'],
            'detected_keywords': best_case['keywords'],
            'highlighted_text': highlighted_text,
            'icon': best_case['icon'],
            'severity': best_case['severity'],
            'color': best_case['color'],
            'all_detected_cases': detected_cases
        }
    
    def _highlight_keywords(self, text: str, keywords: List[str], color: str) -> str:
        """
        Highlight keywords in the text with HTML spans
        
        Args:
            text: Original text
            keywords: List of keywords to highlight
            color: Color for highlighting
            
        Returns:
            HTML string with highlighted keywords
        """
        highlighted_text = text
        
        for keyword in keywords:
            # Create case-insensitive regex pattern
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            
            # Replace with highlighted version
            highlighted_text = pattern.sub(
                f'<span style="background-color: {color}; color: white; padding: 2px 4px; border-radius: 3px; font-weight: bold;">{keyword}</span>',
                highlighted_text
            )
        
        return highlighted_text
    
    def get_case_type_display_name(self, case_type: str) -> str:
        """Convert case_type to display name"""
        display_names = {
            'academic_dishonesty': 'Academic Dishonesty',
            'physical_altercation': 'Physical Altercation',
            'theft': 'Theft',
            'vandalism': 'Vandalism',
            'disrespectful_behavior': 'Disrespectful Behavior',
            'substance_abuse': 'Substance Abuse',
            'technology_misuse': 'Technology Misuse',
            'attendance_violation': 'Attendance Violation',
            'dress_code_violation': 'Dress Code Violation',
            'disruption': 'Classroom Disruption',
            'general_violation': 'General Violation',
            'unknown': 'Unknown'
        }
        return display_names.get(case_type, case_type.replace('_', ' ').title())

# Create global instance
case_detector = CaseDetector()
