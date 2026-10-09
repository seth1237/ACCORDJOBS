# ocr.py
import logging
import os
from typing import Optional

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logging.warning("OCR libraries not installed. Install pytesseract and Pillow for image text extraction.")

logger = logging.getLogger(__name__)

class OCRProcessor:
    def __init__(self):
        self.available = OCR_AVAILABLE
        if self.available:
            # Try to set tesseract path (common locations)
            import sys
            if sys.platform == 'win32':
                # Windows common paths
                paths = [
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                ]
                for path in paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        break
            elif sys.platform == 'linux':
                # Linux - tesseract is usually in PATH
                pass
            elif sys.platform == 'darwin':
                # macOS - tesseract is usually in PATH
                pass
    
    def extract_text_from_image(self, image_path: str) -> Optional[str]:
        """Extract text from image using OCR"""
        if not self.available:
            logger.warning("OCR not available")
            return None
        
        try:
            # Open image
            image = Image.open(image_path)
            
            # Preprocess image for better OCR
            image = self._preprocess_image(image)
            
            # Extract text
            text = pytesseract.image_to_string(image)
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting text from image {image_path}: {e}")
            return None
    
    def _preprocess_image(self, image):
        """Preprocess image for better OCR results"""
        try:
            # Convert to grayscale if not already
            if image.mode != 'L':
                image = image.convert('L')
            
            # Increase contrast
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Resize if too small
            width, height = image.size
            if width < 1000:
                scale_factor = 1000 / width
                new_size = (int(width * scale_factor), int(height * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            return image
        except:
            return image
    
    def is_image_file(self, file_path: str) -> bool:
        """Check if file is an image"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'}
        ext = os.path.splitext(file_path)[1].lower()
        return ext in image_extensions