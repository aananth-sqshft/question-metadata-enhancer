# modules/llm_processor.py
import os
import json
import logging
import requests
from dotenv import load_dotenv
from distutils.version import StrictVersion

# Conditionally import anthropic SDK if available
try:
    import anthropic
    ANTHROPIC_SDK_AVAILABLE = True
except ImportError:
    ANTHROPIC_SDK_AVAILABLE = False

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
            
            # Add more detailed information based on exception type
            if 'anthropic-version' in str(e).lower():
                error_msg = "API version error: The Anthropic API version header might be incorrect. Please update your API version or check your credentials."
            elif 'api key' in str(e).lower() or 'apikey' in str(e).lower() or 'authentication' in str(e).lower():
                error_msg = "Authentication error: Please check your Anthropic API key is correctly set in the environment variables."
            elif 'model' in str(e).lower():
                error_msg = "Model error: The requested AI model may be invalid or unavailable. Please check your model configuration."
            elif 'timeout' in str(e).lower() or 'connection' in str(e).lower():
                error_msg = "Connection error: Unable to connect to the LLM service. Please check your internet connection and try again."
            
            return {'error': error_msg, 'detailed_error': str(e)}
    
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
{{
  "question_type": "string",
  "difficulty_level": "string",
  "keywords": ["string"],
  "cognitive_skills": ["string"],
  "topic_classification": {{
    "main_topic": "string",
    "subtopics": ["string"]
  }},
  "cleaned_text": "string"
}}
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
        # Use SDK if available, otherwise fall back to direct API calls
        if ANTHROPIC_SDK_AVAILABLE:
            try:
                client = anthropic.Anthropic(api_key=self.api_key)
                # Set client timeout to prevent hanging
                client.timeout = 30
                # If the anthropic-sdk version is 0.16.0, Claude 2 should work
                message = client.messages.create(
                    model="claude-2",  # Using a model compatible with our SDK version
                    max_tokens=1000,
                    temperature=0.3,
                    system="You are an expert in educational assessment and metadata generation.",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                # Check SDK version to handle different response formats
                try:
                    return message.content[0].text
                except (AttributeError, IndexError):
                    # Older SDK version might have a different structure
                    if hasattr(message, 'completion'):
                        return message.completion
                    elif hasattr(message, 'content'):
                        if isinstance(message.content, str):
                            return message.content
                        elif isinstance(message.content, list):
                            for content_block in message.content:
                                if hasattr(content_block, 'text'):
                                    return content_block.text
                        # Last resort fallback
                        return str(message.content)
            except Exception as e:
                logger.error(f"Anthropic SDK error: {str(e)}")
                logger.info("Falling back to direct API call")
                # Fall back to direct API call
        
        # Direct API call implementation
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"  # Using a compatible version with our SDK
        }
        
        # This data object is not used anymore - we pass the params directly to the API call
        data = {}
        # Now using the correct structure for the API call below
        
        try:
            # Revert to using the completions endpoint for Claude 2 which worked with API v2023-06-01
            response = requests.post(
                "https://api.anthropic.com/v1/complete",
                headers=headers,
                json={
                    "model": "claude-2",
                    "max_tokens_to_sample": 1000,
                    "temperature": 0.3,
                    "prompt": f"\n\nHuman: {prompt}\n\nAssistant:"
                },
                timeout=30  # Add a 30 second timeout to prevent hanging
            )
            
            # Check for non-JSON responses (like HTML error pages)
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' not in content_type.lower():
                raise Exception(f"Unexpected response type: {content_type}. This may indicate an authentication issue or network problem.")
            
            if response.status_code != 200:
                error_content = response.json() if 'application/json' in content_type.lower() else response.text
                raise Exception(f"Anthropic API error: {error_content}")
            
            result = response.json()
            # Extract completion from the complete endpoint response
            return result.get("completion", "")
        except requests.exceptions.Timeout:
            logger.error("Anthropic API request timed out after 30 seconds")
            raise Exception("Connection timeout: The API request took too long to complete. Please try again later.")
        except requests.exceptions.ConnectionError:
            logger.error("Connection error when calling Anthropic API")
            raise Exception("Connection error: Could not connect to the Anthropic API. Please check your internet connection.")
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise Exception(f"API request failed: {str(e)}")
    
    def _parse_response(self, response):
        """
        Parse the LLM response into a structured format.
        
        Args:
            response (str): LLM response
            
        Returns:
            dict: Structured metadata
        """
        try:
            # Check if response is None or empty
            if not response:
                raise ValueError("Empty response received from LLM")
                
            # Check if response might be HTML (indicating an error page)
            if response.strip().startswith('<'):
                error_msg = "Received HTML response instead of JSON. This likely indicates an API authentication error or rate limit issue."
                logger.error(error_msg)
                logger.debug(f"HTML response received: {response[:200]}...")
                return {'error': error_msg, 'raw_response': response[:500]}
            
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
        except Exception as e:
            error_msg = f"Error processing LLM response: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Problematic response: {response}")
            return {'error': error_msg, 'raw_response': str(response)[:500] if response else 'None'}
        
        