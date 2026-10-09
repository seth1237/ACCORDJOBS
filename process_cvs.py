# process_cvs.py
import os
import sys
from main import ATSProcessor

def main():
    print("="*60)
    print("AI-Powered ATS - CV Processing Only")
    print("="*60)
    
    # Initialize the processor
    print("\n🔧 Initializing ATS...")
    parser = ATSProcessor()
    
    # Process CV files from the CVs directory
    print("\n📄 Processing CV files from 'CVs/' directory...")
    file_stats = parser.process_cv_files()
    
    print(f"\n✅ Processing complete!")
    print(f"   - Files processed: {file_stats['processed']}")
    print(f"   - Duplicates skipped: {file_stats['duplicates']}")
    print(f"   - Errors: {file_stats['errors']}")
    
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
    else:
        print("\n⚠️  No candidates found in the database.")
    
    print("\n" + "="*60)
    print("✅ Done! View the dashboard at: http://localhost:5000")
    print("   Run: python dashboard_server.py")
    print("="*60)

if __name__ == "__main__":
    main()