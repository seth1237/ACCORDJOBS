# config.py - Updated
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Email Configuration (IMAP for receiving)
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'mail.astermedsupplies.co.ke')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 993))
    EMAIL_USER = os.getenv('EMAIL_USER', '')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
    EMAIL_FOLDER = os.getenv('EMAIL_FOLDER', 'INBOX')
    EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'true').lower() == 'true'
    # Newest messages only. Older mail is not opened and flags are not changed.
    RECENT_EMAIL_LIMIT = int(os.getenv('RECENT_EMAIL_LIMIT', 720))
    
    # SMTP Configuration (for sending - optional)
    SMTP_HOST = os.getenv('SMTP_HOST', 'mail.astermedsupplies.co.ke')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASS = os.getenv('SMTP_PASS', '')
    SMTP_FROM = os.getenv('SMTP_FROM', '')
    SYSTEM_FROM_NAME = os.getenv('SYSTEM_FROM_NAME', 'Elevate HR Platform')
    
    # Gemini Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'google/gemini-2.0-flash-exp:free')
    # Off by default. The mailbox import scores CVs locally. Set true only
    # for a one-off pass that may call the language API.
    USE_AI_EXTRACTION = os.getenv('USE_AI_EXTRACTION', 'false').lower() == 'true'
    
    # Database Configuration
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'database/candidates.db')
    
    # Storage Paths
    CV_STORAGE_PATH = os.getenv('CV_STORAGE_PATH', 'CVs/')
    DOCUMENTS_PATH = os.getenv('DOCUMENTS_PATH', 'documents/')
    OUTPUT_PATH = os.getenv('OUTPUT_PATH', 'output/')
    LOG_PATH = os.getenv('LOG_PATH', 'logs/')
    
    # Processing Configuration
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', 4))
    SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.doc', '.txt', '.rtf', '.jpg', '.jpeg', '.png']
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 10485760))  # 10MB
    
    # Scoring Configuration
    MIN_SCORE_FOR_INTERVIEW = float(os.getenv('MIN_SCORE_FOR_INTERVIEW', 70.0))

    # Review-screen login. This is not the mailbox password.
    DASHBOARD_EMAIL = os.getenv('DASHBOARD_EMAIL', 'hr@accordmedical.co.ke')
    DASHBOARD_PASSWORD = os.getenv('DASHBOARD_PASSWORD', 'hr123')
    DASHBOARD_NAME = os.getenv('DASHBOARD_NAME', 'HR')
    SECRET_KEY = os.getenv('SECRET_KEY', 'accord-medical-hr-review-local')