# process_emails_clean.py
import sys
import logging
from main import ATSProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    print("="*60)
    print("AI-Powered ATS - Email Processing (Clean Version)")
    print("="*60)
    
    # Initialize the processor
    print("\n🔧 Initializing ATS...")
    parser = ATSProcessor()
    
    if not parser.email_client:
        print("❌ Email client not configured. Please check your .env file.")
        return
    
    print("\n📧 Reading the newest 720 messages only. Older mail is left alone.")
    stats = parser.process_recent_emails(720)
    
    print(f"\n✅ Email processing complete!")
    print(f"   - Emails processed: {stats['total_emails']}")
    print(f"   - Candidates processed: {stats['processed_candidates']}")
    print(f"   - Duplicates skipped: {stats['duplicates']}")
    print(f"   - Errors: {stats['errors']}")
    
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
            print(f"   {i}. {candidate['full_name']} - Score: {candidate['score']:.1f}%")
    
    print("\n" + "="*60)
    print("✅ Done! View the dashboard at: http://localhost:5000")
    print("   Run: python dashboard_server.py")
    print("="*60)

if __name__ == "__main__":
    main()