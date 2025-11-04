from flask import Blueprint, request, jsonify, current_app
from ...utils.file_upload import save_upload
from ...auth_utils import login_required
from .ocr_utils import (
    extract_text_from_file, 
    extract_fields_from_text, 
    detect_offense_from_text, 
    detect_all_offenses_from_text,
    identify_offender_from_text
)
from . import bp


@bp.route('/upload', methods=['POST'])
@login_required
def upload_ocr_form():
    """
    OCR Upload endpoint for extracting text from complaint forms
    Accepts: Image files (.jpg, .jpeg, .png) or PDF files
    Returns: Extracted fields, detected offense information, and identified offenders
    """
    file = request.files.get('file')
    if not file:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    try:
        # Save the uploaded file securely
        saved_path = save_upload(file, current_app.config['UPLOAD_FOLDER'])
        
        # Extract text from the file using OCR
        try:
            extracted_text = extract_text_from_file(saved_path)
        except RuntimeError as ocr_error:
            # Tesseract not installed or other OCR error
            return jsonify({
                "success": False,
                "error": str(ocr_error),
                "error_type": "tesseract_not_installed",
                "install_instructions": "Please install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki"
            }), 500
        
        # Extract structured fields from the text
        fields = extract_fields_from_text(extracted_text)
        
        # Identify offenders from the full text (works for both template and narrative formats)
        offenders = identify_offender_from_text(extracted_text)
        
        # If name not found in fields but found in offenders, use offender data
        if offenders and (not fields.get("first_name") or not fields.get("last_name")):
            # Use first detected offender as primary subject
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
        
        # Detect offense from the description or full text
        offense_info = detect_offense_from_text(fields.get("description", "") or extracted_text)
        
        # Also get all detected offenses for comprehensive analysis
        all_offenses = detect_all_offenses_from_text(fields.get("description", "") or extracted_text)

        response = {
            "success": True,
            "file_path": saved_path,
            "extracted_text": extracted_text,
            "fields": fields,
            "offense_detected": offense_info,
            "all_offenses_detected": all_offenses,
            "offenders_identified": offenders
        }
        return jsonify(response), 200
        
    except Exception as e:
        current_app.logger.error(f"OCR extraction error: {str(e)}")
        return jsonify({
            "success": False, 
            "error": f"OCR extraction failed: {str(e)}"
        }), 500


@bp.route('/extract-text', methods=['POST'])
@login_required
def extract_text_only():
    """
    Extract text only from uploaded document without field parsing
    Useful for testing OCR quality
    """
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        # Save the uploaded file securely
        saved_path = save_upload(file, current_app.config['UPLOAD_FOLDER'])
        
        # Extract text from the file using OCR
        extracted_text = extract_text_from_file(saved_path)

        response = {
            "success": True,
            "file_path": saved_path,
            "extracted_text": extracted_text
        }
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/extract-from-text', methods=['POST'])
@login_required
def extract_from_text():
    """
    Extract fields from manually entered text (fallback when Tesseract is not available)
    Accepts: Plain text in request body
    Returns: Extracted fields and detected offense information
    """
    try:
        data = request.get_json()
        extracted_text = data.get('text', '').strip()
        
        if not extracted_text:
            return jsonify({
                "success": False,
                "error": "No text provided"
            }), 400
        
        # Extract structured fields from the text
        fields = extract_fields_from_text(extracted_text)
        
        # Identify offenders from the full text
        offenders = identify_offender_from_text(extracted_text)
        
        # If name not found in fields but found in offenders, use offender data
        if offenders and (not fields.get("first_name") or not fields.get("last_name")):
            full_name = offenders[0]
            name_parts = full_name.split()
            
            # Handle compound last names
            if len(name_parts) >= 3 and name_parts[-3].lower() in ['de', 'dela', 'del', 'van', 'von']:
                fields["last_name"] = " ".join(name_parts[-3:])
                fields["first_name"] = " ".join(name_parts[:-3])
            elif len(name_parts) >= 2 and name_parts[-2].lower() in ['de', 'dela', 'del', 'van', 'von']:
                fields["last_name"] = " ".join(name_parts[-2:])
                fields["first_name"] = " ".join(name_parts[:-2])
            elif len(name_parts) >= 2:
                fields["last_name"] = name_parts[-1]
                fields["first_name"] = " ".join(name_parts[:-1])
        
        # Detect offense from the description or full text
        offense_info = detect_offense_from_text(fields.get("description", "") or extracted_text)
        all_offenses = detect_all_offenses_from_text(fields.get("description", "") or extracted_text)

        response = {
            "success": True,
            "extracted_text": extracted_text,
            "fields": fields,
            "offense_detected": offense_info,
            "all_offenses_detected": all_offenses,
            "offenders_identified": offenders
        }
        return jsonify(response), 200
        
    except Exception as e:
        current_app.logger.error(f"Text extraction error: {str(e)}")
        return jsonify({
            "success": False, 
            "error": f"Text extraction failed: {str(e)}"
        }), 500


@bp.route('/test', methods=['GET'])
def test_ocr():
    """Test endpoint to verify OCR module is registered"""
    return jsonify({
        "message": "OCR module is working",
        "endpoints": [
            "/ocr/upload - Upload and process complaint form (POST)",
            "/ocr/extract-text - Extract text only (POST)",
            "/ocr/extract-from-text - Extract from manual text entry (POST)",
            "/ocr/test - Test endpoint (GET)"
        ]
    }), 200

