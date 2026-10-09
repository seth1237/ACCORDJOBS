# test_system.py
import sys
import os

print("Testing ATS System...")
print("="*50)

# Test imports
try:
    print("Testing imports...")
    from config import Config
    print("✓ Config imported")
    
    from utils import file_hash, ensure_directory, is_supported_file
    print("✓ Utils imported")
    
    from ocr import OCRProcessor
    print("✓ OCR imported")
    
    from parser import TextExtractor
    print("✓ Parser imported")
    
    from gemini import GeminiExtractor
    print("✓ Gemini imported")
    
    from scoring import CandidateScorer
    print("✓ Scoring imported")
    
    from job_matcher import JobMatcher
    print("✓ Job Matcher imported")
    
    from database import Database
    print("✓ Database imported")
    
    from main import ATSProcessor
    print("✓ Main imported")
    
    print("\n✅ All imports successful!")
    
except ImportError as e:
    print(f"\n❌ Import failed: {e}")
    sys.exit(1)

# Test directories
print("\nTesting directories...")
directories = ['CVs', 'output', 'database', 'logs']
for dir_name in directories:
    if os.path.exists(dir_name):
        print(f"✓ {dir_name}/ exists")
    else:
        print(f"⚠️  {dir_name}/ does not exist - creating...")
        ensure_directory(dir_name)

print("\n✅ System test complete!")
