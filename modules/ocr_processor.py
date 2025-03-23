# modules/ocr_processor.py
import os
import pytesseract
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class OCRProcessor:
    """
    Handles OCR processing for question images.
    Extracts text from images using Tesseract OCR.
    """
    
    def __init__(self, images_dir):
        """
        Initialize OCR processor with the directory containing question images.
        
        Args:
            images_dir (str): Path to the directory containing question images
        """
        self.images_dir = images_dir
        # Configure Tesseract path if needed
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Uncomment on Windows
    
    def get_image_list(self):
        """
        Get a list of all question images in the configured directory.
        
        Returns:
            list: List of filenames for question images
        """
        if not os.path.exists(self.images_dir):
            logger.error(f"Image directory not found: {self.images_dir}")
            return []
        
        # Only include PNG files that start with "question_"
        return [f for f in os.listdir(self.images_dir) 
                if f.startswith("question_") and f.lower().endswith('.png')]
    
    def process_image(self, image_filename):
        """
        Perform OCR on a single image.
        
        Args:
            image_filename (str): Filename of the image to process
            
        Returns:
            dict: Dictionary containing the OCR results and metadata
                {
                    'filename': str,
                    'text': str,
                    'success': bool,
                    'error': str (optional)
                }
        """
        image_path = os.path.join(self.images_dir, image_filename)
        result = {
            'filename': image_filename,
            'text': '',
            'success': False
        }
        
        if not os.path.exists(image_path):
            result['error'] = f"Image file not found: {image_path}"
            logger.error(result['error'])
            return result
        
        try:
            # Open the image
            img = Image.open(image_path)
            
            # Perform OCR
            ocr_config = r'--psm 6'  # Assume a single block of text
            extracted_text = pytesseract.image_to_string(img, config=ocr_config)
            
            # Clean the text
            cleaned_text = self._clean_text(extracted_text)
            
            result['text'] = cleaned_text
            result['success'] = True
            return result
            
        except Exception as e:
            error_msg = f"OCR processing failed for {image_filename}: {str(e)}"
            result['error'] = error_msg
            logger.error(error_msg)
            return result
    
    def process_batch(self, image_filenames=None):
        """
        Process a batch of images.
        
        Args:
            image_filenames (list, optional): List of filenames to process.
                If None, all images in the directory will be processed.
                
        Returns:
            list: List of dictionaries containing OCR results for each image
        """
        if image_filenames is None:
            image_filenames = self.get_image_list()
        
        results = []
        for filename in image_filenames:
            logger.info(f"Processing {filename}...")
            result = self.process_image(filename)
            results.append(result)
        
        return results
    
    def _clean_text(self, text):
        """
        Clean and normalize OCR-extracted text.
        
        Args:
            text (str): Raw OCR output
            
        Returns:
            str: Cleaned text
        """
        if not text:
            return ""
        
        # Replace multiple newlines with a single one
        cleaned = ' '.join([line.strip() for line in text.split('\n') if line.strip()])
        
        # Remove any unusual characters or OCR artifacts
        # (This could be expanded based on common OCR issues with your documents)
        return cleaned.strip()
    
    