# setup.py
import os
import sys
import subprocess

def setup_project():
    """Setup the ATS project"""
    
    print("Setting up AI-Powered ATS...")
    
    # Create directories
    directories = ['CVs', 'output', 'database', 'logs']
    for dir_name in directories:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"Created directory: {dir_name}")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("Warning: Python 3.8+ is recommended")
    
    # Check for required packages
    try:
        import google.generativeai
        print("✓ Gemini SDK installed")
    except ImportError:
        print("✗ Gemini SDK not installed. Run: pip install google-generativeai")
    
    try:
        import PyPDF2
        print("✓ PyPDF2 installed")
    except ImportError:
        print("✗ PyPDF2 not installed. Run: pip install PyPDF2")
    
    try:
        import docx
        print("✓ python-docx installed")
    except ImportError:
        print("✗ python-docx not installed. Run: pip install python-docx")
    
    # Check .env file
    if not os.path.exists('.env'):
        print("\n⚠️  .env file not found. Create one from .env.example")
        if os.path.exists('.env.example'):
            import shutil
            shutil.copy('.env.example', '.env')
            print("Created .env from .env.example")
            print("Please edit .env with your credentials")
    
    print("\n✅ Setup complete!")
    print("\nTo run the ATS:")
    print("  1. Edit .env with your credentials")
    print("  2. Run: python main.py")
    print("  3. To view dashboard: python dashboard_server.py")
    print("\nHappy recruiting! 🚀")

if __name__ == '__main__':
    setup_project()