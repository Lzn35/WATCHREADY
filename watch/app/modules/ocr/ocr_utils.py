import os
import re
import json
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from dotenv import load_dotenv

load_dotenv()

# Configure Tesseract path if provided
tess_path = os.getenv("TESSERACT_PATH")
if tess_path:
    pytesseract.pytesseract.tesseract_cmd = tess_path

# Load offense list
def load_offense_list():
    offense_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "offense_list.json")
    with open(offense_file, "r", encoding="utf-8") as f:
        return json.load(f)

OFFENSE_LIST = load_offense_list()

# OCR: extract text from image or pdf
def extract_text_from_file(file_path):
    """
    Extract text from image or PDF using Tesseract OCR.
    
    Raises:
        RuntimeError: If Tesseract is not installed
    """
    # Check if Tesseract is available
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        raise RuntimeError(
            "Tesseract OCR is not installed or not in PATH. "
            "Please install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki"
        )
    
    ext = os.path.splitext(file_path)[1].lower()
    text_output = ""

    # If PDF, convert to images first
    if ext == ".pdf":
        try:
            pages = convert_from_path(file_path, dpi=300)
            for page in pages:
                text_output += pytesseract.image_to_string(page)
        except Exception as e:
            raise RuntimeError(f"Failed to process PDF: {str(e)}")
    else:
        try:
            img = Image.open(file_path)
            img = img.convert("L")  # grayscale
            text_output = pytesseract.image_to_string(img)
        except Exception as e:
            raise RuntimeError(f"Failed to process image: {str(e)}")

    return text_output

# Extract specific fields (Last Name, First Name, etc.)
def extract_fields_from_text(text):
    """
    Extract fields from both template and narrative formats.
    Template: "Last Name: DE LA CRUZ"
    Narrative: "student Juan Miguel De La Cruz from BSIT 3A"
    """
    fields = {}
    
    # Try template patterns first
    template_patterns = {
        "last_name": r"Last\s*Name[:\-]?\s*([^\n\r]+)",
        "first_name": r"First\s*Name[:\-]?\s*([^\n\r]+)",
        "program": r"Program[:\-]?\s*([^\n\r]+)",
        "section": r"Section[:\-]?\s*([^\n\r]+)",
        "date": r"Date[:\-]?\s*([^\n\r]+)",
        "description": r"Description[:\-]?\s*([\s\S]*?)(?=\n\n|\Z)"
    }
    
    for key, pattern in template_patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        fields[key] = match.group(1).strip() if match else ""
    
    # If template fields not found, try narrative extraction
    if not fields.get("first_name") and not fields.get("last_name"):
        # Try to get full name from narrative
        # More precise patterns with word boundaries
        name_patterns = [
            # "Faculty Member Michael Ramos, instructor" - with comma
            r"(?:Faculty\s+Member|Staff\s+Member)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s*,)",
            # "student Juan Miguel De La Cruz from BSIT" - handles multi-word last names
            r"(?:student)\s+([A-Z][a-z]+(?:\s+(?:De|Dela|Del|Da|Di|Van|Von)\s+)?(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*))\s+from",
            # "staff member Carlo Mendoza from" - simple names
            r"(?:staff\s+member|employee)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)\s+from",
            # "instructor [Name]" - for faculty without "member"
            r"(?:instructor)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s+from|\s*,)",
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, text, re.IGNORECASE)
            if name_match:
                full_name = name_match.group(1).strip()
                # Remove any trailing words like "from", "was", etc.
                full_name = re.sub(r'\s+(from|was|were|,)\s*$', '', full_name, flags=re.IGNORECASE).strip()
                
                # Handle Filipino compound last names (De La Cruz, Dela Cruz, etc.)
                name_parts = full_name.split()
                if len(name_parts) >= 3 and name_parts[-3].lower() in ['de', 'dela', 'del', 'van', 'von']:
                    # Last 3 words are the last name (e.g., "De La Cruz")
                    fields["last_name"] = " ".join(name_parts[-3:])
                    fields["first_name"] = " ".join(name_parts[:-3])
                elif len(name_parts) >= 2 and name_parts[-2].lower() in ['de', 'dela', 'del', 'van', 'von']:
                    # Last 2 words are the last name (e.g., "Del Rosario")
                    fields["last_name"] = " ".join(name_parts[-2:])
                    fields["first_name"] = " ".join(name_parts[:-2])
                elif len(name_parts) >= 2:
                    # Standard: last word is last name
                    fields["last_name"] = name_parts[-1]
                    fields["first_name"] = " ".join(name_parts[:-1])
                break
    
    # Extract program/department from narrative  
    if not fields.get("program"):
        # Pattern: "from [Program/Department]"
        program_patterns = [
            # "instructor from the BSBA Department" - capture BSBA
            r"from\s+(?:the\s+)?(BS[A-Z]{2,4})\s+Department",
            # "from BSIT 3A" or "from BSIT"
            r"from\s+(BS[A-Z]{2,4})\b",
            # "from the Maintenance Department" - capture Maintenance
            r"from\s+(?:the\s+)?([A-Z][a-z]+)\s+Department\b",
            # Generic department mention
            r"(?:program|course|department)[:\-]?\s*([A-Z][A-Z]+)\b",  # BSIT, BSBA in caps
        ]
        for pattern in program_patterns:
            prog_match = re.search(pattern, text, re.IGNORECASE)
            if prog_match:
                prog = prog_match.group(1).strip()
                if prog and len(prog) >= 2:  # At least 2 characters
                    fields["program"] = prog
                    break
    
    # Extract section from narrative
    if not fields.get("section"):
        # Pattern: "3A", "CS-401", "Section 3A"
        section_patterns = [
            r"\b([A-Z]{2,4}[-\s]?\d{1,3}[A-Z]?)\b",  # BSIT-3A, CS-401, 3A
            r"Section[:\-]?\s*([^\n\r,]+)",
        ]
        for pattern in section_patterns:
            sec_match = re.search(pattern, text)
            if sec_match:
                fields["section"] = sec_match.group(1).strip()
                break
    
    # Extract date from narrative
    if not fields.get("date"):
        # Pattern: "October 7, 2025", "Oct 7, 2025", "10/7/2025"
        date_patterns = [
            r"(?:on\s+)?([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",  # October 7, 2025
            r"(?:on\s+)?(\d{1,2}/\d{1,2}/\d{4})",  # 10/7/2025
            r"(?:on\s+)?(\d{4}-\d{2}-\d{2})",  # 2025-10-07
        ]
        for pattern in date_patterns:
            date_match = re.search(pattern, text, re.IGNORECASE)
            if date_match:
                fields["date"] = date_match.group(1).strip()
                break
    
    # If no specific description field, use the main body of text
    if not fields.get("description"):
        # Get everything after the header/title
        lines = text.split('\n')
        # Skip first 2-3 lines (usually headers)
        body_lines = []
        skip_count = 0
        for line in lines:
            line = line.strip()
            if line and not any(header in line.upper() for header in ['REPORT', 'MEMO', 'INCIDENT', 'COMPLAINT FORM', 'DISCIPLINARY']):
                if skip_count >= 1:  # Start capturing after first non-header line
                    body_lines.append(line)
                else:
                    skip_count += 1
            elif line and any(header in line.upper() for header in ['REPORT', 'MEMO', 'INCIDENT']):
                skip_count = 0  # Reset if we hit another header
        
        if body_lines:
            fields["description"] = " ".join(body_lines)
        else:
            # Use full text as description if nothing else found
            fields["description"] = text.strip()
    
    return fields

