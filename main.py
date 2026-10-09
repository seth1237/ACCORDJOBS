# main.py
import os
import logging
import json
import re
import shutil
import sqlite3
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import sys

from config import Config
from database import Database
from email_client import EmailClient
from attachment_downloader import AttachmentDownloader
from parser import TextExtractor
from gemini import GeminiExtractor
from utils import file_hash, is_supported_file, ensure_directory, clean_text
from scoring import CandidateScorer
from job_matcher import JobMatcher
from applicant_analyzer import ApplicantFitModel
from documents import select_cv

# Setup logging
def setup_logging():
    ensure_directory(Config.LOG_PATH)
    log_file = os.path.join(Config.LOG_PATH, f"ats_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

class ATSProcessor:
    def __init__(self):
        self.db = Database(Config.DATABASE_PATH)
        self.email_client = EmailClient()
        self.downloader = AttachmentDownloader()
        self.text_extractor = TextExtractor()
        self.gemini = GeminiExtractor()
        self.scorer = CandidateScorer()
        self.matcher = JobMatcher()
        self.analyzer = ApplicantFitModel()
        
        # Ensure required directories exist
        ensure_directory(Config.CV_STORAGE_PATH)
        ensure_directory(Config.DOCUMENTS_PATH)
        ensure_directory(Config.OUTPUT_PATH)
        
        logger.info("ATS Processor initialized")
    
    def process_emails(self, limit: int = 50) -> Dict:
        """Process unread emails with attachments"""
        logger.info("Starting email processing...")
        
        stats = {
            'total_emails': 0,
            'total_attachments': 0,
            'processed_candidates': 0,
            'duplicates': 0,
            'errors': 0,
            'candidates': []
        }
        
        # Connect to email server
        if not self.email_client.connect():
            logger.error("Failed to connect to email server")
            return stats
        
        try:
            # Fetch unread emails
            emails = self.email_client.fetch_unread_emails(limit)
            stats['total_emails'] = len(emails)
            
            if not emails:
                logger.info("No unread emails found")
                return stats
            
            # Process emails in parallel
            with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
                future_to_email = {
                    executor.submit(self._process_single_email, email): email 
                    for email in emails
                }
                
                for future in as_completed(future_to_email):
                    email = future_to_email[future]
                    try:
                        result = future.result()
                        if result:
                            stats['processed_candidates'] += 1
                            stats['candidates'].append(result)
                    except Exception as e:
                        logger.error(f"Error processing email: {e}")
                        stats['errors'] += 1
            
        except Exception as e:
            logger.error(f"Error in email processing: {e}")
        finally:
            self.email_client.disconnect()
        
        logger.info(f"Processing complete. Processed: {stats['processed_candidates']}, "
                   f"Duplicates: {stats['duplicates']}, Errors: {stats['errors']}")
        
        return stats

    def process_recent_emails(self, count: int = None) -> Dict:
        """Import CVs from the newest messages only.

        Older messages are not opened. Read and unread flags are left as they are.
        """
        if count is None:
            count = Config.RECENT_EMAIL_LIMIT
        logger.info(f"Reading the newest {count} messages, read-only")
        stats = {
            'total_emails': 0,
            'total_attachments': 0,
            'processed_candidates': 0,
            'duplicates': 0,
            'errors': 0,
            'candidates': []
        }
        if not self.email_client.connect():
            logger.error("Failed to connect to email server")
            return stats
        try:
            emails = self.email_client.fetch_recent_emails(count)
            stats['total_emails'] = len(emails)
            for email in emails:
                try:
                    result = self._process_single_email(email)
                    if result:
                        stats['processed_candidates'] += 1
                        stats['candidates'].append(result)
                except Exception as exc:
                    logger.error(f"Error processing email: {exc}")
                    stats['errors'] += 1
        except Exception as exc:
            logger.error(f"Error in recent email processing: {exc}")
        finally:
            self.email_client.disconnect()
        logger.info(
            "Recent import finished. Candidates: %s, errors: %s",
            stats['processed_candidates'], stats['errors'],
        )
        return stats
    
    def _process_single_email(self, email) -> Optional[Dict]:
        """Process a single email - simplified version"""
        try:
            logger.info(f"Processing email: {email.subject} from {email.sender}")
            
            saved = list(getattr(email, "saved_files", None) or [])
            if not saved and email.attachments:
                import glob
                for attachment_name in email.attachments:
                    matches = glob.glob(os.path.join(Config.CV_STORAGE_PATH, f"*_{attachment_name}"))
                    if not matches:
                        matches = glob.glob(os.path.join(Config.CV_STORAGE_PATH, f"*{attachment_name}"))
                    for path in matches:
                        saved.append({"filename": attachment_name, "path": path})
            if not saved:
                logger.info(f"No attachments to review in: {email.subject}")
                return None

            prepared = []
            from documents import classify_filename, name_is_only_an_image
            lone_scan = len(saved) == 1 and name_is_only_an_image(
                (saved[0].get("filename") or os.path.basename(saved[0].get("path") or ""))
            )
            for item in saved:
                filename = item.get("filename") or os.path.basename(item.get("path") or "")
                text = ""
                sniff = (not classify_filename(filename)) or (lone_scan and name_is_only_an_image(filename))
                if sniff and item.get("path"):
                    text = (self.text_extractor.extract_text(item["path"]) or "")[:4000]
                prepared.append({
                    **item,
                    "filename": filename,
                    "text": text,
                    "lone_image": lone_scan and name_is_only_an_image(filename),
                })

            chosen, others = select_cv(prepared)
            others = [self._park_document(item) for item in others]
            candidate_data = None
            candidate_id = None
            if chosen and chosen.get("path"):
                file_hash_val = file_hash(chosen["path"])
                if self.db.candidate_exists(file_hash_val):
                    logger.info(f"Duplicate CV detected: {os.path.basename(chosen['path'])}")
                    candidate_id = self._candidate_id_for_path(chosen["path"])
                else:
                    candidate_data = self._process_attachment(chosen["path"], email)
                    if candidate_data:
                        candidate_id = self._candidate_id_for_path(chosen["path"])
            else:
                logger.info(f"No CV in '{email.subject}'. Other documents were kept and not scored.")

            if others:
                self.db.save_documents(candidate_id, getattr(email, "message_id", "") or "", others)
                logger.info(
                    "Kept %s non-CV document(s) from '%s'",
                    len(others), email.subject,
                )
            return candidate_data
            
        except Exception as e:
            logger.error(f"Error processing email {email.subject}: {e}")
            return None

    def _park_document(self, item: Dict) -> Dict:
        """Move a non-CV file out of the CV folder so it is not scored later."""
        src = item.get("path") or ""
        parked = {key: value for key, value in item.items() if key != "text"}
        if not src or not os.path.isfile(src):
            return parked
        ensure_directory(Config.DOCUMENTS_PATH)
        dest = os.path.join(Config.DOCUMENTS_PATH, os.path.basename(src))
        if os.path.abspath(src) != os.path.abspath(dest):
            if os.path.exists(dest):
                dest = os.path.join(
                    Config.DOCUMENTS_PATH,
                    f"{file_hash(src)[:8]}_{os.path.basename(src)}",
                )
            shutil.move(src, dest)
        parked["path"] = dest
        return parked

    def _candidate_id_for_path(self, path: str):
        digest = file_hash(path)
        if not digest:
            return None
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM candidates WHERE file_hash = ?",
                (digest,),
            ).fetchone()
            return row["id"] if row else None
    
    def _process_attachment(self, file_path: str, email) -> Optional[Dict]:
        """Process a single attachment"""
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None
            
            # Generate file hash
            file_hash_value = file_hash(file_path)
            
            # Check for duplicates
            if self.db.candidate_exists(file_hash_value):
                logger.info(f"Duplicate CV detected: {os.path.basename(file_path)}")
                return None
            
            text = self.text_extractor.extract_text(file_path)
            if not text:
                logger.error(f"Could not extract text from: {file_path}")
                return None
            return self._finalize_candidate(file_path, text, email, file_hash_value)
            
        except Exception as e:
            logger.error(f"Error processing attachment {file_path}: {e}")
            return None
    
    def process_cv_files(self, directory: str = None) -> Dict:
        """Process CV files from a directory"""
        if not directory:
            directory = Config.CV_STORAGE_PATH
        
        logger.info(f"Processing CV files from: {directory}")
        
        stats = {
            'total_files': 0,
            'processed': 0,
            'duplicates': 0,
            'errors': 0,
            'candidates': []
        }
        
        if not os.path.exists(directory):
            logger.error(f"Directory not found: {directory}")
            return stats
        
        files = [f for f in os.listdir(directory) 
                if os.path.isfile(os.path.join(directory, f)) 
                and is_supported_file(f)]
        
        stats['total_files'] = len(files)
        
        for filename in files:
            file_path = os.path.join(directory, filename)
            try:
                candidate_data = self._process_cv_file(file_path)
                if candidate_data:
                    stats['processed'] += 1
                    stats['candidates'].append(candidate_data)
                else:
                    stats['duplicates'] += 1
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")
                stats['errors'] += 1
        
        return stats
    
    def _process_cv_file(self, file_path: str) -> Optional[Dict]:
        """Process a single CV file"""
        try:
            # Generate file hash
            file_hash_value = file_hash(file_path)
            
            # Check for duplicates
            if self.db.candidate_exists(file_hash_value):
                logger.info(f"Duplicate CV detected: {os.path.basename(file_path)}")
                return None
            
            text = self.text_extractor.extract_text(file_path)
            if not text:
                logger.error(f"Could not extract text from: {file_path}")
                return None
            return self._finalize_candidate(file_path, text, None, file_hash_value)
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return None

    def _finalize_candidate(self, file_path: str, text: str, email, file_hash_value: str) -> Optional[Dict]:
        """Score a CV against the HR role and store the review row.

        Reading and scoring stay on this machine. The language API is skipped
        unless USE_AI_EXTRACTION is turned on, because those calls were the
        part that failed and dropped CVs.
        """
        extracted = {}
        if Config.USE_AI_EXTRACTION:
            extracted = self.gemini.extract_candidate_data(clean_text(text)) or {}
            if not isinstance(extracted, dict):
                extracted = {}
        subject = getattr(email, "subject", "") if email else ""
        body = getattr(email, "body", "") if email else ""
        sender = getattr(email, "sender", "") if email else ""
        analysis = self.analyzer.analyze(
            cv_text=text,
            email_subject=subject or "",
            email_body=body or "",
            email_sender=sender or "",
            extracted=extracted,
        )
        candidate_data = _candidate_payload(extracted, analysis, file_path, file_hash_value)
        try:
            candidate_id = self.db.save_candidate(candidate_data)
        except sqlite3.IntegrityError:
            logger.info(f"Duplicate CV detected: {os.path.basename(file_path)}")
            return None
        if not candidate_id:
            return None
        self.db.save_analysis(candidate_id, analysis)
        self.db.update_candidate_score(candidate_id, analysis.get("general_rating") or 0)
        logger.info(
            "Reviewed %s as %s (fitness %.0f, general %.0f)",
            candidate_data.get("full_name") or os.path.basename(file_path),
            analysis.get("applied_role_category"),
            analysis.get("fitness_score") or 0,
            analysis.get("general_rating") or 0,
        )
        return candidate_data
    
    def match_candidates_to_job(self, job_description_text: str, candidate_ids: List[int] = None) -> Dict:
        """Match candidates to a job description"""
        logger.info("Starting job matching...")
        
        # Parse job description
        job_requirements = self.matcher.parse_job_description(job_description_text)
        
        if not job_requirements:
            logger.error("Failed to parse job description")
            return {'error': 'Failed to parse job description'}
        
        # Save job description
        job_id = self.db.save_job_description(
            job_requirements.get('title', 'Unknown Position'),
            job_description_text,
            json.dumps(job_requirements)
        )
        
        # Get candidates
        if candidate_ids:
            candidates = []
            for cid in candidate_ids:
                candidate = self.db.get_candidate_by_id(cid)
                if candidate:
                    candidates.append(candidate)
        else:
            candidates = self.db.get_all_candidates(limit=1000)  # Get all
        
        if not candidates:
            return {'error': 'No candidates found'}
        
        # Match candidates
        results = self.matcher.match_all_candidates(candidates, job_requirements)
        
        # Save results and update scores
        for result in results:
            candidate_id = result.get('candidate_id')
            if candidate_id:
                self.db.update_candidate_score(candidate_id, result['score'])
                self.db.save_match_result(candidate_id, job_id, result)
        
        logger.info(f"Matched {len(results)} candidates for job: {job_requirements.get('title')}")
        
        return {
            'job_id': job_id,
            'job_title': job_requirements.get('title'),
            'total_candidates': len(results),
            'results': results
        }
    
    def generate_dashboard(self) -> Dict:
        """Generate dashboard statistics and data"""
        logger.info("Generating dashboard...")
        
        stats = self.db.get_dashboard_stats()
        top_candidates = self.db.get_top_candidates(10)
        recent_candidates = self.db.get_all_candidates(20)
        
        dashboard = {
            'generated_at': datetime.now().isoformat(),
            'stats': stats,
            'top_candidates': top_candidates,
            'recent_candidates': recent_candidates,
            'recommendations': []
        }
        
        # Generate recommendations
        for candidate in top_candidates:
            if candidate['score'] >= Config.MIN_SCORE_FOR_INTERVIEW:
                dashboard['recommendations'].append({
                    'candidate_id': candidate['id'],
                    'name': candidate['full_name'],
                    'score': candidate['score'],
                    'action': 'Interview'
                })
        
        # Save dashboard to file
        dashboard_path = os.path.join(Config.OUTPUT_PATH, f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(dashboard_path, 'w') as f:
            json.dump(dashboard, f, indent=2, default=str)
        
        logger.info(f"Dashboard saved to: {dashboard_path}")
        
        return dashboard

def main():
    """Main entry point"""
    parser = ATSProcessor()
    
    # Newest mail only. Older messages stay untouched and nothing is marked read.
    print(f"Reading the newest {Config.RECENT_EMAIL_LIMIT} messages (read-only)...")
    email_stats = parser.process_recent_emails(Config.RECENT_EMAIL_LIMIT)
    print(f"Processed {email_stats['processed_candidates']} candidates from the newest mail")
    
    # Process CV files in directory
    print("\nProcessing CV files...")
    file_stats = parser.process_cv_files()
    print(f"Processed {file_stats['processed']} CV files")
    
    # Generate dashboard
    print("\nGenerating dashboard...")
    dashboard = parser.generate_dashboard()
    print(f"Total candidates: {dashboard['stats']['total_candidates']}")
    print(f"New today: {dashboard['stats']['new_today']}")
    print(f"Interview recommendations: {dashboard['stats']['interview_recommended']}")
    
    print("\nReview them at http://localhost:5000")
    print("Sign in with the HR review account. That password is not the mailbox password.")


def _pick(analysis: Dict, extracted: Dict, key: str, fallback=None):
    value = analysis.get(key)
    if value not in (None, "", [], {}):
        return value
    if isinstance(extracted, dict) and extracted.get(key) not in (None, "", [], {}):
        return extracted.get(key)
    return fallback


def _candidate_payload(extracted: Dict, analysis: Dict, file_path: str, file_hash_value: str) -> Dict:
    name = _pick(analysis, extracted, "full_name")
    if not name:
        stem = os.path.splitext(os.path.basename(file_path))[0]
        stem = re.sub(r"^[0-9a-fA-F]{8}_", "", stem).strip() or "Unknown applicant"
        name = stem
    return {
        "full_name": name,
        "email": _pick(analysis, extracted, "email", ""),
        "phone": _pick(analysis, extracted, "phone", ""),
        "location": _pick(analysis, extracted, "location", ""),
        "linkedin": extracted.get("linkedin") or "",
        "github": extracted.get("github") or "",
        "portfolio": extracted.get("portfolio") or "",
        "professional_summary": _pick(analysis, extracted, "professional_summary", ""),
        "estimated_years_experience": analysis.get("years_experience") or 0,
        "career_level": _pick(analysis, extracted, "career_level", ""),
        "recommended_department": analysis.get("applied_role_category") or "",
        "confidence": analysis.get("role_confidence") or 0,
        "skills": _pick(analysis, extracted, "skills", []),
        "experience": _pick(analysis, extracted, "experience", []),
        "education": _pick(analysis, extracted, "education", []),
        "certifications": _pick(analysis, extracted, "certifications", []),
        "projects": extracted.get("projects") if isinstance(extracted.get("projects"), list) else [],
        "languages": extracted.get("languages") if isinstance(extracted.get("languages"), list) else [],
        "awards": extracted.get("awards") if isinstance(extracted.get("awards"), list) else [],
        "file_hash": file_hash_value,
        "file_name": os.path.basename(file_path),
        "file_path": file_path,
    }

if __name__ == "__main__":
    main()