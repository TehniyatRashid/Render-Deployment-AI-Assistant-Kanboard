# ai_services.py
import os
import logging
import json
import time
from typing import Dict, Any
from google import genai
from google.genai import types
from dotenv import load_dotenv
import requests
from datetime import datetime

load_dotenv()
logger = logging.getLogger(__name__)

class AIEstimator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("⚠️ GEMINI_API_KEY not found in environment variables")
            self.client = None
            self.model_id = None
            self.available = False
            return
            
        try:
            self.client = genai.Client(api_key=api_key)
            self.model_id = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
            self.available = True
            logger.info(f"✅ Gemini AI Service initialized with model: {self.model_id}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini client: {e}")
            self.client = None
            self.available = False
    
    def estimate_task(self, task_description: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Calls Gemini API to get a structured task estimation."""
        
        if not self.available:
            logger.error("Gemini service not available")
            return self._get_fallback_response(task_description)
        
        prompt = self._create_prompt(task_description)
        
        try:
            # Configure generation with parameters
            generation_config = types.GenerateContentConfig(
                temperature=1.0,
                top_p=0.95,
                top_k=40,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
            
            # Retry logic for failures
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    response = self.client.models.generate_content(
                        model=self.model_id,
                        contents=prompt,
                        config=generation_config
                    )
                    logger.info(f"✅ Gemini API call successful (attempt {attempt + 1})")
                    break
                    
                except Exception as e:
                    error_str = str(e)
                    if "503" in error_str or "UNAVAILABLE" in error_str or "429" in error_str:
                        if attempt < max_retries - 1:
                            logger.warning(f"Attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            logger.error(f"All retries failed: {error_str}")
                            return self._get_fallback_response(task_description, f"API Error: {error_str}")
                    else:
                        logger.error(f"Gemini API Error: {error_str}")
                        return self._get_fallback_response(task_description, f"API Error: {error_str}")
            
            # Parse JSON from response
            response_text = response.text.strip()
            logger.debug(f"Raw AI Response: {response_text[:200]}...")
            
            # Remove markdown code blocks if present
            response_text = self._clean_response(response_text)
            
            try:
                estimate_data = json.loads(response_text)
                
                # Validate and format the response
                formatted_data = self._validate_and_format_response(estimate_data, task_description)
                formatted_data["success"] = True
                
                logger.info(f"Successfully parsed estimate for: {task_description[:50]}...")
                return formatted_data
                
            except json.JSONDecodeError as je:
                logger.warning(f"Failed to parse JSON: {je}. Response: {response_text[:200]}")
                return self._get_fallback_response(task_description, f"JSON Parse Error: {je}")
            
        except Exception as e:
            logger.error(f"Unexpected error in estimate_task: {str(e)}", exc_info=True)
            return self._get_fallback_response(task_description, f"Unexpected Error: {str(e)}")
    
    def _create_prompt(self, task_description: str) -> str:
        """Create the prompt for Gemini"""
        return f"""
You are a software project management assistant specialized in Kanban-based workflows.
Analyze the task below and return a STRICTLY VALID JSON response.

TASK DESCRIPTION:
{task_description}

Return JSON in this EXACT format:
{{
    "title": "Short action-based title (3-6 words, start with verb like Fix, Add, Update, Create)",
    "estimated_time": "string (e.g., '2 days', '1 week', '3 weeks')",
    "priority": "string (Low/Medium/High)",
    "complexity_level": "string (Low/Medium/High)",
    "dependencies": ["array of prerequisite tasks or systems"],
    "required_access": [
        "Specific access requirement 1 (e.g., 'GitHub Repository Write Access')",
        "Specific access requirement 2 (e.g., 'AWS Lambda Deployment Console')",
        "Specific access requirement 3 (e.g., 'PostgreSQL Database Admin Rights')"
    ],
    "suggested_labels": ["array", "of", "labels"],
    "reasoning": "MUST BE IN THIS EXACT FORMAT (see below)"
}}

CRITICAL: The "reasoning" field MUST follow this EXACT structure:

"Phase 1: Technical Breakdown
Overview: [Write 3-4 concise technical sentences describing the approach, architecture, or key technologies involved. Be specific about the technical stack and implementation strategy.]

Phase 1: [First milestone name]
- [Specific task 1]
- [Specific task 2]
- [Specific task 3]

Phase 2: [Second milestone name]
- [Specific task 1]
- [Specific task 2]
- [Specific task 3]

Phase 3: [Third milestone name]
- [Specific task 1]
- [Specific task 2]
- [Specific task 3]"

IMPORTANT for required_access:
- Be specific about exact access needed for THIS TASK
- Include service/tool name (GitHub, AWS, PostgreSQL, Slack, Telegram, etc.)
- Specify access type (Read, Write, Admin, Console, etc.)

Analyze the task and provide realistic, practical estimates.
"""
    
    def _clean_response(self, response_text: str) -> str:
        """Clean the response text"""
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        return response_text.strip()
    
    def _validate_and_format_response(self, data: Dict, task_description: str) -> Dict:
        """Validate and format the response data"""
        # Ensure required_access is always an array
        if 'required_access' in data:
            if isinstance(data['required_access'], str):
                data['required_access'] = [data['required_access']]
        
        # Ensure dependencies is always an array
        if 'dependencies' in data:
            if isinstance(data['dependencies'], str):
                data['dependencies'] = [data['dependencies']]
        
        # Ensure suggested_labels is always an array
        if 'suggested_labels' in data:
            if isinstance(data['suggested_labels'], str):
                data['suggested_labels'] = [data['suggested_labels']]
        
        return data
    
    def _get_fallback_response(self, task_description: str, error: str = None) -> Dict[str, Any]:
        """Generate a fallback response when AI fails"""
        logger.warning(f"Using fallback response for: {task_description[:50]}...")
        
        return {
            "success": False,
            "error": error or "AI service temporarily unavailable",
            "title": f"Analysis: {task_description[:40]}...",
            "estimated_time": "1-2 weeks",
            "priority": "Medium",
            "complexity_level": "Medium",
            "dependencies": ["Initial requirements gathering", "Technical review"],
            "required_access": [
                "Development Environment Access",
                "Version Control System (GitHub/GitLab)",
                "Testing Environment"
            ],
            "suggested_labels": ["feature", "development", "needs-review"],
            "reasoning": f"""Phase 1: Technical Breakdown
Overview: Manual technical analysis required for '{task_description[:100]}...'. Standard development workflow with modern tech stack. Requires environment setup, implementation, and deployment phases.

Phase 1: Requirements Analysis and Setup
- Review task requirements and define scope
- Set up development environment and tools
- Create project structure and initial configuration

Phase 2: Core Implementation
- Implement main functionality according to specifications
- Write comprehensive unit and integration tests
- Conduct code review and refactoring

Phase 3: Testing and Deployment
- Perform end-to-end testing in staging environment
- Create deployment documentation and runbooks
- Deploy to production with monitoring setup""",
            "fallback": True,
            "timestamp": datetime.now().isoformat()
        }
