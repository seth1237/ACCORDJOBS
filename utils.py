# utils.py
import hashlib
import logging
import os
import re
from typing import Optional
from datetime import datetime
import magic

from config import Config

logger = logging.getLogger(__name__)

def file_hash(file_path: str) -> str:
    """Generate SHA-256 hash of a file"""
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logger.error(f"Error hashing file {file_path}: {e}")
        return ""

def get_file_extension(file_path: str) -> str:
    """Get file extension"""
    return os.path.splitext(file_path)[1].lower()

def get_file_mime_type(file_path: str) -> str:
    """Get MIME type of file"""
    try:
        return magic.from_file(file_path, mime=True)
    except:
        return "application/octet-stream"

def is_supported_file(file_path: str) -> bool:
    """Check if file is supported"""
    extension = get_file_extension(file_path)
    return extension in Config.SUPPORTED_EXTENSIONS

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    phone = re.sub(r'[\s\-\(\)\.]', '', phone)
    return len(phone) >= 10 and phone.isdigit()

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters but keep useful ones
    text = re.sub(r'[^\w\s\.,;:!?@#$%&*()+\-=<>]', '', text)
    return text.strip()

def extract_years_from_text(text: str) -> float:
    """Extract years of experience from text"""
    patterns = [
        r'(\d+)\s*years?\s*of\s*experience',
        r'experience\s*:\s*(\d+)\s*years?',
        r'(\d+)\s*\+\s*years?',
        r'(\d+)\s*yrs?\s*exp',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    
    # Try to find standalone numbers
    years_found = re.findall(r'(\d+)\s*(?:years?|yrs?)', text, re.IGNORECASE)
    if years_found:
        return float(max(years_found))
    
    return 0.0

def parse_date(date_string: str) -> Optional[datetime]:
    """Parse date from various formats"""
    formats = [
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%m/%d/%Y',
        '%d-%m-%Y',
        '%b %Y',
        '%B %Y',
        '%Y'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string.strip(), fmt)
        except:
            continue
    
    return None

def calculate_duration(start_date: str, end_date: str) -> str:
    """Calculate duration between two dates"""
    try:
        start = parse_date(start_date)
        end = parse_date(end_date) if end_date else datetime.now()
        
        if start and end:
            years = end.year - start.year
            months = end.month - start.month
            
            if months < 0:
                years -= 1
                months += 12
            
            if years > 0 and months > 0:
                return f"{years} year{'s' if years > 1 else ''}, {months} month{'s' if months > 1 else ''}"
            elif years > 0:
                return f"{years} year{'s' if years > 1 else ''}"
            elif months > 0:
                return f"{months} month{'s' if months > 1 else ''}"
            else:
                return "Less than a month"
    except:
        pass
    
    return "Unknown"

def ensure_directory(path: str):
    """Ensure directory exists"""
    if not os.path.exists(path):
        os.makedirs(path)