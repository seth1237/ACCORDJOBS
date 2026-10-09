# scoring.py
import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class CandidateScorer:
    def __init__(self):
        self.weights = {
            'experience': 0.25,
            'skills_match': 0.30,
            'education': 0.15,
            'projects': 0.10,
            'certifications': 0.10,
            'career_level_match': 0.10
        }
    
    def calculate_score(self, candidate_data: Dict, job_requirements: Dict = None) -> Dict:
        """Calculate overall score for a candidate"""
        if not candidate_data:
            return {'total_score': 0, 'details': {}}
        
        scores = {}
        
        # Experience score
        scores['experience'] = self._score_experience(
            candidate_data.get('experience', []),
            candidate_data.get('estimated_years_experience', 0),
            job_requirements
        )
        
        # Skills score
        scores['skills_match'] = self._score_skills(
            candidate_data.get('skills', []),
            job_requirements.get('required_skills', []) if job_requirements else []
        )
        
        # Education score
        scores['education'] = self._score_education(
            candidate_data.get('education', []),
            job_requirements.get('education_requirements', '') if job_requirements else ''
        )
        
        # Projects score
        scores['projects'] = self._score_projects(
            candidate_data.get('projects', [])
        )
        
        # Certifications score
        scores['certifications'] = self._score_certifications(
            candidate_data.get('certifications', [])
        )
        
        # Career level match
        scores['career_level_match'] = self._score_career_level(
            candidate_data.get('career_level', ''),
            job_requirements.get('title', '') if job_requirements else ''
        )
        
        # Calculate weighted total
        total_score = 0
        for key, score in scores.items():
            total_score += score * self.weights.get(key, 0)
        
        total_score = min(100, total_score * 100)
        
        return {
            'total_score': round(total_score, 1),
            'details': {k: round(v * 100, 1) for k, v in scores.items()},
            'recommendation': self._get_recommendation(total_score)
        }
    
    def _score_experience(self, experience: List[Dict], total_years: float, job_req: Dict = None) -> float:
        """Score candidate's experience"""
        if not experience:
            return 0.0
        
        # Base score on total years
        if total_years >= 10:
            years_score = 1.0
        elif total_years >= 7:
            years_score = 0.9
        elif total_years >= 5:
            years_score = 0.8
        elif total_years >= 3:
            years_score = 0.7
        elif total_years >= 1:
            years_score = 0.5
        else:
            years_score = 0.3
        
        # Check relevance if job requirements exist
        relevance_score = 1.0
        if job_req and 'title' in job_req:
            # Simple relevance check - look for job title in experience
            job_title_keywords = job_req.get('title', '').lower().split()
            relevance_score = 0.6  # Default relevance
            
            max_relevance = 0
            for exp in experience:
                position = exp.get('position', '').lower()
                company = exp.get('company', '').lower()
                combined = f"{position} {company}"
                
                # Calculate keyword matches
                matches = sum(1 for keyword in job_title_keywords if keyword in combined)
                if matches > 0:
                    relevance = min(1.0, matches / len(job_title_keywords))
                    max_relevance = max(max_relevance, relevance)
            
            if max_relevance > 0:
                relevance_score = max_relevance
        
        return (years_score * 0.6 + relevance_score * 0.4)
    
    def _score_skills(self, candidate_skills: List[Dict], required_skills: List[str]) -> float:
        """Score candidate's skills against requirements"""
        if not candidate_skills or not required_skills:
            return 0.5  # Neutral if no skills or no requirements
        
        candidate_skill_names = {s.get('name', '').lower() for s in candidate_skills}
        required_skill_names = {s.lower() for s in required_skills}
        
        if not required_skill_names:
            return 1.0
        
        # Calculate matches
        matches = required_skill_names.intersection(candidate_skill_names)
        match_count = len(matches)
        match_ratio = match_count / len(required_skill_names)
        
        # Check skill levels/years
        years_bonus = 0
        for skill in candidate_skills:
            skill_name = skill.get('name', '').lower()
            years = skill.get('years', 0)
            if skill_name in required_skill_names and years >= 3:
                years_bonus += 0.05
        
        years_bonus = min(0.2, years_bonus)
        
        return min(1.0, match_ratio + years_bonus)
    
    def _score_education(self, education: List[Dict], education_requirement: str) -> float:
        """Score candidate's education"""
        if not education:
            return 0.3
        
        # Define education levels
        levels = {
            'phd': 1.0,
            'doctorate': 1.0,
            'masters': 0.9,
            'ms': 0.9,
            'ma': 0.9,
            'mba': 0.9,
            'bachelors': 0.7,
            'bs': 0.7,
            'ba': 0.7,
            'associate': 0.5,
            'high school': 0.3
        }
        
        # Find highest level
        highest_score = 0.3
        for edu in education:
            degree = edu.get('degree', '').lower()
            for level, score in levels.items():
                if level in degree:
                    highest_score = max(highest_score, score)
        
        # Check if it meets requirements
        if education_requirement:
            req_lower = education_requirement.lower()
            if 'phd' in req_lower or 'doctorate' in req_lower:
                required_score = 0.9
            elif 'master' in req_lower:
                required_score = 0.8
            elif 'bachelor' in req_lower:
                required_score = 0.6
            else:
                required_score = 0.5
            
            if highest_score >= required_score:
                return highest_score
            else:
                return 0.3
        else:
            return highest_score
    
    def _score_projects(self, projects: List[Dict]) -> float:
        """Score candidate's projects"""
        if not projects:
            return 0.2
        
        # Score based on number and quality of projects
        num_projects = len(projects)
        
        if num_projects >= 5:
            base_score = 1.0
        elif num_projects >= 3:
            base_score = 0.8
        elif num_projects >= 1:
            base_score = 0.6
        else:
            base_score = 0.2
        
        # Check if projects have descriptions
        quality_score = 0
        for project in projects:
            if project.get('description'):
                quality_score += 0.2
            if project.get('technologies'):
                quality_score += 0.2
            if project.get('url'):
                quality_score += 0.1
        
        quality_score = min(1.0, quality_score)
        
        return base_score * 0.6 + quality_score * 0.4
    
    def _score_certifications(self, certifications: List[Dict]) -> float:
        """Score candidate's certifications"""
        if not certifications:
            return 0.2
        
        num_certs = len(certifications)
        
        if num_certs >= 5:
            return 1.0
        elif num_certs >= 3:
            return 0.8
        elif num_certs >= 1:
            return 0.6
        else:
            return 0.2
    
    def _score_career_level(self, career_level: str, job_title: str) -> float:
        """Score career level match"""
        if not career_level or not job_title:
            return 0.5
        
        career_level = career_level.lower()
        job_title = job_title.lower()
        
        # Map career levels to positions
        level_map = {
            'senior': ['senior', 'lead', 'principal', 'manager', 'director'],
            'mid': ['mid', 'intermediate', 'staff'],
            'junior': ['junior', 'entry', 'trainee', 'associate']
        }
        
        for level, keywords in level_map.items():
            if level in career_level:
                # Check if job title matches career level
                for keyword in keywords:
                    if keyword in job_title:
                        return 1.0
                return 0.6
        
        return 0.5
    
    def _get_recommendation(self, score: float) -> str:
        """Get recommendation based on score"""
        if score >= 80:
            return "Strong Interview"
        elif score >= 70:
            return "Interview"
        elif score >= 60:
            return "Consider"
        elif score >= 40:
            return "Maybe"
        else:
            return "Reject"