# job_matcher.py
import logging
from typing import Dict, Any, List
import json

from gemini import GeminiExtractor
from scoring import CandidateScorer

logger = logging.getLogger(__name__)

class JobMatcher:
    def __init__(self):
        self.gemini = GeminiExtractor()
        self.scorer = CandidateScorer()
    
    def parse_job_description(self, text: str) -> Dict:
        """Parse job description to extract requirements"""
        if self.gemini.available:
            return self.gemini.extract_job_requirements(text)
        return self._fallback_job_parse(text)
    
    def match_candidate(self, candidate_data: Dict, job_requirements: Dict) -> Dict:
        """Match a candidate against job requirements"""
        result = {
            'candidate_name': candidate_data.get('full_name', 'Unknown'),
            'job_title': job_requirements.get('title', 'Unknown'),
            'score': 0,
            'strengths': [],
            'weaknesses': [],
            'recommendation': '',
            'details': {}
        }
        
        # Use Gemini for matching if available
        if self.gemini.available:
            gemini_match = self.gemini.match_candidate_to_job(candidate_data, job_requirements)
            if gemini_match and 'match_score' in gemini_match:
                result['score'] = gemini_match.get('match_score', 0)
                result['strengths'] = gemini_match.get('strengths', [])
                result['weaknesses'] = gemini_match.get('weaknesses', [])
                result['recommendation'] = gemini_match.get('recommendation', '')
                result['details'] = gemini_match.get('detailed_analysis', '')
                return result
        
        # Fallback to rule-based scoring
        score_result = self.scorer.calculate_score(candidate_data, job_requirements)
        result['score'] = score_result.get('total_score', 0)
        result['recommendation'] = score_result.get('recommendation', '')
        result['details'] = score_result.get('details', {})
        
        # Generate strengths and weaknesses
        strengths, weaknesses = self._generate_strengths_weaknesses(candidate_data, job_requirements, result['score'])
        result['strengths'] = strengths
        result['weaknesses'] = weaknesses
        
        return result
    
    def match_all_candidates(self, candidates: List[Dict], job_requirements: Dict) -> List[Dict]:
        """Match multiple candidates against job requirements"""
        results = []
        
        for candidate in candidates:
            match = self.match_candidate(candidate, job_requirements)
            match['candidate_id'] = candidate.get('id')
            results.append(match)
        
        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results
    
    def _fallback_job_parse(self, text: str) -> Dict:
        """Fallback job parsing without Gemini"""
        import re
        
        requirements = {
            'title': '',
            'required_skills': [],
            'preferred_skills': [],
            'min_experience_years': 0,
            'education_requirements': '',
            'responsibilities': [],
            'keywords': []
        }
        
        # Try to find title
        title_patterns = [
            r'(?:position|role|job title)[:\s]+([^\n\.]+)',
            r'^([^\n\.]+)\s*position',
            r'we are looking for a[n]?\s+([^\n\.]+)'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                requirements['title'] = match.group(1).strip()
                break
        
        # Extract skills
        skill_patterns = [
            r'(?:required|key|essential)\s+skills?[:\s]+([^\n]+)',
            r'skills?[:\s]+([^\n]+)',
            r'(?:proficient|experience)\s+in\s+([^\n\.]+)'
        ]
        
        skills_found = []
        for pattern in skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Split by commas or "and"
                skills = re.split(r',\s*|\s+and\s+', match)
                skills_found.extend([s.strip() for s in skills if s.strip()])
        
        requirements['required_skills'] = skills_found[:10]
        
        # Extract years of experience
        exp_pattern = r'(\d+)\s*\+\s*years?\s+of\s+experience'
        match = re.search(exp_pattern, text, re.IGNORECASE)
        if match:
            requirements['min_experience_years'] = int(match.group(1))
        
        return requirements
    
    def _generate_strengths_weaknesses(self, candidate: Dict, job: Dict, score: float) -> tuple:
        """Generate strengths and weaknesses based on comparison"""
        strengths = []
        weaknesses = []
        
        # Check skills
        candidate_skills = {s.get('name', '').lower() for s in candidate.get('skills', [])}
        required_skills = {s.lower() for s in job.get('required_skills', [])}
        
        if required_skills:
            matching_skills = candidate_skills.intersection(required_skills)
            missing_skills = required_skills - candidate_skills
            
            if matching_skills:
                strengths.append(f"Has required skills: {', '.join(list(matching_skills)[:3])}")
            
            if missing_skills:
                weaknesses.append(f"Missing skills: {', '.join(list(missing_skills)[:3])}")
        
        # Check experience
        estimated_years = candidate.get('estimated_years_experience', 0)
        required_years = job.get('min_experience_years', 0)
        
        if required_years > 0:
            if estimated_years >= required_years:
                strengths.append(f"Has {estimated_years} years of experience (meets {required_years} year requirement)")
            else:
                weaknesses.append(f"Only {estimated_years} years of experience (needs {required_years} years)")
        
        # Check education
        education = candidate.get('education', [])
        edu_requirement = job.get('education_requirements', '')
        
        if edu_requirement and education:
            highest_degree = max(education, key=lambda x: x.get('year', '0') if x.get('year', '').isdigit() else '0')
            degree = highest_degree.get('degree', '')
            if degree:
                strengths.append(f"Has {degree}")
        
        # Career level
        if candidate.get('career_level') and job.get('title'):
            strengths.append(f"Career level: {candidate.get('career_level')}")
        
        # Projects
        if candidate.get('projects'):
            strengths.append(f"Has {len(candidate.get('projects', []))} projects")
        
        # Certifications
        if candidate.get('certifications'):
            strengths.append(f"Has {len(candidate.get('certifications', []))} certifications")
        
        # Limit strengths and weaknesses
        strengths = strengths[:3] if len(strengths) > 3 else strengths
        weaknesses = weaknesses[:3] if len(weaknesses) > 3 else weaknesses
        
        # If no weaknesses but score is less than perfect, add generic weakness
        if not weaknesses and score < 100:
            weaknesses.append("Could further optimize skills matching")
        
        return strengths, weaknesses