#!/usr/bin/env python3
"""
OCR Service Server
Dedicated microservice for OCR processing with multiple engines
"""

import os
import sys
import logging
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils.ocr_processor import OCRProcessor
except ImportError:
    print("Warning: OCRProcessor not found, creating minimal implementation")
    
    class OCRProcessor:
        def __init__(self):
            self.engines = ['tesseract', 'easyocr']
            
        def extract_text_from_image(self, image_path, engines=None):
            """Minimal OCR implementation"""
            try:
                import pytesseract
                from PIL import Image
                
                image = Image.open(image_path)
                text = pytesseract.image_to_string(image)
                
                return {
                    'success': True,
                    'text': text,
                    'engine_used': 'tesseract',
                    'confidence': 0.8
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'text': '',
                    'engine_used': 'none'
                }

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize OCR processor
ocr_processor = OCRProcessor()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp', 'pdf'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Removed duplicate health check - using the more comprehensive one below

@app.route('/ocr/extract', methods=['POST'])
def extract_text():
    """Extract text from uploaded image"""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Check file extension
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'File type not allowed. Supported: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Get optional parameters
        engines = request.form.get('engines', 'tesseract,easyocr').split(',')
        language = request.form.get('language', 'eng')
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Process with OCR
            result = ocr_processor.extract_text_from_image(
                temp_path, 
                engines=engines
            )
            
            # Add metadata
            result['filename'] = filename
            result['file_size'] = os.path.getsize(temp_path)
            result['language'] = language
            
            return jsonify(result)
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"OCR extraction error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def ocr_health_check():
    """Health check endpoint for Docker health checks"""
    try:
        # Test OCR processor availability
        if not ocr_processor:
            return jsonify({
                "status": "unhealthy",
                "error": "OCR processor not initialized",
                "service": "ocr-service"
            }), 503
        
        # Test basic functionality
        engines = getattr(ocr_processor, 'engines', ['tesseract'])
        
        return jsonify({
            "status": "healthy",
            "service": "ocr-service",
            "engines_available": engines,
            "processor_ready": True
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "service": "ocr-service"
        }), 503

@app.route('/ocr/engines', methods=['GET'])
def get_engines():
    """Get available OCR engines"""
    return jsonify({
        'engines': ocr_processor.engines if hasattr(ocr_processor, 'engines') else ['tesseract'],
        'default': 'tesseract'
    })

@app.route('/ocr/languages', methods=['GET'])
def get_languages():
    """Get supported languages"""
    return jsonify({
        'languages': {
            'eng': 'English',
            'hin': 'Hindi',
            'tam': 'Tamil',
            'tel': 'Telugu',
            'kan': 'Kannada',
            'mal': 'Malayalam'
        },
        'default': 'eng'
    })

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return jsonify({
        'success': False,
        'error': 'File too large. Maximum size: 16MB'
    }), 413

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server error"""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('FLASK_PORT', 8898))
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting OCR Service on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )
