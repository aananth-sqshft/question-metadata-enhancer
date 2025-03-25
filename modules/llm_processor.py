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
    
    # Simple syllabus topics for each subject
    CHEMISTRY_SYLLABUS = "Atomic structure, Chemical bonding, Organic chemistry"
    MATHEMATICS_SYLLABUS = "Algebra, Calculus, Statistics, Geometry"
    ECONOMICS_SYLLABUS = "Microeconomics, Macroeconomics, International trade, Market structures"
    GP_SYLLABUS = "Social issues, Environment, Technology, Politics, Ethics"
  
    # Detailed physics syllabus structure
    PHYSICS_SYLLABUS = {
  "Sections": [
    {
      "Section": "MEASUREMENT",
      "Chapter": "Measurement",
      "Topics": [
        "Physical quantities and SI units",
        "Scalars and vectors",
        "Errors and uncertainties"
      ]
    },
    {
      "Section": "NEWTONIAN MECHANICS",
      "Chapter": "Kinematics",
      "Topics": [
        "Rectilinear motion",
        "Non-linear motion"
      ]
    },
    {
      "Section": "NEWTONIAN MECHANICS",
      "Chapter": "Dynamics",
      "Topics": [
        "Newton's laws of motion",
        "Linear momentum and its conservation"
      ]
    },
    {
      "Section": "NEWTONIAN MECHANICS",
      "Chapter": "Forces",
      "Topics": [
        "Types of force",
        "Centre of gravity",
        "Turning effects of forces",
        "Equilibrium of forces",
        "Upthrust"
      ]
    },
    {
      "Section": "NEWTONIAN MECHANICS",
      "Chapter": "Work, Energy and Power",
      "Topics": [
        "Work",
        "Energy conversion and conservation",
        "Efficiency",
        "Potential energy and kinetic energy",
        "Power"
      ]
    },
    {
      "Section": "NEWTONIAN MECHANICS",
      "Chapter": "Motion in a Circle",
      "Topics": [
        "Kinematics of uniform circular motion",
        "Centripetal acceleration",
        "Centripetal force"
      ]
    },
    {
      "Section": "NEWTONIAN MECHANICS",
      "Chapter": "Gravitational Field",
      "Topics": [
        "Gravitational field",
        "Gravitational force between point masses",
        "Gravitational field of a point mass",
        "Gravitational field near to the surface of the Earth",
        "Gravitational potential",
        "Circular orbits"
      ]
    },
    {
      "Section": "THERMAL PHYSICS",
      "Chapter": "Temperature and Ideal Gases",
      "Topics": [
        "Thermal equilibrium",
        "Temperature scales",
        "Equation of state",
        "Kinetic theory of gases",
        "Kinetic energy of a molecule"
      ]
    },
    {
      "Section": "THERMAL PHYSICS",
      "Chapter": "First Law of Thermodynamics",
      "Topics": [
        "Specific heat capacity and specific latent heat",
        "Internal energy",
        "First law of thermodynamics"
      ]
    },
    {
      "Section": "OSCILLATIONS AND WAVES",
      "Chapter": "Oscillations",
      "Topics": [
        "Simple harmonic motion",
        "Energy in simple harmonic motion",
        "Damped and forced oscillations, resonance"
      ]
    },
    {
      "Section": "OSCILLATION AND WAVES",
      "Chapter": "Wave Motion",
      "Topics": [
        "Progressive waves",
        "Transverse and longitudinal waves",
        "Polarisation",
        "Determination of frequency and wavelength of sound waves"
      ]
    },
    {
      "Section": "OSCILLATION AND WAVES",
      "Chapter": "Superposition",
      "Topics": [
        "Principle of superposition",
        "Stationary waves",
        "Diffraction",
        "Two-source interference",
        "Single slit and multiple slit diffraction"
      ]
    },
    {
      "Section": "ELECTRICITY AND MAGNETISM",
      "Chapter": "Electric Fields",
      "Topics": [
        "Concept of an electric field",
        "Electric force between point charges",
        "Electric field of a point charge",
        "Uniform electric fields",
        "Electric potential"
      ]
    },
    {
      "Section": "ELECTRICITY AND MAGNETISM",
      "Chapter": "Current of Electricity",
      "Topics": [
        "Electric current",
        "Potential difference",
        "Resistance and resistivity",
        "Electromotive force"
      ]
    },
    {
      "Section": "ELECTRICITY AND MAGNETISM",
      "Chapter": "D.C. Circuits",
      "Topics": [
        "Circuit symbols and diagrams",
        "Series and parallel arrangements",
        "Potential divider",
        "Balanced potentials"
      ]
    },
    {
      "Section": "ELECTRICITY AND MAGNETISM",
      "Chapter": "Electromagnetism",
      "Topics": [
        "Concept of a magnetic field",
        "Magnetic fields due to currents",
        "Force on a current-carrying conductor",
        "Force between current-carrying conductors",
        "Force on a moving charge"
      ]
    },
    {
      "Section": "ELECTRICITY AND MAGNETISM",
      "Chapter": "Electromagnetic Induction",
      "Topics": [
        "Magnetic flux",
        "Laws of electromagnetic induction"
      ]
    },
    {
      "Section": "ELECTRICITY AND MAGNETISM",
      "Chapter": "Alternating Current",
      "Topics": [
        "Characteristics of alternating currents",
        "The transformer",
        "Rectification with a diode"
      ]
    },
    {
      "Section": "MODERN PHYSICS",
      "Chapter": "Quantum Physics",
      "Topics": [
        "Energy of a photon",
        "The photoelectric effect",
        "Wave-particle duality",
        "Energy levels in atoms",
        "Line spectra",
        "X-ray spectra",
        "The uncertainty principle"
      ]
    },
    {
      "Section": "MODERN PHYSICS",
      "Chapter": "Nuclear Physics",
      "Topics": [
        "The nucleus",
        "Isotopes",
        "Nuclear processes",
        "Mass defect and nuclear binding energy",
        "Radioactive decay",
        "Biological effects of radiation"
      ]
    }
  ]
}
    
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
        prompt = self._create_prompt(ocr_text, metadata_str, existing_metadata)
        
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
    
    def _create_prompt(self, ocr_text, metadata_str, existing_metadata=None):
        """
        Create the prompt for the LLM.
        
        Args:
            ocr_text (str): OCR-extracted text
            metadata_str (str): Formatted existing metadata
            existing_metadata (dict, optional): Raw metadata dictionary
            
        Returns:
            str: Complete prompt for the LLM
        """
        # Determine subject based on metadata
        is_physics = False
        is_chemistry = False
        is_math = False
        is_economics = False
        is_gp = False
        
        # Debug log the incoming metadata
        logger.info(f"Creating prompt with metadata: {existing_metadata}")
        
        # Check if metadata contains subject information
        subject_found = False
        
        # First try to get subject from existing_metadata dict if it exists
        if existing_metadata and 'subject' in existing_metadata:
            subject = existing_metadata['subject'].lower()
            subject_found = True
            logger.info(f"Found subject in existing_metadata: {subject}")
        
        # If not found in existing_metadata, try to extract from metadata_str
        elif metadata_str and "Subject:" in metadata_str:
            # Extract subject from metadata_str
            lines = metadata_str.split("\n")
            for line in lines:
                if line.startswith("Subject:"):
                    subject = line.replace("Subject:", "").strip().lower()
                    subject_found = True
                    logger.info(f"Found subject in metadata_str: {subject}")
                    break
        
        if subject_found:
            if subject == 'physics':
                is_physics = True
                logger.info("Subject identified as physics")
            elif subject == 'chemistry':
                is_chemistry = True
                logger.info("Subject identified as chemistry")
            elif subject == 'mathematics' or subject == 'math':
                is_math = True
                logger.info("Subject identified as mathematics")
            elif subject == 'economics':
                is_economics = True
                logger.info("Subject identified as economics")
            elif subject == 'general paper' or subject == 'gp':
                is_gp = True
                logger.info("Subject identified as general paper")
            else:
                logger.info(f"Subject '{subject}' not recognized as any of the configured subjects")
        else:
            logger.info("No subject found in metadata")
            
        # Add subject-specific instructions if relevant
        subject_instruction = ""
        
        if is_physics:
            syllabus_str = str(self.PHYSICS_SYLLABUS)
            subject_instruction = f"""This is a Physics question. Find and update 'chapter' and 'topic' with the correct values from this syllabus json: {syllabus_str}."""
            logger.info(f"Adding physics syllabus to prompt: {syllabus_str}")
            logger.info(f"Physics syllabus variable type: {type(self.PHYSICS_SYLLABUS)}")
        elif is_chemistry:
            subject_instruction = f"""This is a Chemistry question. Find and update 'chapter' and 'topic' with the correct values from this syllabus json: {self.CHEMISTRY_SYLLABUS}."""
            logger.info(f"Adding chemistry syllabus to prompt: {self.CHEMISTRY_SYLLABUS}")
        elif is_math:
            subject_instruction = f"""This is a Mathematics question. Find and update 'chapter' and 'topic' with the correct values from this syllabus json:  {self.MATHEMATICS_SYLLABUS}."""
            logger.info(f"Adding mathematics syllabus to prompt: {self.MATHEMATICS_SYLLABUS}")
        elif is_economics:
            subject_instruction = f"""This is an Economics question. Find and update 'chapter' and 'topic' with the correct values from this syllabus json:  {self.ECONOMICS_SYLLABUS}."""
            logger.info(f"Adding economics syllabus to prompt: {self.ECONOMICS_SYLLABUS}")
        elif is_gp:
            subject_instruction = f"""This is a General Paper question. Find and update 'chapter' and 'topic' with the correct values from this syllabus json:  {self.GP_SYLLABUS}."""
            logger.info(f"Adding general paper syllabus to prompt: {self.GP_SYLLABUS}")
        
        logger.info(f"Final subject instruction: {subject_instruction}")
        
        # Build the complete prompt
        full_prompt = f"""
You are an expert in educational assessment. Analyze the following exam question and generate enhanced metadata for it.

QUESTION TEXT:
{ocr_text}

EXISTING METADATA:
{metadata_str}

{subject_instruction}

Return your analysis in the following JSON format:
Please generate the following additional metadata:
1. Question type (multiple choice, short answer, fill in the blanks, open ended, calculation, essay, etc.)
2. Difficulty level (easy, medium, hard, very hard)
3. Keywords or key concepts (comma-separated)
4. Cognitive skills required (recall, understanding, application, analysis, evaluation, creation etc)
5. Detailed topic classification with subtopics
6. A cleaned and properly formatted version of the question text and answer choices (for multiple choice) with your answer and your confidence in the answer

Return your analysis in the following JSON format:
```json
{{
  "chapter": "chapter matched up from syllabus json",
  "topic": "topic matched up from syllabus json",
  "question_type": "string (e.g., 'multiple_choice', 'true_false', 'open_ended', 'fill_in_the_blank', 'other')",
  "difficulty_level": "string (e.g., 'easy', 'medium', 'hard')",
  "keywords": ["string (e.g., 'keyword1')", "string (e.g., 'keyword2')", "string (e.g., 'keyword3')"],
  "cognitive_skills": ["string (e.g., 'recall')", "string (e.g., 'understanding')", "string (e.g., 'application')"],
  "cleaned_text": "string (The rephrased and formatted question text)",
  "answer": "string (For multiple choice, the letter of the correct answer.  For other types, the full answer text.)",
  "choices": [
    {{
      "letter": "string (e.g., 'A')",
      "text": "string (Text of choice A)"
    }},
    {{
      "letter": "string (e.g., 'B')",
      "text": "string (Text of choice B)"
    }},
    {{
      "letter": "string (e.g., 'C')",
      "text": "string (Text of choice C)"
    }}
  ],
  "answer_confidence": "number (between 0 and 1, e.g., 0.95)"
}}
```

Do not include any other text in your response - only the JSON.
"""

        # Log a shortened version of the prompt for debugging
        ocr_preview = ocr_text[:100] + "..." if len(ocr_text) > 100 else ocr_text
        log_prompt = f"""
You are an expert in educational assessment. Analyze the following exam question and generate enhanced metadata for it.

QUESTION TEXT:
{ocr_preview}

EXISTING METADATA:
{metadata_str}

{subject_instruction}

Return your analysis in the following JSON format:
[...rest of prompt omitted for brevity...]
"""
        logger.info(f"Generated prompt with subject instruction: {log_prompt}")
        
        return full_prompt
    
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
                # Fix SDK initialization by using only api_key parameter
                client = anthropic.Anthropic(api_key=self.api_key)
                # Using the latest model available with the SDK
                message = client.messages.create(
                    model="claude-3-haiku-20240307",  # Updated to a newer model available in the API
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
            "anthropic-version": "2023-06-01"  # This version should work with our requests
        }
        
        # This data object is not used anymore - we pass the params directly to the API call
        data = {}
        # Now using the correct structure for the API call below
        
        try:
            # Use messages endpoint for Claude 3 models
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={
                    "model": "claude-3-haiku-20240307",  # Updated to newer model
                    "max_tokens": 1000,
                    "temperature": 0.3,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
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
            # Extract content from the messages endpoint response
            if "content" in result and len(result["content"]) > 0:
                return result["content"][0]["text"]
            else:
                logger.error(f"Unexpected response structure: {result}")
                return ""
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
            
            # Fix the choices display format if present
            if 'choices' in metadata and isinstance(metadata['choices'], list):
                formatted_choices = []
                for choice in metadata['choices']:
                    if isinstance(choice, dict) and 'letter' in choice and 'text' in choice:
                        formatted_choices.append(f"{choice['letter']}: {choice['text']}")
                
                # Replace the choices array with the formatted string
                if formatted_choices:
                    metadata['choices'] = formatted_choices
            
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