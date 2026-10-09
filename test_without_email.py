# test_without_email.py
import os
from main import ATSProcessor

print("Testing ATS without email...")

# Create the processor
parser = ATSProcessor()

# Just generate dashboard (should work even without emails)
print("\nGenerating dashboard...")
dashboard = parser.generate_dashboard()

print(f"\n✅ Dashboard generated successfully!")
print(f"Total candidates: {dashboard['stats']['total_candidates']}")
print(f"New today: {dashboard['stats']['new_today']}")
print(f"Interview recommendations: {dashboard['stats']['interview_recommended']}")
print(f"Average experience: {dashboard['stats']['avg_experience']} years")

# Show top candidates if any
if dashboard['top_candidates']:
    print("\nTop Candidates:")
    for candidate in dashboard['top_candidates'][:3]:
        print(f"  - {candidate['full_name']}: {candidate['score']:.1f}%")
        