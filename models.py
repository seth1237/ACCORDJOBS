# models.py
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class Candidate:
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""
    professional_summary: str = ""
    estimated_years_experience: float = 0.0
    career_level: str = ""
    recommended_department: str = ""
    confidence: float = 0.0
    file_hash: str = ""
    file_name: str = ""
    file_path: str = ""
    skills: List[dict] = field(default_factory=list)
    experience: List[dict] = field(default_factory=list)
    education: List[dict] = field(default_factory=list)
    certifications: List[dict] = field(default_factory=list)
    projects: List[dict] = field(default_factory=list)
    languages: List[dict] = field(default_factory=list)
    awards: List[dict] = field(default_factory=list)
    score: float = 0.0
    status: str = "pending"
    created_at: Optional[datetime] = None

@dataclass
class Email:
    subject: str = ""
    sender: str = ""
    body: str = ""
    date: Optional[datetime] = None
    attachments: List[str] = field(default_factory=list)
    saved_files: List[dict] = field(default_factory=list)
    message_id: str = ""

@dataclass
class JobDescription:
    title: str = ""
    description: str = ""
    requirements: str = ""
    is_active: bool = True

@dataclass
class MatchResult:
    candidate_id: int
    job_id: int
    match_score: float
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendation: str = ""