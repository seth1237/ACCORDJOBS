# gemini.py - Updated with working OpenRouter models
import json
import logging
from typing import Dict, Any, Optional
import re
import requests

from config import Config

logger = logging.getLogger(__name__)

class GeminiExtractor:
    def __init__(self):
        self.available = True
        self.api_key = Config.GEMINI_API_KEY
        self.model = Config.GEMINI_MODEL
        
        # Check if it's an OpenRouter key
        if self.api_key and self.api_key.startswith('sk-or-v1-'):
            logger.info("Using OpenRouter API")
            self.api_base = "https://openrouter.ai/api/v1/chat/completions"
            self.is_openrouter = True
            
            # Use a known working model if the configured one doesn't work
            # Try these models in order of preference
            self.models_to_try = [
                self.model,  # Try the configured model first
                "google/gemini-2.0-flash-lite-001",
                "google/gemini-1.5-flash-8b",
                "google/gemini-1.5-flash",
                "mistralai/mistral-7b-instruct:free",
                "meta-llama/llama-3.2-3b-instruct:free",
                "microsoft/phi-3-mini-128k-instruct:free"
            ]
        else:
            self.is_openrouter = False
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"Google Gemini client initialized with model: {self.model}")
            except Exception as e:
                logger.error(f"Error initializing Gemini: {e}")
                self.available = False
    
    def _call_openrouter_with_retry(self, prompt: str) -> Optional[str]:
        """Call OpenRouter API with model fallback"""
        last_error = None
        
        for model in self.models_to_try:
            try:
                logger.info(f"Trying OpenRouter model: {model}")
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:5000",
                    "X-Title": "ATS System"
                }
                
                data = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that extracts structured information from CVs."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
                
                response = requests.post(
                    self.api_base,
                    headers=headers,
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                    if content:
                        logger.info(f"Successfully used model: {model}")
                        return content
                else:
                    logger.warning(f"Model {model} failed: {response.status_code}")
                    if response.status_code == 404:
                        last_error = f"Model not found: {model}"
                    else:
                        last_error = f"HTTP {response.status_code}: {response.text[:100]}"
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Error with model {model}: {e}")
                continue
        
        logger.error(f"All models failed. Last error: {last_error}")
        return None
    
    def extract_candidate_data(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract structured candidate data from CV text"""
        if not self.available:
            logger.error("Gemini extractor not available")
            return None
        
        try:
            prompt = self._build_extraction_prompt(text)
            
            if self.is_openrouter:
                response = self._call_openrouter_with_retry(prompt)
            else:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )
                response = response.text if response else None
            
            if not response:
                logger.warning("No response from API")
                return None
            
            # Extract JSON from response
            json_str = self._extract_json(response)
            
            if not json_str:
                logger.warning("No JSON found in response")
                logger.debug(f"Response was: {response[:200]}...")
                return None
            
            data = json.loads(json_str)
            
            # Validate and clean data
            data = self._clean_extracted_data(data)
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting data: {e}")
            return None
    
    def extract_job_requirements(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract job requirements from job description"""
        if not self.available:
            logger.error("Gemini extractor not available")
            return None
        
        try:
            prompt = self._build_job_prompt(text)
            
            if self.is_openrouter:
                response = self._call_openrouter_with_retry(prompt)
            else:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )
                response = response.text if response else None
            
            if not response:
                logger.warning("No response from API")
                return None
            
            json_str = self._extract_json(response)
            
            if not json_str:
                logger.warning("No JSON found in response")
                return None
            
            return json.loads(json_str)
            
        except Exception as e:
            logger.error(f"Error extracting job requirements: {e}")
            return None
    
    def match_candidate_to_job(self, candidate_data: Dict, job_requirements: Dict) -> Dict:
        """Match candidate against job requirements"""
        if not self.available:
            return {"error": "API not available"}
        
        try:
            prompt = self._build_match_prompt(candidate_data, job_requirements)
            
            if self.is_openrouter:
                response = self._call_openrouter_with_retry(prompt)
            else:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )
                response = response.text if response else None
            
            if not response:
                return {"error": "No response from API"}
            
            json_str = self._extract_json(response)
            
            if not json_str:
                return {"error": "No JSON found in response"}
            
            return json.loads(json_str)
            
        except Exception as e:
            logger.error(f"Error matching candidate to job: {e}")
            return {"error": str(e)}
    
    def _build_extraction_prompt(self, text: str) -> str:
        """Build prompt for candidate data extraction"""
        return f"""Extract structured candidate data from this CV and return ONLY valid JSON.

CV TEXT:
{text[:3000]}

Return a JSON object with this structure:
{{
  "full_name": "",
  "email": "",
  "phone": "",
  "location": "",
  "professional_summary": "",
  "skills": [],
  "education": [],
  "experience": [],
  "certifications": [],
  "estimated_years_experience": 0,
  "career_level": ""
}}

Skills should be an array of objects: {{"name": "skill_name", "years": 0}}
Education: {{"institution": "", "degree": "", "field": "", "year": ""}}
Experience: {{"company": "", "position": "", "start_date": "", "end_date": "", "description": ""}}

Only include information found in the text. Use empty strings for missing fields."""
    
    def _build_job_prompt(self, text: str) -> str:
        """Build prompt for job requirements extraction"""
        return f"""Extract job requirements from this description and return ONLY valid JSON.

JOB DESCRIPTION:
{text[:3000]}

Return JSON: {{"title": "", "required_skills": [], "min_experience_years": 0, "education_requirements": ""}}"""
    
    def _build_match_prompt(self, candidate_data: Dict, job_requirements: Dict) -> str:
        """Build prompt for matching candidate to job"""
        return f"""Compare candidate to job requirements and return ONLY valid JSON.

CANDIDATE: {json.dumps(candidate_data, indent=2)}
JOB: {json.dumps(job_requirements, indent=2)}

Return: {{"match_score": 85, "strengths": [], "weaknesses": [], "recommendation": "Interview"}}"""
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from text"""
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group()
        
        json_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_block:
            return json_block.group(1)
        
        return None
    
    def _clean_extracted_data(self, data: Dict) -> Dict:
        """Clean and normalize extracted data"""
        cleaned = {}
        
        for key, value in data.items():
            if key in ['skills', 'languages', 'education', 'experience', 'certifications']:
                if isinstance(value, list):
                    cleaned[key] = [item for item in value if item and any(str(v).strip() for v in item.values() if v)]
                else:
                    cleaned[key] = value
            elif isinstance(value, str):
                cleaned[key] = value.strip()
            else:
                cleaned[key] = value
        
        for field in ['file_name', 'file_path', 'file_hash']:
            if field not in cleaned:
                cleaned[field] = ""
        
        return cleaned