# Detect offense in description using both regex and keywords
def detect_offense_from_text(description):
    text_upper = description.upper()
    detected_offenses = []
    
    for code, info in OFFENSE_LIST.items():
        matched = False
        match_method = None
        matched_text = None
        
        # Try regex pattern first (more accurate)
        if "regex" in info:
            pattern = info["regex"]
            regex_match = re.search(pattern, text_upper, re.IGNORECASE)
            if regex_match:
                matched = True
                match_method = "regex"
                matched_text = regex_match.group(0)
        
        # Fall back to keyword matching if no regex or no match
        if not matched:
            for kw in info.get("keywords", []):
                if kw in text_upper:
                    matched = True
                    match_method = "keyword"
                    matched_text = kw
                    break
        
        # Add to detected offenses if matched
        if matched:
            detected_offenses.append({
                "code": code,
                "label": info["label"],
                "category": info["category"],
                "severity": info["severity"],
                "match_method": match_method,
                "matched_text": matched_text
            })
    
    # Return the highest severity offense, or UNKNOWN if none found
    if detected_offenses:
        # Sort by severity (highest first)
        detected_offenses.sort(key=lambda x: x["severity"], reverse=True)
        return detected_offenses[0]
    
    return {"code": "UNKNOWN", "label": "Unclassified", "category": "N/A", "severity": 0}

# Get all detected offenses (for comprehensive analysis)
def detect_all_offenses_from_text(description):
    text_upper = description.upper()
    detected_offenses = []
    
    for code, info in OFFENSE_LIST.items():
        matched = False
        match_method = None
        matched_text = None
        
        # Try regex pattern first (more accurate)
        if "regex" in info:
            pattern = info["regex"]
            regex_match = re.search(pattern, text_upper, re.IGNORECASE)
            if regex_match:
                matched = True
                match_method = "regex"
                matched_text = regex_match.group(0)
        
        # Fall back to keyword matching if no regex or no match
        if not matched:
            for kw in info.get("keywords", []):
                if kw in text_upper:
                    matched = True
                    match_method = "keyword"
                    matched_text = kw
                    break
        
        # Add to detected offenses if matched
        if matched:
            detected_offenses.append({
                "code": code,
                "label": info["label"],
                "category": info["category"],
                "severity": info["severity"],
                "match_method": match_method,
                "matched_text": matched_text
            })
    
    # Sort by severity (highest first)
    detected_offenses.sort(key=lambda x: x["severity"], reverse=True)
    
    return detected_offenses if detected_offenses else [{"code": "UNKNOWN", "label": "Unclassified", "category": "N/A", "severity": 0, "match_method": "none", "matched_text": "N/A"}]


