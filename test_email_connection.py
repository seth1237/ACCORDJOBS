# test_email_connection.py
import imaplib
import ssl
from config import Config

def test_email_connection():
    print("="*60)
    print("Testing Email Connection")
    print("="*60)
    
    print(f"\n📧 Email Configuration:")
    print(f"   Host: {Config.EMAIL_HOST}")
    print(f"   Port: {Config.EMAIL_PORT}")
    print(f"   User: {Config.EMAIL_USER}")
    print(f"   SSL: {Config.EMAIL_USE_SSL}")
    
    try:
        print("\n🔄 Attempting to connect...")
        
        if Config.EMAIL_USE_SSL:
            # Use SSL (port 993)
            mail = imaplib.IMAP4_SSL(Config.EMAIL_HOST, Config.EMAIL_PORT)
        else:
            # Use TLS (port 587) - connect then starttls
            mail = imaplib.IMAP4(Config.EMAIL_HOST, Config.EMAIL_PORT)
            mail.starttls()
        
        print("   ✅ Connected to server")
        
        # Login
        mail.login(Config.EMAIL_USER, Config.EMAIL_PASSWORD)
        print("   ✅ Login successful")
        
        # Select folder
        mail.select(Config.EMAIL_FOLDER)
        print(f"   ✅ Selected folder: {Config.EMAIL_FOLDER}")
        
        # Check for unread emails
        status, messages = mail.search(None, 'UNSEEN')
        if status == 'OK':
            unread = len(messages[0].split())
            print(f"   📨 Unread emails: {unread}")
        
        # Close connection
        mail.close()
        mail.logout()
        print("\n✅ Email connection test PASSED!")
        return True
        
    except imaplib.IMAP4.error as e:
        print(f"\n❌ IMAP Authentication failed: {e}")
        print("\nPossible fixes:")
        print("1. Check your email password")
        print("2. Make sure IMAP is enabled for this account")
        print("3. Try using a different port (143 for non-SSL, 993 for SSL)")
        return False
        
    except ConnectionRefusedError:
        print(f"\n❌ Connection refused to {Config.EMAIL_HOST}:{Config.EMAIL_PORT}")
        print("\nPossible fixes:")
        print("1. Check if the host is correct")
        print("2. Try port 143 (non-SSL) or 993 (SSL)")
        print("3. Check if IMAP is enabled on the server")
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_email_connection()