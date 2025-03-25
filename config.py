# config.py
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Application settings
DEBUG = True

# Path configuration
QUESTION_FOLDER = os.getenv('QUESTION_FOLDER')  # Path to snipped question images
METADATA_FILE = os.getenv('METADATA_FILE')  # Path to metadata file

# Database configuration
DB_FILE = os.getenv('DB_FILE', os.path.join(os.path.dirname(METADATA_FILE), 'questions.db'))

# LLM API Configuration
LLM_API_TYPE = 'anthropic'  # or 'openai'
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# OCR Configuration
TESSERACT_CMD = None  # Path to Tesseract executable, None for default location
# e.g. r'C:\Program Files\Tesseract-OCR\tesseract.exe' on Windows

# Logging settings
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

