# test_email_download.py
import os
import sys
from email_client import EmailClient
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_email_download():
    print("="*60)
    print("Testing Email Download")
    print("="*60)
    
    # Create email client
    client = EmailClient()
    
    # Connect
    print("\n📧 Connecting to email server...")
    if not client.connect():
        print("❌ Failed to connect")
        return
    
    print("✅ Connected")
    
    # Fetch emails
    print("\n📨 Fetching unread emails...")
    emails = client.fetch_unread_emails(limit=5)
    
    print(f"\n✅ Found {len(emails)} job application emails")
    
    for i, email in enumerate(emails, 1):
        print(f"\n{i}. Subject: {email.subject}")
        print(f"   From: {email.sender}")
        print(f"   Attachments: {len(email.attachments)}")
        if email.attachments:
            for att in email.attachments[:3]:
                print(f"   - {att}")
        
        # Check if attachments were saved
        import glob
        import os
        saved_files = []
        for att in email.attachments:
            pattern = os.path.join(Config.CV_STORAGE_PATH, f"*{att}")
            files = glob.glob(pattern)
            if files:
                saved_files.extend(files)
        
        if saved_files:
            print(f"   ✅ Saved files: {len(saved_files)}")
            for f in saved_files:
                print(f"      - {os.path.basename(f)}")
        else:
            print("   ⚠️  No files saved")
    
    # Disconnect
    client.disconnect()
    print("\n✅ Test complete")

if __name__ == "__main__":
    test_email_download()