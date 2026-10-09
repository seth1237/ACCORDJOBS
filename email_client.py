# email_client.py - Updated with date range filtering
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import os
import logging
from typing import List, Optional
from datetime import datetime, timedelta
import re
import base64
import quopri
from email.utils import mktime_tz, parsedate_tz

from config import Config
from models import Email

logger = logging.getLogger(__name__)


def recent_sequence_window(total: int, count: int):
    """Oldest-to-newest sequence numbers for the newest `count` messages.

    IMAP sequence 1 is the oldest message in the folder. The newest message
    is `total`. A window of (281, 1000) means messages 1–280 are never fetched.
    """
    total = int(total or 0)
    count = int(count or 0)
    if total <= 0 or count <= 0:
        return 0, 0
    start = max(1, total - count + 1)
    return start, total

class EmailClient:
    def __init__(self):
        self.host = Config.EMAIL_HOST
        self.port = Config.EMAIL_PORT
        self.user = Config.EMAIL_USER
        self.password = Config.EMAIL_PASSWORD
        self.folder = Config.EMAIL_FOLDER
        self.use_ssl = getattr(Config, 'EMAIL_USE_SSL', True)
        self.connection = None
    
    def connect(self):
        """Connect to email server"""
        try:
            if self.use_ssl:
                self.connection = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                self.connection = imaplib.IMAP4(self.host, self.port)
            
            self.connection.login(self.user, self.password)
            self.connection.select(self.folder)
            logger.info(f"Connected to email server: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to email server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from email server"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except:
                pass
            self.connection = None
    
    def fetch_emails_by_date(self, start_date: str, end_date: str, limit: int = None) -> List[Email]:
        """Fetch emails within a date range"""
        if not self.connection:
            if not self.connect():
                return []
        
        emails = []
        
        try:
            # Convert dates to IMAP format (DD-MMM-YYYY)
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Add one day to end_date to include the full day
            end_dt = end_dt + timedelta(days=1)
            
            # Format for IMAP search
            start_imap = start_dt.strftime('%d-%b-%Y')
            end_imap = end_dt.strftime('%d-%b-%Y')
            
            logger.info(f"Searching for emails from {start_imap} to {end_imap}")
            
            # Search for emails in date range
            search_criteria = f'(SINCE "{start_imap}" BEFORE "{end_imap}")'
            status, messages = self.connection.search(None, search_criteria)
            
            if status != 'OK':
                logger.warning(f"No emails found in date range")
                return []
            
            message_ids = messages[0].split()
            logger.info(f"Found {len(message_ids)} emails in date range")
            
            # Filter for job application emails
            job_keywords = ['application', 'apply', 'cv', 'resume', 'curriculum vitae', 
                          'position', 'job', 'sales', 'engineer', 'technical', 
                          'biomedical', 'internship', 'opportunity', 'vacancy']
            
            filtered_ids = []
            for msg_id in message_ids:
                try:
                    # Fetch just the headers
                    status, msg_data = self.connection.fetch(msg_id, '(BODY.PEEK[HEADER])')
                    if status == 'OK' and msg_data and msg_data[0]:
                        header_data = msg_data[0][1]
                        if isinstance(header_data, bytes):
                            header_data = header_data.decode('utf-8', errors='ignore')
                        header_lower = header_data.lower()
                        
                        # Check if it's a job application
                        is_job = any(keyword in header_lower for keyword in job_keywords)
                        if is_job:
                            filtered_ids.append(msg_id)
                except Exception as e:
                    logger.debug(f"Error checking email: {e}")
                    continue
            
            logger.info(f"Found {len(filtered_ids)} job application emails in date range")
            
            # Limit if specified
            if limit and len(filtered_ids) > limit:
                filtered_ids = filtered_ids[-limit:]
            
            for msg_id in filtered_ids:
                try:
                    email_obj = self._fetch_single_email_safe(msg_id)
                    if email_obj:
                        emails.append(email_obj)
                        # Mark as read
                        try:
                            self.connection.store(msg_id, '+FLAGS', '\\Seen')
                        except:
                            pass
                except Exception as e:
                    logger.error(f"Error fetching email {msg_id}: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(emails)} job application emails from date range")
            
        except Exception as e:
            logger.error(f"Error fetching emails by date: {e}")
        
        return emails
    
    def fetch_recent_emails(self, count: int = 720) -> List[Email]:
        """Read only the newest `count` messages, without changing the mailbox.

        The folder is opened read-only. Messages are fetched with BODY.PEEK,
        which does not set the read flag. Anything older than this window
        is not requested.
        """
        if not self.connection:
            if not self.connect():
                return []

        emails = []
        try:
            status, data = self.connection.select(self.folder, readonly=True)
            if status != 'OK' or not data or not data[0]:
                logger.error("Could not open the mailbox read-only. Nothing was changed.")
                return []
            total = int(data[0])
            start, end = recent_sequence_window(total, count)
            if end == 0:
                logger.info("Mailbox is empty")
                return []
            logger.info(
                "Reading messages %s–%s of %s. Older mail is not opened.",
                start, end, total,
            )
            for seq in range(start, end + 1):
                msg_id = str(seq).encode()
                try:
                    if not self._header_might_have_cv(msg_id):
                        continue
                    email_obj = self._fetch_peek(msg_id)
                    if email_obj:
                        emails.append(email_obj)
                except Exception as exc:
                    logger.error(f"Error reading message {seq}: {exc}")
            logger.info(f"Read {len(emails)} messages with a CV or application from the newest {end - start + 1}")
        except Exception as exc:
            logger.error(f"Error reading recent mail: {exc}")
        return emails

    def _header_might_have_cv(self, msg_id) -> bool:
        """Peek the header only. A plain text note with no attachment is skipped."""
        status, msg_data = self.connection.fetch(msg_id, '(BODY.PEEK[HEADER])')
        if status != 'OK' or not msg_data:
            return False
        header = None
        for item in msg_data:
            if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], (bytes, bytearray)):
                header = item[1]
                break
        if header is None:
            return False
        header = header.decode('utf-8', errors='ignore')
        lowered = header.lower()
        if 'multipart/' in lowered or 'attachment' in lowered or 'filename' in lowered:
            return True
        keywords = (
            'application', 'apply', 'cv', 'resume', 'curriculum vitae',
            'position', 'job', 'vacancy', 'internship',
        )
        return any(keyword in lowered for keyword in keywords)

    def _fetch_peek(self, msg_id) -> Optional[Email]:
        """Download one message without setting the read flag."""
        status, data = self.connection.fetch(msg_id, '(BODY.PEEK[])')
        if status != 'OK' or not data:
            return None
        msg_data = None
        for item in data:
            if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], (bytes, bytearray)):
                msg_data = item[1]
                break
        if not msg_data:
            return None
        msg = email.message_from_bytes(msg_data)
        email_obj = Email()
        email_obj.subject = self._safe_decode_header(msg.get('Subject', ''))
        email_obj.sender = self._safe_decode_header(msg.get('From', ''))
        email_obj.message_id = msg.get('Message-ID', '')
        date_str = msg.get('Date', '')
        if date_str:
            try:
                date_tuple = parsedate_tz(date_str)
                if date_tuple:
                    email_obj.date = datetime.fromtimestamp(mktime_tz(date_tuple))
                else:
                    email_obj.date = datetime.now()
            except Exception:
                email_obj.date = datetime.now()
        else:
            email_obj.date = datetime.now()
        self._parse_email_content(msg, email_obj)
        return email_obj

    def fetch_unread_emails(self, limit: int = 50) -> List[Email]:
        """Fetch unread emails with attachments"""
        if not self.connection:
            if not self.connect():
                return []
        
        emails = []
        
        try:
            # Search for unread emails
            status, messages = self.connection.search(None, 'UNSEEN')
            
            if status != 'OK':
                logger.warning("No unread emails found")
                return []
            
            message_ids = messages[0].split()
            
            # Filter for job application emails
            job_keywords = ['application', 'apply', 'cv', 'resume', 'curriculum vitae', 
                          'position', 'job', 'sales', 'engineer', 'technical', 
                          'biomedical', 'internship', 'opportunity', 'vacancy']
            
            filtered_ids = []
            for msg_id in message_ids:
                try:
                    # Fetch just the headers
                    status, msg_data = self.connection.fetch(msg_id, '(BODY.PEEK[HEADER])')
                    if status == 'OK' and msg_data and msg_data[0]:
                        header_data = msg_data[0][1]
                        if isinstance(header_data, bytes):
                            header_data = header_data.decode('utf-8', errors='ignore')
                        header_lower = header_data.lower()
                        
                        # Check if it's a job application
                        is_job = any(keyword in header_lower for keyword in job_keywords)
                        if is_job:
                            filtered_ids.append(msg_id)
                        else:
                            # Mark non-job emails as read
                            try:
                                self.connection.store(msg_id, '+FLAGS', '\\Seen')
                            except:
                                pass
                except Exception as e:
                    logger.debug(f"Error checking email: {e}")
                    continue
            
            logger.info(f"Found {len(filtered_ids)} job application emails out of {len(message_ids)} total")
            
            # Limit the number of emails processed
            if limit and len(filtered_ids) > limit:
                filtered_ids = filtered_ids[-limit:]
            
            for msg_id in filtered_ids:
                try:
                    email_obj = self._fetch_single_email_safe(msg_id)
                    if email_obj:
                        emails.append(email_obj)
                        # Mark as read
                        try:
                            self.connection.store(msg_id, '+FLAGS', '\\Seen')
                        except:
                            pass
                except Exception as e:
                    logger.error(f"Error fetching email {msg_id}: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(emails)} job application emails")
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
        
        return emails
    
    def _fetch_single_email_safe(self, msg_id) -> Optional[Email]:
        """Fetch a single email using a safe method"""
        try:
            # Try multiple methods to fetch the email
            msg_data = None
            
            # Method 1: Try RFC822
            try:
                status, data = self.connection.fetch(msg_id, '(RFC822)')
                if status == 'OK' and data and data[0]:
                    msg_data = data[0][1]
            except:
                pass
            
            # Method 2: Try BODY.PEEK
            if not msg_data:
                try:
                    status, data = self.connection.fetch(msg_id, '(BODY.PEEK[])')
                    if status == 'OK' and data and data[0]:
                        msg_data = data[0][1]
                except:
                    pass
            
            # Method 3: Try using UID
            if not msg_data:
                try:
                    status, data = self.connection.uid('FETCH', msg_id, '(BODY.PEEK[])')
                    if status == 'OK' and data and data[0]:
                        msg_data = data[0][1]
                except:
                    pass
            
            if not msg_data:
                logger.warning(f"Could not fetch email content for {msg_id}")
                return None
            
            # Parse the email
            msg = email.message_from_bytes(msg_data)
            
            # Create email object
            email_obj = Email()
            
            # Parse headers
            email_obj.subject = self._safe_decode_header(msg.get('Subject', ''))
            email_obj.sender = self._safe_decode_header(msg.get('From', ''))
            email_obj.message_id = msg.get('Message-ID', '')
            
            # Parse date
            date_str = msg.get('Date', '')
            if date_str:
                try:
                    # Try to parse the date
                    date_tuple = parsedate_tz(date_str)
                    if date_tuple:
                        timestamp = mktime_tz(date_tuple)
                        email_obj.date = datetime.fromtimestamp(timestamp)
                    else:
                        email_obj.date = datetime.now()
                except:
                    email_obj.date = datetime.now()
            else:
                email_obj.date = datetime.now()
            
            # Parse body and attachments
            self._parse_email_content(msg, email_obj)
            
            return email_obj
            
        except Exception as e:
            logger.error(f"Error in _fetch_single_email_safe: {e}")
            return None
    
    def _parse_email_content(self, msg, email_obj: Email):
        """Parse email content and extract attachments"""
        try:
            attachments = []
            body_parts = []
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition', ''))
                    
                    # Check for attachment
                    if 'attachment' in content_disposition.lower():
                        filename = part.get_filename()
                        if filename:
                            filename = self._safe_decode_header(filename)
                            if filename:
                                attachments.append(filename)
                                saved_path = self._save_attachment(part, filename, email_obj.message_id)
                                if saved_path:
                                    email_obj.saved_files.append({
                                        "filename": filename,
                                        "path": saved_path,
                                    })
                    
                    # Get body text
                    elif content_type in ['text/plain', 'text/html']:
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                charset = part.get_content_charset() or 'utf-8'
                                try:
                                    body = payload.decode(charset, errors='ignore')
                                    body_parts.append(body)
                                except:
                                    body_parts.append(payload.decode('utf-8', errors='ignore'))
                        except:
                            pass
            else:
                # Simple email
                try:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        charset = msg.get_content_charset() or 'utf-8'
                        try:
                            body = payload.decode(charset, errors='ignore')
                            body_parts.append(body)
                        except:
                            body_parts.append(payload.decode('utf-8', errors='ignore'))
                except:
                    pass
            
            email_obj.body = '\n'.join(body_parts) if body_parts else ""
            email_obj.attachments = attachments
            
        except Exception as e:
            logger.error(f"Error parsing email content: {e}")
    
    def _save_attachment(self, part, filename: str, message_id: str):
        """Save attachment to disk"""
        try:
            from utils import is_supported_file
            from config import Config
            import hashlib
            import os
            
            # Check if supported
            if not is_supported_file(filename):
                return None
            
            # Get the attachment data
            payload = part.get_payload(decode=True)
            if not payload:
                return None
            
            # Generate a safe filename
            file_hash = hashlib.md5(payload).hexdigest()[:8]
            safe_filename = f"{file_hash}_{filename}"
            file_path = os.path.join(Config.CV_STORAGE_PATH, safe_filename)
            
            # Save the file
            with open(file_path, 'wb') as f:
                f.write(payload)
            
            logger.info(f"Saved attachment: {safe_filename}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving attachment {filename}: {e}")
            return None
    
    def _safe_decode_header(self, header_value) -> str:
        """Safely decode email header"""
        try:
            if not header_value:
                return ""
            
            decoded_parts = decode_header(header_value)
            result = []
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    try:
                        if encoding:
                            part = part.decode(encoding, errors='ignore')
                        else:
                            part = part.decode('utf-8', errors='ignore')
                    except:
                        part = part.decode('utf-8', errors='ignore')
                result.append(str(part))
            
            return ' '.join(result).strip()
        except:
            return str(header_value)