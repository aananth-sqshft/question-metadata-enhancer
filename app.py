# app.py
import os
import json
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory
# Import config
from config import QUESTION_FOLDER, METADATA_FILE, LLM_API_TYPE, DEBUG, ANTHROPIC_API_KEY


# Import modules
from modules.ocr_processor import OCRProcessor
from modules.llm_processor import LLMProcessor
from modules.metadata_manager import MetadataManager

# Add this near the top of your app.py after loading configuration
print(f"[DEBUG] QUESTION_FOLDER value: '{QUESTION_FOLDER}'")
print(f"[DEBUG] QUESTION_FOLDER from env: '{os.getenv('QUESTION_FOLDER')}'")
print(f"[DEBUG] Directory exists: {os.path.exists(QUESTION_FOLDER)}")
if os.path.exists(QUESTION_FOLDER):
    print(f"[DEBUG] Files in directory: {os.listdir(QUESTION_FOLDER)}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, 
            static_folder=os.path.abspath('static'),
            static_url_path='/static')

logger.info(f"Created directory: {QUESTION_FOLDER}")

# Ensure directories exist
if not os.path.exists(QUESTION_FOLDER):
    os.makedirs(QUESTION_FOLDER)
    logger.info(f"Created directory: {QUESTION_FOLDER}")


# Initialize components
ocr_processor = OCRProcessor(QUESTION_FOLDER)
llm_processor = LLMProcessor(LLM_API_TYPE)
metadata_manager = MetadataManager(METADATA_FILE)

# Routes
@app.route('/')
def index():
    """Main dashboard page"""
    image_list = ocr_processor.get_image_list()
    print(f"[DEBUG] Image list from OCR processor: {image_list}")
    return render_template('dashboard.html', images=image_list, question_folder=QUESTION_FOLDER)


@app.route('/debug')
def debug_info():
    """Debug endpoint to see configuration and files"""
    # Get OCR processor's image list
    image_list = ocr_processor.get_image_list()
    
    # Check if we can access the files directly
    direct_files = []
    if os.path.exists(QUESTION_FOLDER):
        direct_files = os.listdir(QUESTION_FOLDER)
    
    return jsonify({
        'question_folder': QUESTION_FOLDER,
        'folder_exists': os.path.exists(QUESTION_FOLDER),
        'env_question_folder': os.getenv('QUESTION_FOLDER'),
        'ocr_processor_image_list': image_list,
        'direct_files_in_folder': direct_files,
        'all_env_vars': {k: v for k, v in os.environ.items() if 'FOLDER' in k or 'FILE' in k or 'PATH' in k}
    })


@app.route('/images')
def list_images():
    """API endpoint to get a list of all question images"""
    image_list = ocr_processor.get_image_list()
    return jsonify(image_list)

@app.route('/images/<filename>')
def serve_image(filename):
    """Serve a question image"""
    print(f"[DEBUG] Serving image: {filename} from folder: {QUESTION_FOLDER}")
    # For security, validate the filename doesn't contain path traversal
    if '..' in filename or filename.startswith('/'):
        return "Invalid filename", 400
        
    # Check if the file exists before trying to serve it
    full_path = os.path.join(QUESTION_FOLDER, filename)
    if not os.path.exists(full_path):
        print(f"[DEBUG] Image file not found: {full_path}")
        return "Image not found", 404
        
    print(f"[DEBUG] Serving image from: {full_path}")
    return send_from_directory(QUESTION_FOLDER, filename)

@app.route('/ocr/process', methods=['POST'])
def process_ocr():
    """Process images with OCR"""
    data = request.get_json()
    filenames = data.get('filenames', [])
    
    if not filenames:
        # Process all images if none specified
        filenames = ocr_processor.get_image_list()
    
    # Process the images
    results = ocr_processor.process_batch(filenames)
    
    return jsonify({
        'success': True,
        'processed': len(results),
        'results': results
    })

@app.route('/ocr/result/<filename>')
def get_ocr_result(filename):
    """Get OCR results for a specific image"""
    result = ocr_processor.process_image(filename)
    
    # Get existing metadata
    metadata = metadata_manager.get_metadata_for_image(filename)
    
    return jsonify({
        'ocr_result': result,
        'metadata': metadata
    })

@app.route('/llm/analyze', methods=['POST'])
def analyze_with_llm():
    """Analyze OCR text with LLM"""
    data = request.get_json()
    filename = data.get('filename')
    ocr_text = data.get('ocr_text', '')
    
    if not filename or not ocr_text:
        return jsonify({
            'success': False,
            'error': 'Filename and OCR text required'
        }), 400
    
    # Get existing metadata
    existing_metadata = metadata_manager.get_metadata_for_image(filename)
    
    # Call LLM for analysis
    enhanced_metadata = llm_processor.analyze_question(ocr_text, existing_metadata)
    
    # Improved error handling
    success = True
    error_message = None
    
    if 'error' in enhanced_metadata:
        success = False
        error_message = enhanced_metadata.get('error', 'Unknown error during LLM analysis')
        app.logger.error(f"LLM analysis error for {filename}: {error_message}")
        # Add additional context if available
        if 'raw_response' in enhanced_metadata:
            app.logger.debug(f"Raw response: {enhanced_metadata['raw_response']}")
    
    return jsonify({
        'success': success,
        'error': error_message,
        'metadata': enhanced_metadata,
        'filename': filename
    })

@app.route('/metadata/update', methods=['POST'])
def update_metadata():
    """Update metadata with enhanced information"""
    data = request.get_json()
    filename = data.get('filename')
    enhanced_metadata = data.get('metadata', {})
    
    if not filename or not enhanced_metadata:
        return jsonify({
            'success': False,
            'error': 'Filename and metadata required'
        }), 400
    
    # Update the metadata
    success = metadata_manager.update_metadata(filename, enhanced_metadata)
    
    return jsonify({
        'success': success,
        'filename': filename
    })

@app.route('/metadata/batch-update', methods=['POST'])
def batch_update_metadata():
    """Update metadata for multiple images"""
    data = request.get_json()
    updates = data.get('updates', [])
    
    if not updates:
        return jsonify({
            'success': False,
            'error': 'No updates provided'
        }), 400
    
    # Validate format
    if not all('filename' in item and 'metadata' in item for item in updates):
        return jsonify({
            'success': False,
            'error': 'Invalid update format'
        }), 400
    
    # Format updates for the manager
    formatted_updates = [(item['filename'], item['metadata']) for item in updates]
    
    # Update the metadata
    success_count, failure_count = metadata_manager.update_batch_metadata(formatted_updates)
    
    return jsonify({
        'success': failure_count == 0,
        'success_count': success_count,
        'failure_count': failure_count
    })

@app.route('/ocr/review/<filename>')
def ocr_review(filename):
    """Page for reviewing OCR results"""
    return render_template('ocr_review.html', filename=filename)

@app.route('/metadata/review/<filename>')
def metadata_review(filename):
    """Page for reviewing enhanced metadata"""
    return render_template('metadata_review.html', filename=filename)

@app.route('/test-css')
def test_css():
    return send_from_directory('static/css', 'main.css')


if __name__ == '__main__':
    app.run(debug=DEBUG, host='0.0.0.0', port=5001)  # Different port from extractor

