# parser.py
import os
import logging
from typing import Optional

# PDF extraction
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logging.warning("PyPDF2 not installed. PDF extraction will be limited.")

# DOCX extraction
try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logging.warning("python-docx not installed. DOCX extraction will be limited.")

# DOC extraction (using antiword or catdoc)
try:
    import subprocess
    DOC_AVAILABLE = True
except:
    DOC_AVAILABLE = False

from config import Config
from utils import get_file_extension
from ocr import OCRProcessor

logger = logging.getLogger(__name__)

class TextExtractor:
    def __init__(self):
        self.ocr = OCRProcessor()
    
    def extract_text(self, file_path: str) -> Optional[str]:
        """Extract text from various file formats"""
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
        
        extension = get_file_extension(file_path)
        
        if extension == '.pdf':
            return self._extract_pdf(file_path)
        elif extension in ['.docx', '.docm']:
            return self._extract_docx(file_path)
        elif extension == '.doc':
            return self._extract_doc(file_path)
        elif extension in ['.txt', '.rtf']:
            return self._extract_text_file(file_path)
        elif extension in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
            return self._extract_image(file_path)
        else:
            logger.warning(f"Unsupported file format: {extension}")
            return None
    
    def _extract_pdf(self, file_path: str) -> Optional[str]:
        """Extract text from PDF"""
        if not PDF_AVAILABLE:
            logger.warning("PyPDF2 not available, PDF extraction skipped")
            return None
        
        try:
            text = ""
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting PDF {file_path}: {e}")
            return None
    
    def _extract_docx(self, file_path: str) -> Optional[str]:
        """Extract text from DOCX"""
        if not DOCX_AVAILABLE:
            logger.warning("python-docx not available, DOCX extraction skipped")
            return None
        
        try:
            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting DOCX {file_path}: {e}")
            return None
    
    def _extract_doc(self, file_path: str) -> Optional[str]:
        """Extract text from DOC using antiword or catdoc"""
        try:
            # Try antiword (better for Word documents)
            result = subprocess.run(
                ['antiword', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        try:
            # Try catdoc as fallback
            result = subprocess.run(
                ['catdoc', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        logger.warning(f"Could not extract DOC file: {file_path}")
        return None
    
    def _extract_text_file(self, file_path: str) -> Optional[str]:
        """Extract text from plain text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read().strip()
            except Exception as e:
                logger.error(f"Error reading text file {file_path}: {e}")
                return None
    
    def _extract_image(self, file_path: str) -> Optional[str]:
        """Extract text from image using OCR"""
        return self.ocr.extract_text_from_image(file_path)