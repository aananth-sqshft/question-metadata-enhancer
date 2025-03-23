# modules/llm_processor.py
import os
import json
import logging
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class LLMProcessor:
    """
    Handles integration with Large Language Models for metadata enhancement.
    """
    
    def __init__(self, api_type='openai'):
        """
        Initialize LLM processor with the specified API type.
        
        Args:
            api_type (str): Type of LLM API to use ('openai' or 'anthropic')
        """
        self.api_type = api_type.lower()
        
        # Set up API credentials based on the API type
        if self.api_type == 'openai':
            self.api_key = os.getenv('OPENAI_API_KEY')
            if not self.api_key:
                logger.warning("OpenAI API key not found in environment variables.")
        elif self.api_type == 'anthropic':
            self.api_key = os.getenv('ANTHROPIC_API_KEY')
            if not self.api_key:
                logger.warning("Anthropic API key not found in environment variables.")
        else:
            raise ValueError(f"Unsupported API type: {api_type}")
    
    def analyze_question(self, ocr_text, existing_metadata=None):
        """
        Send OCR-extracted text to LLM for analysis and metadata enhancement.
        
        Args:
            ocr_text (str): OCR-extracted text from the question image
            existing_metadata (dict, optional): Existing metadata for the question
            
        Returns:
            dict: Enhanced metadata from LLM analysis
        """
        if not ocr_text:
            return {'error': 'No OCR text provided for analysis'}
        
        # Prepare existing metadata for the prompt
        metadata_str = self._format_metadata(existing_metadata) if existing_metadata else "No existing metadata."
        
        # Create the prompt
        prompt = self._create_prompt(ocr_text, metadata_str)
        
        try:
            # Call the appropriate LLM API
            if self.api_type == 'openai':
                response = self._call_openai(prompt)
            elif self.api_type == 'anthropic':
                response = self._call_anthropic(prompt)
            
            # Parse the LLM response
            enhanced_metadata = self._parse_response(response)
            return enhanced_metadata
            
        except Exception as e:
            error_msg = f"LLM analysis failed: {str(e)}"
            logger.error(error_msg)
            return {'error': error_msg}
    
    def _format_metadata(self, metadata):
        """
        Format existing metadata for inclusion in the prompt.
        
        Args:
            metadata (dict): Existing metadata
            
        Returns:
            str: Formatted metadata string
        """
        formatted = []
        for key, value in metadata.items():
            if key not in ['filename', 'original_image', 'coordinates'] and value:
                formatted.append(f"{key.capitalize()}: {value}")
        
        return "\n".join(formatted) if formatted else "No existing metadata."
    
    def _create_prompt(self, ocr_text, metadata_str):
        """
        Create the prompt for the LLM.
        
        Args:
            ocr_text (str): OCR-extracted text
            metadata_str (str): Formatted existing metadata
            
        Returns:
            str: Complete prompt for the LLM
        """
        return f"""
You are an expert in educational assessment. Analyze the following exam question and generate enhanced metadata for it.

QUESTION TEXT:
{ocr_text}

EXISTING METADATA:
{metadata_str}

Please generate the following additional metadata:
1. Question type (multiple choice, short answer, calculation, essay, etc.)
2. Difficulty level (easy, medium, hard)
3. Keywords or key concepts (comma-separated)
4. Cognitive skills required (recall, understanding, application, analysis, evaluation, creation)
5. Detailed topic classification with subtopics
6. A cleaned and properly formatted version of the question text

Return your analysis in the following JSON format:
```json
{
  "question_type": "string",
  "difficulty_level": "string",
  "keywords": ["string"],
  "cognitive_skills": ["string"],
  "topic_classification": {
    "main_topic": "string",
    "subtopics": ["string"]
  },
  "cleaned_text": "string"
}
```

Do not include any other text in your response - only the JSON.
"""
    
    def _call_openai(self, prompt):
        """
        Call OpenAI API for LLM processing.
        
        Args:
            prompt (str): Complete prompt for the LLM
            
        Returns:
            str: LLM response
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": "gpt-4",  # Or gpt-3.5-turbo for a cheaper, faster option
            "messages": [
                {"role": "system", "content": "You are an expert in educational assessment and metadata generation."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3  # Lower temperature for more consistent, focused responses
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            error_content = response.json()
            raise Exception(f"OpenAI API error: {error_content}")
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    def _call_anthropic(self, prompt):
        """
        Call Anthropic API for LLM processing.
        
        Args:
            prompt (str): Complete prompt for the LLM
            
        Returns:
            str: LLM response
        """
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-3-opus-20240229",  # Or other available Claude models
            "max_tokens": 1000,
            "temperature": 0.3,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            error_content = response.json()
            raise Exception(f"Anthropic API error: {error_content}")
        
        result = response.json()
        return result["content"][0]["text"]
    
    def _parse_response(self, response):
        """
        Parse the LLM response into a structured format.
        
        Args:
            response (str): LLM response
            
        Returns:
            dict: Structured metadata
        """
        try:
            # Extract JSON from the response - assuming the response is JSON or contains JSON
            json_content = response.strip()
            
            # If the response includes markdown code blocks, extract the JSON
            if "```json" in json_content:
                json_content = json_content.split("```json")[1].split("```")[0].strip()
            elif "```" in json_content:
                json_content = json_content.split("```")[1].split("```")[0].strip()
            
            # Parse the JSON
            metadata = json.loads(json_content)
            return metadata
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse LLM response: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Problematic response: {response}")
            return {'error': error_msg, 'raw_response': response}
        
        