# Checks for the HR review model, stored marks, and sign-in.
import os
import re
import tempfile
from datetime import date

from applicant_analyzer import ApplicantFitModel
from auth import verify_password
from database import Database

HR_CV = """
Jane Achieng
jane.achieng@example.test
+254712345678
Nairobi, Kenya
Date of Birth: 15 March 1998

Professional Summary
Human resources officer with 2 years of experience in recruitment, onboarding, and employee relations.

Experience
HR Assistant
Accord Medical Supplies
January 2024 - Present
- Maintained employee records and HR documentation
- Coordinated recruitment and interview scheduling
- Managed leave and attendance
- Advised on employment policies and confidentiality

Administrative Assistant
Nairobi Hospital
June 2022 - December 2023
- Microsoft Excel and Word for office administration

Education
Bachelor of Business Administration (Human Resource Management)
University of Nairobi
2022

Skills
Microsoft Office, Excel, HR policies, employee relations, Employment Act, NSSF, conflict resolution, communication
"""

MEDICAL_CV = """
Peter Otieno
peter.otieno@example.test
+254700000001

Objective
Application for a biomedical engineering role.

Experience
Biomedical Engineering Intern
The Nairobi Hospital
January 2025 - June 2025
- Maintenance and troubleshooting of medical equipment
- Supported the clinical engineering team

Education
Diploma in Medical Engineering
Kenya Medical Training College
2024

Skills
Medical equipment, troubleshooting, customer support
"""

SALES_CV = """
Mary Wanjiku
mary.wanjiku@example.test

Experience
Technical Sales Executive
ABC Medical
January 2019 - December 2024
- Territory sales of medical devices
- Customer relationships

Education
Bachelor of Commerce
University of Nairobi
2018
"""

GRAD_ONLY = """
Amina Hassan
amina.hassan@example.test

Education
Bachelor of Commerce
University of Nairobi
2016

Experience
Office Assistant
County Office
January 2020 - December 2021
- Filing and reception
"""


def test_hr_candidate():
    result = ApplicantFitModel().analyze(
        HR_CV,
        email_subject="Application for HR Officer",
        email_sender="Jane Achieng <jane.achieng@example.test>",
    )
    assert result["applied_role_category"] == "Human Resources", result["applied_role_category"]
    assert result["full_name"] == "Jane Achieng"
    assert result["email"] == "jane.achieng@example.test"
    assert result["years_experience"] >= 3, result["years_experience"]
    assert result["hr_years"] >= 1, result["hr_years"]
    assert result["fitness_score"] >= 70, result["fitness_score"]
    assert result["general_rating"] > 0
    assert any("Applied for the HR role" in item for item in result["strengths"])
    today = date.today()
    born = date(1998, 3, 15)
    expected_age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    assert result["age"] == expected_age, result["age"]
    assert result["age_estimated"] is False
    titles = " ".join(role["position"] for role in result["previous_roles"])
    assert "HR Assistant" in titles, result["previous_roles"]


def test_other_roles_are_not_labelled_hr():
    model = ApplicantFitModel()
    medical = model.analyze(MEDICAL_CV, email_subject="Application for Biomedical Engineer")
    assert medical["applied_role_category"] == "Medical Engineer", medical
    assert medical["fitness_score"] < 55, medical["fitness_score"]
    assert any("not the HR vacancy" in gap for gap in medical["gaps"]), medical["gaps"]

    sales = model.analyze(SALES_CV, email_subject="Application for Technical Sales Engineer")
    assert sales["applied_role_category"] == "Technical Sales", sales["applied_role_category"]
    assert sales["hr_years"] == 0
    assert any("Relevant degree" in item for item in sales["strengths"])
    assert any("not the HR vacancy" in item for item in sales["gaps"])


def test_estimated_age_and_empty_cv():
    estimated = ApplicantFitModel().analyze(GRAD_ONLY, email_subject="Admin assistant application")
    assert estimated["age_estimated"] is True
    assert estimated["age"] == date.today().year - (2016 - 22)
    empty = ApplicantFitModel().analyze("")
    assert empty["applied_role_category"] == "Other"
    assert empty["fitness_score"] < 30
    assert empty["previous_roles"] == []


def test_sorting_and_marks_survive_rescore():
    path = os.path.join(tempfile.mkdtemp(), "review.db")
    database = Database(path)
    user = database.get_user("hr@accordmedical.co.ke")
    assert user and verify_password("hr123", user["password_hash"])
    assert not verify_password("nope", user["password_hash"])

    model = ApplicantFitModel()
    older = model.analyze(SALES_CV, email_subject="Application for Technical Sales Engineer")
    younger = model.analyze(HR_CV, email_subject="Application for HR Officer")
    older_id = database.save_candidate({
        "full_name": older["full_name"],
        "email": older["email"],
        "file_hash": "hash-older",
        "estimated_years_experience": older["years_experience"],
        "experience": older["experience"],
        "education": older["education"],
        "skills": older["skills"],
    })
    younger_id = database.save_candidate({
        "full_name": younger["full_name"],
        "email": younger["email"],
        "file_hash": "hash-younger",
        "estimated_years_experience": younger["years_experience"],
    })
    database.save_analysis(older_id, older)
    database.save_analysis(younger_id, younger)

    by_years = database.get_applicants(sort="years", order="desc")
    assert [row["id"] for row in by_years] == [older_id, younger_id], by_years
    by_age = database.get_applicants(sort="age", order="asc")
    assert by_age[0]["id"] == younger_id
    hr_only = database.get_applicants(category="Human Resources")
    assert [row["id"] for row in hr_only] == [younger_id]

    database.save_mark(younger_id, "shortlisted", 4, "Call this week", user["email"])
    database.save_analysis(younger_id, {**younger, "fitness_score": 12, "general_rating": 10})
    saved = database.get_applicant(younger_id)
    assert saved["hr_mark"] == "shortlisted"
    assert saved["hr_rating"] == 4
    assert saved["fitness_score"] == 12
    assert saved["mark_history"][0]["notes"] == "Call this week"
    assert saved["status"] == "shortlisted"

    try:
        database.save_mark(younger_id, "nope", 4, "", user["email"])
        raise AssertionError("invalid mark was accepted")
    except ValueError:
        pass
    try:
        database.save_mark(younger_id, "interview", 9, "", user["email"])
        raise AssertionError("invalid rating was accepted")
    except ValueError:
        pass