def identify_offender_from_text(text):
    """
    Detects offender names in both structured forms and narrative letters.
    1. Uses 'Last Name' and 'First Name' fields if available (template-based).
    2. Uses contextual pattern matching if the form is unstructured (narrative).
    3. Finds names in various contexts and natural language patterns.
    
    Returns:
        list: List of detected offender names (deduplicated)
    """
    offenders = []
    
    # --- Pattern 1: Template-based extraction ---
    # e.g. "Last Name: DE LA CRUZ" + "First Name: JUAN MIGUEL"
    # Look for structured form fields
    last_name_match = re.search(r"Last\s*Name[:\-]?\s*([^\n\r]+)", text, re.IGNORECASE)
    first_name_match = re.search(r"First\s*Name[:\-]?\s*([^\n\r]+)", text, re.IGNORECASE)
    
    if last_name_match and first_name_match:
        last_name = last_name_match.group(1).strip()
        first_name = first_name_match.group(1).strip()
        
        # Convert to title case if all uppercase (common in forms)
        if last_name.isupper():
            last_name = last_name.title()
        if first_name.isupper():
            first_name = first_name.title()
        
        full_name = f"{first_name} {last_name}"
        offenders.append(full_name)
    
    # --- Pattern 2: Contextual pattern with keywords ---
    # e.g. "The student Juan Dela Cruz was caught cheating."
    # Keywords: student, offender, faculty, staff, employee
    context_patterns = [
        r"(?:student|offender|faculty|staff|employee)\s+(?:named\s+)?([A-Z][a-z]+(?:\s+(?:de|dela|del|van|von|Da|Di)?\s*[A-Z][a-z]+)+)",
        r"(?:student|offender|faculty|staff|employee)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
    ]
    
    for pattern in context_patterns:
        context_matches = re.findall(pattern, text)
        for name in context_matches:
            if isinstance(name, tuple):
                name = name[0]
            cleaned_name = name.strip()
            # Filter out common words that might be capitalized
            if cleaned_name and not cleaned_name.lower() in ['the', 'was', 'is', 'are', 'were', 'been', 'has', 'have', 'had']:
                offenders.append(cleaned_name)
    
    # --- Pattern 3: Names before action verbs ---
    # e.g. "Juan Miguel De La Cruz was caught", "John Doe committed"
    action_patterns = [
        r"\b([A-Z][a-z]+(?:\s+(?:de|dela|del|van|von|Da|Di)?\s*[A-Z][a-z]+)+)\s+(?:was|were|is|committed|caught|violated|engaged|participated)",
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+(?:who|was|were|committed|caught|violated)",
    ]
    
    for pattern in action_patterns:
        action_matches = re.findall(pattern, text)
        for name in action_matches:
            cleaned_name = name.strip()
            if cleaned_name and len(cleaned_name.split()) >= 2:  # At least first + last name
                offenders.append(cleaned_name)
    
    # --- Pattern 4: "This report is about [Name]" ---
    about_pattern = r"(?:report|complaint|letter|document)\s+(?:is\s+)?(?:about|regarding|concerning)\s+([A-Z][a-z]+(?:\s+(?:de|dela|del|van|von)?\s*[A-Z][a-z]+)+)"
    about_matches = re.findall(about_pattern, text, re.IGNORECASE)
    for name in about_matches:
        cleaned_name = name.strip()
        if cleaned_name:
            offenders.append(cleaned_name)
    
    # --- Pattern 5: Names in quotes or parentheses ---
    # e.g. The offender "Juan Dela Cruz" or student (Juan Dela Cruz)
    quoted_pattern = r'["\'(]([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})["\')]'
    quoted_matches = re.findall(quoted_pattern, text)
    for name in quoted_matches:
        cleaned_name = name.strip()
        if cleaned_name and len(cleaned_name.split()) >= 2:
            offenders.append(cleaned_name)
    
    # Remove duplicates and filter out invalid names
    offenders = list(set(offenders))
    
    # Filter out names that are too short or contain numbers
    filtered_offenders = []
    for name in offenders:
        # Must have at least 2 words (first + last name)
        words = name.split()
        if len(words) >= 2 and not any(char.isdigit() for char in name):
            # Filter out common false positives
            if name.lower() not in ['the student', 'the offender', 'this report', 'this letter']:
                filtered_offenders.append(name)
    
    return filtered_offenders

