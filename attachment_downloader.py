# attachment_downloader.py
import os
import imaplib
import email
from email.header import decode_header
import logging
from typing import List, Optional
import requests
from urllib.parse import urlparse

from config import Config
from utils import ensure_directory, get_file_extension, is_supported_file

logger = logging.getLogger(__name__)

class AttachmentDownloader:
    def __init__(self, storage_path: str = Config.CV_STORAGE_PATH):
        self.storage_path = storage_path
        ensure_directory(storage_path)
    
    def download_attachments_from_email(self, email_msg, email_id: str) -> List[str]:
        """Download all attachments from email message"""
        downloaded_files = []
        
        try:
            if not email_msg.is_multipart():
                return []

            for part in email_msg.walk():
                content_disposition = str(part.get('Content-Disposition', ''))
                
                if 'attachment' in content_disposition.lower():
                    filename = part.get_filename()
                    if filename:
                        filename = self._decode_filename(filename)
                        
                        # Check if it's a supported file
                        if not is_supported_file(filename):
                            continue
                        
                        # Save the attachment
                        file_path = self._save_attachment(part, filename, email_id)
                        if file_path:
                            downloaded_files.append(file_path)
            
            logger.info(f"Downloaded {len(downloaded_files)} attachments from email {email_id}")
            
        except Exception as e:
            logger.error(f"Error downloading attachments: {e}")
        
        return downloaded_files

    def download_from_email(self, email_msg, email_id: str) -> List[str]:
        """Download attachments from email message"""
        downloaded_files = []
        
        try:
            if not email_msg.is_multipart():
                return []
            
            for part in email_msg.walk():
                content_disposition = str(part.get('Content-Disposition', ''))
                
                if 'attachment' in content_disposition.lower():
                    filename = part.get_filename()
                    if filename:
                        filename = self._decode_filename(filename)
                        
                        # Check if it's a supported file
                        if not is_supported_file(filename):
                            continue
                        
                        # Save the attachment
                        file_path = self._save_attachment(part, filename, email_id)
                        if file_path:
                            downloaded_files.append(file_path)
            
            logger.info(f"Downloaded {len(downloaded_files)} attachments from email {email_id}")
            
        except Exception as e:
            logger.error(f"Error downloading attachments: {e}")
        
        return downloaded_files
    
    def download_from_url(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """Download attachment from URL"""
        try:
            # Generate filename if not provided
            if not filename:
                filename = os.path.basename(urlparse(url).path)
                if not filename:
                    filename = f"cv_{hash(url)}.pdf"
            
            # Check if supported
            if not is_supported_file(filename):
                return None
            
            # Download file
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Save file
            file_path = os.path.join(self.storage_path, filename)
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error downloading from URL: {e}")
            return None
    
    def _save_attachment(self, part, filename: str, email_id: str) -> Optional[str]:
        """Save attachment to disk"""
        try:
            # Clean filename
            filename = self._sanitize_filename(filename)
            
            # Add email ID prefix to avoid conflicts
            base_filename, ext = os.path.splitext(filename)
            filename = f"{email_id}_{base_filename}{ext}"
            
            file_path = os.path.join(self.storage_path, filename)
            
            # Check if file already exists
            if os.path.exists(file_path):
                # Add timestamp to avoid overwriting
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{email_id}_{base_filename}_{timestamp}{ext}"
                file_path = os.path.join(self.storage_path, filename)
            
            # Save file
            with open(file_path, 'wb') as f:
                payload = part.get_payload(decode=True)
                if payload:
                    f.write(payload)
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving attachment {filename}: {e}")
            return None
    
    def _decode_filename(self, filename) -> str:
        """Decode email filename"""
        if isinstance(filename, bytes):
            try:
                filename = filename.decode('utf-8', errors='ignore')
            except:
                filename = str(filename)
        
        # Handle encoded filenames
        if '=?' in filename:
            parts = filename.split('?')
            if len(parts) >= 3:
                try:
                    import base64
                    decoded = base64.b64decode(parts[3])
                    filename = decoded.decode('utf-8', errors='ignore')
                except:
                    pass
        
        return filename
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename"""
        # Remove path traversal characters
        filename = filename.replace('/', '_').replace('\\', '_')
        # Remove other problematic characters
        import re
        filename = re.sub(r'[<>:"|?*]', '_', filename)
        return filename.strip()