def test_only_the_cv_is_scored():
    from documents import select_cv

    chosen, others = select_cv([
        {"filename": "Jane_Achieng_CV.pdf", "text": ""},
        {"filename": "Cover_Letter.pdf", "text": ""},
        {"filename": "KCSE_certificate.pdf", "text": ""},
        {"filename": "passport_photo.jpg", "text": ""},
        {"filename": "National_ID.pdf", "text": ""},
    ])
    assert chosen["filename"] == "Jane_Achieng_CV.pdf"
    assert sorted(item["kind"] for item in others) == [
        "certificate", "cover_letter", "identity", "photo",
    ]

    letter, rest = select_cv([{
        "filename": "Application.pdf",
        "text": "Dear Sir, I am writing to apply for the position. Yours faithfully",
    }])
    assert letter is None
    assert rest[0]["kind"] == "cover_letter"

    scanned, rest = select_cv([
        {
            "filename": "scan001.pdf",
            "text": "CURRICULUM VITAE\nWork experience\nEducational background\nSkills\nReferees",
        },
        {
            "filename": "scan002.pdf",
            "text": "This is to certify that the student has successfully completed the course.",
        },
    ])
    assert scanned["filename"] == "scan001.pdf"
    assert rest[0]["kind"] == "certificate"

    photo, rest = select_cv([{
        "filename": "IMG_4401.jpg",
        "text": "CURRICULUM VITAE\nWork experience\nEducational background\nSkills",
        "lone_image": True,
    }])
    assert photo["filename"] == "IMG_4401.jpg"
    assert rest == []

    ignored, rest = select_cv([
        {"filename": "Jane_CV.pdf", "text": ""},
        {"filename": "IMG_4401.jpg", "text": "CURRICULUM VITAE work experience skills", "lone_image": False},
    ])
    assert ignored["filename"] == "Jane_CV.pdf"
    assert rest[0]["kind"] == "photo"


def test_login_gate(client=None):
    from dashboard_server import app
    client = app.test_client()
    blocked = client.get("/api/applicants")
    assert blocked.status_code == 401

    page = client.get("/login")
    html = page.get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    bad = client.post("/login", data={
        "email": "hr@accordmedical.co.ke",
        "password": "wrong-password",
        "csrf_token": token,
    })
    assert b"not recognised" in bad.data

    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True)).group(1)
    good = client.post("/login", data={
        "email": "hr@accordmedical.co.ke",
        "password": "hr123",
        "csrf_token": token,
    }, follow_redirects=False)
    assert good.status_code == 302

    home = client.get("/")
    assert home.status_code == 200
    assert b"Applicant review" in home.data
    token = re.search(r'name="csrf-token" content="([^"]+)"', home.get_data(as_text=True)).group(1)

    from dashboard_server import db
    model = ApplicantFitModel()
    analysis = model.analyze(HR_CV, email_subject="Application for HR Officer")
    candidate_id = db.save_candidate({
        "full_name": "Review Test",
        "email": "review.test@example.test",
        "file_hash": "hash-review-test",
        "experience": analysis["experience"],
        "education": analysis["education"],
        "skills": analysis["skills"],
    })
    try:
        db.save_analysis(candidate_id, analysis)
        marked = client.post(
            f"/api/applicants/{candidate_id}/mark",
            json={"mark": "interview", "rating": 5, "notes": "Panel on Tuesday"},
            headers={"X-CSRF-Token": token},
        )
        assert marked.status_code == 200, marked.get_data(as_text=True)
        body = marked.get_json()
        assert body["hr_mark"] == "interview"
        assert body["hr_rating"] == 5
        listed = client.get("/api/applicants?sort=hr_rating&order=desc")
        assert listed.status_code == 200
        assert any(row["id"] == candidate_id for row in listed.get_json())
    finally:
        with db.get_connection() as conn:
            conn.execute("DELETE FROM candidates WHERE email LIKE '%@example.test'")
            conn.commit()


if __name__ == "__main__":
    test_hr_candidate()
    test_other_roles_are_not_labelled_hr()
    test_estimated_age_and_empty_cv()
    test_sorting_and_marks_survive_rescore()
    test_only_the_cv_is_scored()
    test_login_gate()
    print("review model tests passed")
