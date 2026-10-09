# fetch_emails_by_date.py
import os
import sys
import logging
from datetime import datetime
from main import ATSProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    print("="*70)
    print("AI-Powered ATS - Fetch Emails by Date Range")
    print("="*70)
    
    # Define date range
    start_date = "2026-06-10"
    end_date = "2026-07-06"
    
    print(f"\n📅 Date Range: {start_date} to {end_date}")
    print(f"   (All job applications in this period)")
    
    # Initialize the processor
    print("\n🔧 Initializing ATS...")
    parser = ATSProcessor()
    
    if not parser.email_client:
        print("❌ Email client not configured. Please check your .env file.")
        return
    
    # Connect to email
    print("\n📧 Connecting to email server...")
    if not parser.email_client.connect():
        print("❌ Failed to connect to email server")
        return
    
    print("✅ Connected to email server")
    
    # Fetch emails by date
    print(f"\n📨 Fetching job applications from {start_date} to {end_date}...")
    
    try:
        # Use the email client's date-based fetch
        emails = parser.email_client.fetch_emails_by_date(start_date, end_date)
        
        print(f"\n✅ Found {len(emails)} job application emails")
        
        # Process each email
        print("\n📄 Processing CV attachments...")
        
        stats = {
            'total_emails': len(emails),
            'processed': 0,
            'duplicates': 0,
            'errors': 0,
            'candidates': []
        }
        
        for email in emails:
            try:
                # Find saved attachments
                import glob
                attachment_paths = []
                for attachment_name in email.attachments:
                    pattern = os.path.join(Config.CV_STORAGE_PATH, f"*_{attachment_name}")
                    matching_files = glob.glob(pattern)
                    if matching_files:
                        attachment_paths.extend(matching_files)
                    else:
                        pattern = os.path.join(Config.CV_STORAGE_PATH, f"*{attachment_name}")
                        matching_files = glob.glob(pattern)
                        if matching_files:
                            attachment_paths.extend(matching_files)
                
                if not attachment_paths:
                    logger.warning(f"No saved attachments found for: {email.subject}")
                    continue
                
                # Process each attachment
                for file_path in attachment_paths:
                    from utils import file_hash
                    file_hash_val = file_hash(file_path)
                    
                    if parser.db.candidate_exists(file_hash_val):
                        logger.info(f"Duplicate CV: {os.path.basename(file_path)}")
                        stats['duplicates'] += 1
                        continue
                    
                    candidate_data = parser._process_attachment(file_path, email)
                    if candidate_data:
                        stats['processed'] += 1
                        stats['candidates'].append(candidate_data)
                    else:
                        stats['errors'] += 1
                        
            except Exception as e:
                logger.error(f"Error processing email: {e}")
                stats['errors'] += 1
        
        # Print summary
        print("\n" + "="*70)
        print("📊 Processing Summary")
        print("="*70)
        print(f"   Total emails: {stats['total_emails']}")
        print(f"   Candidates processed: {stats['processed']}")
        print(f"   Duplicates skipped: {stats['duplicates']}")
        print(f"   Errors: {stats['errors']}")
        
        # Generate dashboard
        print("\n📊 Generating dashboard...")
        dashboard = parser.generate_dashboard()
        
        # Show stats
        stats = dashboard['stats']
        print("\n📈 Dashboard Statistics:")
        print(f"   - Total candidates: {stats['total_candidates']}")
        print(f"   - New today: {stats['new_today']}")
        print(f"   - Interview recommendations: {stats['interview_recommended']}")
        print(f"   - Average experience: {stats['avg_experience']:.1f} years")
        
        # Show top candidates
        if dashboard['top_candidates']:
            print(f"\n🏆 Top {min(5, len(dashboard['top_candidates']))} Candidates:")
            for i, candidate in enumerate(dashboard['top_candidates'][:5], 1):
                print(f"   {i}. {candidate['full_name']} - Score: {candidate['score']:.1f}% - Status: {candidate['status']}")
        
        print("\n" + "="*70)
        print("✅ Done! View the dashboard at: http://localhost:5000")
        print("   Run: python dashboard_server.py")
        print("="*70)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Need to import Config for the script
    from config import Config
    main()