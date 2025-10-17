"""
Enhanced extraction that combines field extraction with offender detection
"""
from .ocr_utils import extract_fields_from_text, identify_offender_from_text, detect_offense_from_text, detect_all_offenses_from_text

def extract_all_info(text):
    """
    Enhanced extraction that uses both field patterns and offender detection
    Returns complete information with best-effort extraction
    """
    # Get basic fields
    fields = extract_fields_from_text(text)
    
    # Get offenders (works better for narrative formats)
    offenders = identify_offender_from_text(text)
    
    # If name not found in fields but found in offenders, use offender data
    if offenders and (not fields.get("first_name") or not fields.get("last_name")):
        # Use first detected offender
        full_name = offenders[0]
        name_parts = full_name.split()
        
        # Handle compound last names (De La Cruz, Del Rosario, etc.)
        if len(name_parts) >= 3 and name_parts[-3].lower() in ['de', 'dela', 'del', 'van', 'von']:
            fields["last_name"] = " ".join(name_parts[-3:])
            fields["first_name"] = " ".join(name_parts[:-3])
        elif len(name_parts) >= 2 and name_parts[-2].lower() in ['de', 'dela', 'del', 'van', 'von']:
            fields["last_name"] = " ".join(name_parts[-2:])
            fields["first_name"] = " ".join(name_parts[:-2])
        elif len(name_parts) >= 2:
            fields["last_name"] = name_parts[-1]
            fields["first_name"] = " ".join(name_parts[:-1])
    
    # Detect offense
    offense_info = detect_offense_from_text(fields.get("description", "") or text)
    all_offenses = detect_all_offenses_from_text(fields.get("description", "") or text)
    
    return {
        "fields": fields,
        "offenders_identified": offenders,
        "offense_detected": offense_info,
        "all_offenses_detected": all_offenses
    }

