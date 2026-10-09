# gemini_alternative.py (For OpenRouter or other providers)
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
        else:
            # Try using Google Gemini SDK
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                self.is_openrouter = False
                logger.info(f"Gemini client initialized with model: {self.model}")
            except Exception as e:
                logger.error(f"Error initializing Gemini: {e}")
                self.available = False
    
    def extract_candidate_data(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract structured candidate data from CV text"""
        if not self.available:
            logger.error("Gemini extractor not available")
            return None
        
        try:
            prompt = self._build_extraction_prompt(text)
            
            if self.is_openrouter:
                response = self._call_openrouter(prompt)
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
                response = self._call_openrouter(prompt)
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
                response = self._call_openrouter(prompt)
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
    
    def _call_openrouter(self, prompt: str) -> Optional[str]:
        """Call OpenRouter API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            response = requests.post(
                self.api_base,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('choices', [{}])[0].get('message', {}).get('content', '')
            else:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling OpenRouter: {e}")
            return None
    
    def _build_extraction_prompt(self, text: str) -> str:
        """Build prompt for candidate data extraction"""
        return f"""
        You are a specialized CV parser. Extract the following information from the CV text and return it as a JSON object.
        
        CV TEXT:
        {text[:5000]}
        
        Return a JSON object with this exact structure:
        {{
          "full_name": "",
          "email": "",
          "phone": "",
          "location": "",
          "linkedin": "",
          "github": "",
          "portfolio": "",
          "professional_summary": "",
          "skills": [
            {{"name": "", "years": 0}}
          ],
          "languages": [
            {{"language": "", "proficiency": ""}}
          ],
          "education": [
            {{
              "institution": "",
              "degree": "",
              "field": "",
              "year": ""
            }}
          ],
          "experience": [
            {{
              "company": "",
              "position": "",
              "start_date": "",
              "end_date": "",
              "duration": "",
              "description": ""
            }}
          ],
          "certifications": [
            {{"name": "", "issuer": "", "year": ""}}
          ],
          "projects": [
            {{"name": "", "description": "", "technologies": "", "url": ""}}
          ],
          "awards": [
            {{"name": "", "issuer": "", "year": ""}}
          ],
          "references": [],
          "estimated_years_experience": 0,
          "career_level": "Junior/Mid/Senior/Lead",
          "recommended_department": "",
          "confidence": 0.95
        }}
        
        Important:
        1. Extract only information explicitly found in the text
        2. For dates, use format YYYY-MM-DD or YYYY
        3. For confidence, rate from 0.0 to 1.0
        4. If a field is not found, use empty string or empty array as appropriate
        5. Calculate estimated_years_experience from work experience dates if available
        6. Only include JSON in your response, no other text
        """
    
    def _build_job_prompt(self, text: str) -> str:
        """Build prompt for job requirements extraction"""
        return f"""
        You are a specialized job description analyzer. Extract the key requirements from this job description.
        
        JOB DESCRIPTION:
        {text[:5000]}
        
        Return a JSON object with this structure:
        {{
          "title": "",
          "required_skills": [],
          "preferred_skills": [],
          "min_experience_years": 0,
          "education_requirements": "",
          "responsibilities": [],
          "keywords": []
        }}
        
        Only include JSON in your response, no other text.
        """
    
    def _build_match_prompt(self, candidate_data: Dict, job_requirements: Dict) -> str:
        """Build prompt for matching candidate to job"""
        return f"""
        You are a hiring expert. Compare the candidate profile with the job requirements and provide a match analysis.
        
        CANDIDATE PROFILE:
        {json.dumps(candidate_data, indent=2)}
        
        JOB REQUIREMENTS:
        {json.dumps(job_requirements, indent=2)}
        
        Return a JSON object with this structure:
        {{
          "match_score": 85.0,
          "strengths": ["Strong Python skills", "Relevant experience"],
          "weaknesses": ["Missing Docker experience"],
          "recommendation": "Interview",
          "detailed_analysis": "Detailed analysis text here"
        }}
        
        Only include JSON in your response, no other text.
        """
    
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
            if key in ['skills', 'languages', 'education', 'experience', 'certifications', 
                      'projects', 'awards', 'references']:
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