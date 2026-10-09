# Recruitment Extractor (local)

Reads job-application emails from your IMAP mailbox, downloads CV
attachments (PDF/DOCX), extracts structured candidate data with Gemini 2.5,
and saves everything as JSON — all running locally on your machine.

## Setup

```bash
cd RecruitmentExtractor
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

You'll be prompted for, in order:

1. Email address
2. Email password / app password (hidden input)
3. IMAP server (e.g. `mail.yourdomain.com`)
4. IMAP port (defaults to 993)
5. Gemini API key (hidden input)
6. Mailbox folder to scan (defaults to `INBOX`)

Nothing is written to disk — credentials only live in memory for the
current run. If you'd rather not retype them every time, you can add a
`.env` file and load it with `python-dotenv` instead, but the script does
not require this.

## Output

```
CVs/                 # downloaded attachments
output/
  John_Doe.json       # one file per candidate
  Mary_W.json
  summary.json         # combined list of all candidates
```

Each candidate JSON looks like:

```json
{
  "source_email_from": "John Doe <john@example.com>",
  "source_email_subject": "Application for Backend Engineer",
  "source_email_date": "Mon, 1 Jun 2026 10:00:00 +0300",
  "source_file": "John_Doe.pdf",
  "full_name": "John Doe",
  "email": "john@example.com",
  "phone": "+254...",
  "location": "Nairobi, Kenya",
  "current_title": "Backend Engineer",
  "years_of_experience": "5",
  "education": [...],
  "work_experience": [...],
  "skills": [...],
  "certifications": [...],
  "languages": [...],
  "summary": "..."
}
```

## Notes

- Only PDF and DOCX/DOC attachments are picked up by default (see
  `ALLOWED_EXTENSIONS` in `downloader.py`).
- IMAP search defaults to `ALL` mail in the chosen folder. To only scan
  recent messages, change `search_criteria` in `downloader.fetch_email_ids`
  (e.g. `'SINCE "01-Jun-2026"'`).
- If your provider requires an app-specific password (Gmail, Outlook,
  some cPanel setups with 2FA), generate one and use it instead of your
  normal login password.
# ACCORDJOBS
