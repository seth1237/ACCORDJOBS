# test_email.py
import imaplib
from config import Config

def test_email_connection():
    print("Testing email connection...")
    print(f"Host: {Config.EMAIL_HOST}")
    print(f"Port: {Config.EMAIL_PORT}")
    print(f"User: {Config.EMAIL_USER}")
    
    try:
        # Try to connect
        mail = imaplib.IMAP4_SSL(Config.EMAIL_HOST, Config.EMAIL_PORT)
        mail.login(Config.EMAIL_USER, Config.EMAIL_PASSWORD)
        print("✅ Connection successful!")
        mail.select('INBOX')
        print("✅ INBOX selected")
        mail.close()
        mail.logout()
        return True
    except imaplib.IMAP4.error as e:
        print(f"❌ Authentication failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check your email password")
        print("2. Enable IMAP access in your email settings")
        print("3. For Gmail, use an App Password")
        print("4. For corporate email, check with IT about IMAP settings")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("\nPossible issues:")
        print("1. Wrong host or port")
        print("2. Firewall blocking connection")
        print("3. Email provider doesn't support IMAP")
        return False

if __name__ == "__main__":
    test_email_connection()