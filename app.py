# app.py
import os
import json
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory
# Import config
from config import QUESTION_FOLDER, METADATA_FILE, DB_FILE, LLM_API_TYPE, DEBUG, ANTHROPIC_API_KEY


# Import modules
from modules.ocr_processor import OCRProcessor
from modules.llm_processor import LLMProcessor
from modules.metadata_manager import MetadataManager
from modules.database_manager import DatabaseManager

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
database_manager = DatabaseManager(DB_FILE)

# Routes
@app.route('/')
def index():
    """Main dashboard page"""
    # Get all available images from the OCR processor
    all_images = ocr_processor.get_image_list()
    
    # Get images explicitly marked as completed
    completed_review = metadata_manager.get_completed_review_list()
    
    # Filter to only include completed images that actually exist in the image folder
    completed_images = [img for img in completed_review if img in all_images]
    
    # All images not in the completed list are considered pending
    pending_images = [img for img in all_images if img not in completed_images]
    
    print(f"[DEBUG] All images: {len(all_images)}, Pending: {len(pending_images)}, Completed: {len(completed_images)}")
    
    return render_template(
        'dashboard.html', 
        pending_images=pending_images, 
        completed_images=completed_images,
        question_folder=QUESTION_FOLDER
    )


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
    force_reprocess = data.get('force_reprocess', False)
    
    if not filenames:
        # Process all images if none specified
        filenames = ocr_processor.get_image_list()
    
    # Process the images
    results = ocr_processor.process_batch(filenames, force_reprocess=force_reprocess)
    
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

@app.route('/llm/prompt', methods=['POST'])
def get_llm_prompt():
    """Generate and return the LLM prompt for preview/editing"""
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
    
    # Generate prompt (without calling the LLM)
    metadata_str = llm_processor._format_metadata(existing_metadata) if existing_metadata else "No existing metadata."
    prompt = llm_processor._create_prompt(ocr_text, metadata_str)
    
    return jsonify({
        'success': True,
        'prompt': prompt,
        'filename': filename
    })

@app.route('/llm/analyze', methods=['POST'])
def analyze_with_llm():
    """Analyze OCR text with LLM"""
    data = request.get_json()
    filename = data.get('filename')
    ocr_text = data.get('ocr_text', '')
    custom_prompt = data.get('custom_prompt', None)
    
    if not filename or not ocr_text:
        return jsonify({
            'success': False,
            'error': 'Filename and OCR text required'
        }), 400
    
    # Get existing metadata
    existing_metadata = metadata_manager.get_metadata_for_image(filename)
    
    # Call LLM for analysis with optional custom prompt
    if custom_prompt:
        # Use custom prompt directly
        response = llm_processor._call_anthropic(custom_prompt) if llm_processor.api_type == 'anthropic' else llm_processor._call_openai(custom_prompt)
        enhanced_metadata = llm_processor._parse_response(response)
    else:
        # Use the standard analyze_question flow
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

@app.route('/metadata/view/<filename>')
def metadata_view(filename):
    """Page for viewing all details about a question, including OCR results and metadata"""
    # Get OCR results and metadata
    ocr_result = ocr_processor.process_image(filename, force_reprocess=False)
    metadata = metadata_manager.get_metadata_for_image(filename)
    
    # Determine if the question has been processed
    processed = ocr_result.get('success', False)
    
    # Check if review is completed
    review_completed = metadata.get('review_completed', False) if metadata else False
    
    return render_template(
        'metadata_view.html', 
        filename=filename, 
        ocr_result=ocr_result, 
        metadata=metadata, 
        processed=processed,
        review_completed=review_completed
    )

@app.route('/review/toggle/<filename>', methods=['POST'])
def toggle_review_completion(filename):
    """Toggle the review completion status for a question"""
    data = request.get_json()
    completed = data.get('completed', True)
    
    # Update the review status
    success = metadata_manager.mark_review_completed(filename, completed)
    
    return jsonify({
        'success': success,
        'filename': filename,
        'review_completed': completed
    })

@app.route('/database/save', methods=['POST'])
def save_to_database():
    """Save a review-completed question to the SQLite database"""
    data = request.get_json()
    filename = data.get('filename')
    
    if not filename:
        return jsonify({
            'success': False,
            'error': 'Filename is required'
        }), 400
    
    # Get the metadata for this question
    metadata = metadata_manager.get_metadata_for_image(filename)
    
    if not metadata:
        return jsonify({
            'success': False,
            'error': 'Metadata not found for this question'
        }), 404
    
    # Check if review is completed
    if not metadata.get('review_completed', False):
        return jsonify({
            'success': False,
            'error': 'Cannot save to database: review is not completed'
        }), 400
    
    # Save to database
    success = database_manager.save_question(metadata)
    
    return jsonify({
        'success': success,
        'filename': filename
    })

@app.route('/database/questions', methods=['GET'])
def list_database_questions():
    """List all questions stored in the database"""
    # Option to filter by review status
    review_completed = request.args.get('review_completed')
    if review_completed is not None:
        review_completed = review_completed.lower() == 'true'
    
    # Get questions from database
    questions = database_manager.get_all_questions(review_completed)
    
    return jsonify({
        'success': True,
        'questions': [q.get('filename') for q in questions],
        'count': len(questions)
    })

@app.route('/test-css')
def test_css():
    return send_from_directory('static/css', 'main.css')


if __name__ == '__main__':
    app.run(debug=DEBUG, host='0.0.0.0', port=5001)  # Different port from extractor

