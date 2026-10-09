# database.py (UPDATED with Config import)
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

from auth import hash_password
from config import Config
from hr_profile import MARK_STATUS, REVIEW_MARKS, ROLE_CATEGORIES

logger = logging.getLogger(__name__)

SORTS = {
    "general_rating": "a.general_rating",
    "fitness": "a.fitness_score",
    "years": "COALESCE(a.years_experience, c.estimated_years_experience)",
    "hr_years": "a.hr_years",
    "age": "a.age",
    "hr_rating": "a.hr_rating",
    "name": "c.full_name",
    "newest": "c.created_at",
    "role": "a.applied_role_category",
}

ANALYSIS_FIELDS = (
    "applied_role",
    "applied_role_category",
    "role_confidence",
    "role_evidence",
    "age",
    "age_estimated",
    "age_source",
    "years_experience",
    "hr_years",
    "experience_summary",
    "previous_roles",
    "fitness_score",
    "general_rating",
    "fit_band",
    "strengths",
    "gaps",
    "fitness_summary",
    "criteria",
)

JSON_FIELDS = {"role_evidence", "previous_roles", "strengths", "gaps", "criteria"}


def _dict_items(items):
    for item in items or []:
        if isinstance(item, dict):
            yield item


def _loads(value, default):
    if not value:
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def init_database(self):
        """Create all necessary tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Candidates table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT,
                    email TEXT,
                    phone TEXT,
                    location TEXT,
                    linkedin TEXT,
                    github TEXT,
                    portfolio TEXT,
                    professional_summary TEXT,
                    estimated_years_experience REAL,
                    career_level TEXT,
                    recommended_department TEXT,
                    confidence REAL,
                    file_hash TEXT UNIQUE,
                    file_name TEXT,
                    file_path TEXT,
                    status TEXT DEFAULT 'pending',
                    score REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Skills table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    skill TEXT,
                    years REAL,
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
                    UNIQUE(candidate_id, skill)
                )
            ''')
            
            # Experience table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS experience (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    company TEXT,
                    position TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    duration TEXT,
                    description TEXT,
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                )
            ''')
            
            # Education table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS education (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    institution TEXT,
                    degree TEXT,
                    field TEXT,
                    year TEXT,
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                )
            ''')
            
            # Certifications table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS certifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    name TEXT,
                    issuer TEXT,
                    year TEXT,
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                )
            ''')
            
            # Projects table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    name TEXT,
                    description TEXT,
                    technologies TEXT,
                    url TEXT,
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                )
            ''')
            
            # Languages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS languages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    language TEXT,
                    proficiency TEXT,
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                )
            ''')
            
            # Awards table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS awards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    name TEXT,
                    issuer TEXT,
                    year TEXT,
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                )
            ''')
            
            # Emails table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    subject TEXT,
                    sender TEXT,
                    body TEXT,
                    date TIMESTAMP,
                    attachment_names TEXT,
                    message_id TEXT UNIQUE,
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                )
            ''')
            
            # Job descriptions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS job_descriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    description TEXT,
                    requirements TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # Matching results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS match_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    job_id INTEGER,
                    match_score REAL,
                    strengths TEXT,
                    weaknesses TEXT,
                    recommendation TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
                    FOREIGN KEY (job_id) REFERENCES job_descriptions(id) ON DELETE CASCADE,
                    UNIQUE(candidate_id, job_id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE,
                    password_hash TEXT,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS applicant_analysis (
                    candidate_id INTEGER PRIMARY KEY,
                    applied_role TEXT,
                    applied_role_category TEXT,
                    role_confidence REAL,
                    role_evidence TEXT,
                    age INTEGER,
                    age_estimated INTEGER DEFAULT 0,
                    age_source TEXT,
                    years_experience REAL,
                    hr_years REAL,
                    experience_summary TEXT,
                    previous_roles TEXT,
                    fitness_score REAL,
                    general_rating REAL,
                    fit_band TEXT,
                    strengths TEXT,
                    gaps TEXT,
                    fitness_summary TEXT,
                    criteria TEXT,
                    hr_rating REAL,
                    hr_mark TEXT DEFAULT 'unmarked',
                    hr_notes TEXT,
                    marked_by TEXT,
                    marked_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS applicant_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    message_id TEXT,
                    kind TEXT,
                    file_name TEXT,
                    file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE SET NULL
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS applicant_marks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    mark TEXT,
                    rating REAL,
                    notes TEXT,
                    marked_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                )
            ''')

            self._ensure_default_user(cursor)
            conn.commit()
            logger.info("Database initialized successfully")
    
    def save_candidate(self, data: Dict[str, Any]) -> int:
        """Save candidate data and all related information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert candidate
            cursor.execute('''
                INSERT INTO candidates (
                    full_name, email, phone, location, linkedin, github, portfolio,
                    professional_summary, estimated_years_experience, career_level,
                    recommended_department, confidence, file_hash, file_name, file_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('full_name'),
                data.get('email'),
                data.get('phone'),
                data.get('location'),
                data.get('linkedin'),
                data.get('github'),
                data.get('portfolio'),
                data.get('professional_summary'),
                data.get('estimated_years_experience'),
                data.get('career_level'),
                data.get('recommended_department'),
                data.get('confidence'),
                data.get('file_hash'),
                data.get('file_name'),
                data.get('file_path')
            ))
            
            candidate_id = cursor.lastrowid
            
            seen_skills = set()
            for skill in data.get('skills', []) or []:
                if isinstance(skill, str):
                    name, years = skill, 0
                elif isinstance(skill, dict):
                    name = skill.get('name') or skill.get('skill') or ''
                    years = skill.get('years') or 0
                else:
                    continue
                name = str(name).strip()
                if not name or name.lower() in seen_skills:
                    continue
                seen_skills.add(name.lower())
                try:
                    years_value = float(years)
                except (TypeError, ValueError):
                    years_value = 0
                cursor.execute('''
                    INSERT OR IGNORE INTO skills (candidate_id, skill, years)
                    VALUES (?, ?, ?)
                ''', (candidate_id, name, years_value))
            
            for exp in _dict_items(data.get('experience')):
                cursor.execute('''
                    INSERT INTO experience (candidate_id, company, position, start_date, end_date, duration, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    candidate_id,
                    exp.get('company'),
                    exp.get('position'),
                    exp.get('start_date'),
                    exp.get('end_date'),
                    exp.get('duration'),
                    exp.get('description')
                ))
            
            for edu in _dict_items(data.get('education')):
                cursor.execute('''
                    INSERT INTO education (candidate_id, institution, degree, field, year)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    candidate_id,
                    edu.get('institution'),
                    edu.get('degree'),
                    edu.get('field'),
                    edu.get('year')
                ))
            
            for cert in _dict_items(data.get('certifications')):
                cursor.execute('''
                    INSERT INTO certifications (candidate_id, name, issuer, year)
                    VALUES (?, ?, ?, ?)
                ''', (
                    candidate_id,
                    cert.get('name'),
                    cert.get('issuer'),
                    cert.get('year')
                ))
            
            for proj in _dict_items(data.get('projects')):
                cursor.execute('''
                    INSERT INTO projects (candidate_id, name, description, technologies, url)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    candidate_id,
                    proj.get('name'),
                    proj.get('description'),
                    proj.get('technologies'),
                    proj.get('url')
                ))
            
            for lang in _dict_items(data.get('languages')):
                cursor.execute('''
                    INSERT INTO languages (candidate_id, language, proficiency)
                    VALUES (?, ?, ?)
                ''', (
                    candidate_id,
                    lang.get('language'),
                    lang.get('proficiency')
                ))
            
            for award in _dict_items(data.get('awards')):
                cursor.execute('''
                    INSERT INTO awards (candidate_id, name, issuer, year)
                    VALUES (?, ?, ?, ?)
                ''', (
                    candidate_id,
                    award.get('name'),
                    award.get('issuer'),
                    award.get('year')
                ))
            
            conn.commit()
            return candidate_id
    
    def candidate_exists(self, file_hash: str) -> bool:
        """Check if a candidate with given file hash exists"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM candidates WHERE file_hash = ?', (file_hash,))
            return cursor.fetchone() is not None
    
    def get_candidate_by_id(self, candidate_id: int) -> Optional[Dict]:
        """Get complete candidate data by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get candidate
            cursor.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,))
            candidate = cursor.fetchone()
            if not candidate:
                return None
            
            result = dict(candidate)
            
            # Get skills
            cursor.execute('SELECT skill, years FROM skills WHERE candidate_id = ?', (candidate_id,))
            result['skills'] = [dict(row) for row in cursor.fetchall()]
            
            # Get experience
            cursor.execute('SELECT * FROM experience WHERE candidate_id = ?', (candidate_id,))
            result['experience'] = [dict(row) for row in cursor.fetchall()]
            
            # Get education
            cursor.execute('SELECT * FROM education WHERE candidate_id = ?', (candidate_id,))
            result['education'] = [dict(row) for row in cursor.fetchall()]
            
            return result
    
    def get_all_candidates(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get all candidates with pagination"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM candidates 
                ORDER BY score DESC, created_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_top_candidates(self, limit: int = 10) -> List[Dict]:
        """Get top scoring candidates"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM candidates 
                WHERE score > 0 
                ORDER BY score DESC 
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_candidate_status(self, candidate_id: int, status: str):
        """Update candidate status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE candidates 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (status, candidate_id))
            conn.commit()
    
    def update_candidate_score(self, candidate_id: int, score: float):
        """Update candidate match score"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE candidates 
                SET score = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (score, candidate_id))
            conn.commit()
    
    def save_job_description(self, title: str, description: str, requirements: str) -> int:
        """Save a job description"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO job_descriptions (title, description, requirements)
                VALUES (?, ?, ?)
            ''', (title, description, requirements))
            conn.commit()
            return cursor.lastrowid
    
    def save_match_result(self, candidate_id: int, job_id: int, match_data: Dict):
        """Save matching results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO match_results (
                    candidate_id, job_id, match_score, strengths, weaknesses, recommendation
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                candidate_id,
                job_id,
                match_data.get('match_score', 0),
                json.dumps(match_data.get('strengths', [])),
                json.dumps(match_data.get('weaknesses', [])),
                match_data.get('recommendation', '')
            ))
            conn.commit()
    
    def get_dashboard_stats(self) -> Dict:
        """Get dashboard statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Total candidates
            cursor.execute('SELECT COUNT(*) as count FROM candidates')
            stats['total_candidates'] = cursor.fetchone()['count']
            
            # New today
            cursor.execute('''
                SELECT COUNT(*) as count FROM candidates 
                WHERE DATE(created_at) = DATE('now')
            ''')
            stats['new_today'] = cursor.fetchone()['count']
            
            # By status
            cursor.execute('''
                SELECT status, COUNT(*) as count 
                FROM candidates 
                GROUP BY status
            ''')
            stats['by_status'] = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Average experience
            cursor.execute('SELECT AVG(estimated_years_experience) as avg_exp FROM candidates')
            stats['avg_experience'] = cursor.fetchone()['avg_exp'] or 0
            
            # Interview recommendations - FIX: Use Config properly
            min_score = Config.MIN_SCORE_FOR_INTERVIEW
            cursor.execute('''
                SELECT COUNT(*) as count FROM candidates 
                WHERE score >= ? AND status = 'pending'
            ''', (min_score,))
            stats['interview_recommended'] = cursor.fetchone()['count']
            
            return stats
    
    def search_candidates(self, query: str) -> List[Dict]:
        """Search candidates by skills, name, or experience"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            search_pattern = f'%{query}%'
            
            cursor.execute('''
                SELECT DISTINCT c.* FROM candidates c
                LEFT JOIN skills s ON c.id = s.candidate_id
                WHERE c.full_name LIKE ? 
                OR c.email LIKE ? 
                OR c.professional_summary LIKE ?
                OR s.skill LIKE ?
                ORDER BY c.score DESC
            ''', (search_pattern, search_pattern, search_pattern, search_pattern))
            
            return [dict(row) for row in cursor.fetchall()]

    def _ensure_default_user(self, cursor):
        email = (Config.DASHBOARD_EMAIL or "").strip().lower()
        password = Config.DASHBOARD_PASSWORD or ""
        if not email or not password:
            return
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return
        cursor.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
            (email, hash_password(password), Config.DASHBOARD_NAME or "HR"),
        )

    def get_user(self, email: str) -> Optional[Dict]:
        email = (email or "").strip().lower()
        if not email:
            return None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, email, password_hash, name FROM users WHERE email = ?",
                (email,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def save_analysis(self, candidate_id: int, data: Dict[str, Any]):
        """Store the review model output. A later rescore keeps the HR mark."""
        payload = {}
        for field in ANALYSIS_FIELDS:
            value = data.get(field)
            if field in JSON_FIELDS:
                value = json.dumps(value or [])
            elif field == "age_estimated":
                value = 1 if value else 0
            payload[field] = value

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT candidate_id FROM applicant_analysis WHERE candidate_id = ?",
                (candidate_id,),
            )
            values = [payload[field] for field in ANALYSIS_FIELDS]
            if cursor.fetchone():
                assignments = ", ".join(f"{field} = ?" for field in ANALYSIS_FIELDS)
                cursor.execute(
                    f"""UPDATE applicant_analysis
                        SET {assignments}, updated_at = CURRENT_TIMESTAMP
                        WHERE candidate_id = ?""",
                    values + [candidate_id],
                )
            else:
                columns = ["candidate_id", *ANALYSIS_FIELDS]
                placeholders = ", ".join("?" for _ in columns)
                cursor.execute(
                    f"INSERT INTO applicant_analysis ({', '.join(columns)}) VALUES ({placeholders})",
                    [candidate_id, *values],
                )
            conn.commit()

    def get_applicants(
        self,
        sort: str = "general_rating",
        order: str = "desc",
        category: str = "",
        query: str = "",
        limit: int = 200,
        offset: int = 0,
    ) -> List[Dict]:
        sort_expr = SORTS.get(sort, SORTS["general_rating"])
        direction = "ASC" if str(order).lower() == "asc" else "DESC"
        clauses = []
        params: List[Any] = []
        if category in ROLE_CATEGORIES:
            clauses.append("a.applied_role_category = ?")
            params.append(category)
        if query and query.strip():
            like = f"%{query.strip()[:100]}%"
            clauses.append("""(
                c.full_name LIKE ? OR c.email LIKE ? OR c.phone LIKE ?
                OR IFNULL(a.applied_role, '') LIKE ?
                OR IFNULL(a.applied_role_category, '') LIKE ?
                OR IFNULL(a.experience_summary, '') LIKE ?
                OR IFNULL(c.professional_summary, '') LIKE ?
            )""")
            params.extend([like] * 7)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        sql = f"""
            SELECT c.id, c.full_name, c.email, c.phone, c.location, c.status,
                   c.professional_summary, c.file_name, c.created_at,
                   a.applied_role, a.applied_role_category, a.role_confidence,
                   a.age, a.age_estimated, a.years_experience, a.hr_years,
                   a.fitness_score, a.general_rating, a.fit_band,
                   a.hr_rating, a.hr_mark, a.experience_summary
            FROM candidates c
            LEFT JOIN applicant_analysis a ON a.candidate_id = c.id
            {where}
            ORDER BY CASE WHEN {sort_expr} IS NULL THEN 1 ELSE 0 END,
                     {sort_expr} {direction}
            LIMIT ? OFFSET ?
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, [*params, limit, offset])
            return [_applicant_list_row(row) for row in cursor.fetchall()]

    def get_applicant(self, candidate_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
            candidate = cursor.fetchone()
            if not candidate:
                return None
            result = dict(candidate)
            cursor.execute(
                "SELECT * FROM applicant_analysis WHERE candidate_id = ?",
                (candidate_id,),
            )
            analysis = cursor.fetchone()
            if analysis:
                parsed = dict(analysis)
                for field in JSON_FIELDS:
                    parsed[field] = _loads(parsed.get(field), [])
                parsed["age_estimated"] = bool(parsed.get("age_estimated"))
                parsed["hr_mark"] = parsed.get("hr_mark") or "unmarked"
                result.update(parsed)
            else:
                result["hr_mark"] = "unmarked"
                result["strengths"] = []
                result["gaps"] = []
                result["criteria"] = []
                result["previous_roles"] = []
            cursor.execute(
                "SELECT skill, years FROM skills WHERE candidate_id = ?",
                (candidate_id,),
            )
            result["skills"] = [
                {"name": row["skill"], "years": row["years"]} for row in cursor.fetchall()
            ]
            cursor.execute("SELECT * FROM experience WHERE candidate_id = ?", (candidate_id,))
            result["experience"] = [dict(row) for row in cursor.fetchall()]
            cursor.execute("SELECT * FROM education WHERE candidate_id = ?", (candidate_id,))
            result["education"] = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                """SELECT mark, rating, notes, marked_by, created_at
                   FROM applicant_marks
                   WHERE candidate_id = ?
                   ORDER BY id DESC""",
                (candidate_id,),
            )
            result["mark_history"] = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                """SELECT id, kind, file_name, file_path
                   FROM applicant_documents
                   WHERE candidate_id = ?
                   ORDER BY id""",
                (candidate_id,),
            )
            result["documents"] = [_document_row(row) for row in cursor.fetchall()]
            return result

    def save_mark(self, candidate_id: int, mark: str, rating, notes: str, marked_by: str) -> Dict:
        if mark not in REVIEW_MARKS:
            raise ValueError("Unknown mark")
        if rating is None or rating == "":
            rating_value = None
        else:
            try:
                rating_value = float(rating)
            except (TypeError, ValueError):
                raise ValueError("Rating must be from 1 to 5")
            if rating_value < 1 or rating_value > 5:
                raise ValueError("Rating must be from 1 to 5")
        notes = (notes or "").strip()[:2000]
        marked_by = (marked_by or "").strip()[:120]
        status = MARK_STATUS.get(mark, "pending")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM candidates WHERE id = ?", (candidate_id,))
            if not cursor.fetchone():
                raise ValueError("Applicant not found")
            cursor.execute(
                """INSERT INTO applicant_marks (candidate_id, mark, rating, notes, marked_by)
                   VALUES (?, ?, ?, ?, ?)""",
                (candidate_id, mark, rating_value, notes, marked_by),
            )
            cursor.execute(
                """UPDATE applicant_analysis
                   SET hr_mark = ?, hr_rating = ?, hr_notes = ?, marked_by = ?,
                       marked_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                   WHERE candidate_id = ?""",
                (mark, rating_value, notes, marked_by, candidate_id),
            )
            if cursor.rowcount == 0:
                cursor.execute(
                    """INSERT INTO applicant_analysis
                       (candidate_id, hr_mark, hr_rating, hr_notes, marked_by, marked_at)
                       VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                    (candidate_id, mark, rating_value, notes, marked_by),
                )
            cursor.execute(
                """UPDATE candidates
                   SET status = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (status, candidate_id),
            )
            conn.commit()
        return self.get_applicant(candidate_id)

    def get_review_stats(self) -> Dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS n FROM candidates")
            total = cursor.fetchone()["n"]
            by_role = {category: 0 for category in ROLE_CATEGORIES}
            cursor.execute(
                """SELECT applied_role_category AS category, COUNT(*) AS n
                   FROM applicant_analysis
                   GROUP BY applied_role_category"""
            )
            for row in cursor.fetchall():
                key = row["category"] or "Other"
                by_role[key] = by_role.get(key, 0) + row["n"]
            cursor.execute(
                "SELECT COUNT(*) AS n FROM applicant_analysis WHERE fitness_score >= 70"
            )
            strong_fit = cursor.fetchone()["n"]
            cursor.execute(
                """SELECT COUNT(*) AS n FROM applicant_analysis
                   WHERE hr_mark IS NOT NULL AND hr_mark != 'unmarked'"""
            )
            marked = cursor.fetchone()["n"]
            cursor.execute("SELECT AVG(years_experience) AS n FROM applicant_analysis")
            avg_years = cursor.fetchone()["n"] or 0
            cursor.execute(
                "SELECT AVG(age) AS n FROM applicant_analysis WHERE age IS NOT NULL"
            )
            avg_age = cursor.fetchone()["n"]
            return {
                "total": total,
                "by_role": by_role,
                "strong_fit": strong_fit,
                "marked": marked,
                "avg_years": round(avg_years, 1),
                "avg_age": round(avg_age, 1) if avg_age is not None else None,
            }


    def save_documents(self, candidate_id: Optional[int], message_id: str, documents: List[Dict]):
        """Keep cover letters, certificates, and other files off the applicant score."""
        if not documents:
            return
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for item in documents:
                cursor.execute(
                    """INSERT INTO applicant_documents
                       (candidate_id, message_id, kind, file_name, file_path)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        candidate_id,
                        message_id or "",
                        item.get("kind") or "other",
                        item.get("filename") or item.get("file_name") or "",
                        item.get("path") or item.get("file_path") or "",
                    ),
                )
            conn.commit()

    def get_document(self, candidate_id: int, document_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, candidate_id, kind, file_name, file_path
                   FROM applicant_documents
                   WHERE id = ? AND candidate_id = ?""",
                (document_id, candidate_id),
            )
            row = cursor.fetchone()
            return _document_row(row) if row else None


def _document_row(row) -> Dict:
    from documents import KIND_LABELS
    item = dict(row)
    item["kind_label"] = KIND_LABELS.get(item.get("kind") or "", "Other document")
    return item


def _applicant_list_row(row) -> Dict:
    item = dict(row)
    item["age_estimated"] = bool(item.get("age_estimated"))
    item["hr_mark"] = item.get("hr_mark") or "unmarked"
    return item