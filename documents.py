# Decide which attachment is the CV. Other files stay with the applicant
# and are not scored as a second person.

import os
import re

CV_NAME = re.compile(
    r"(?<![a-z])(cv|c\.v|resume|résumé|curriculum|vitae|biodata)(?![a-z])",
    re.IGNORECASE,
)
COVER_NAME = re.compile(
    r"cover[\s_-]*letter|application[\s_-]*letter|motivational[\s_-]*letter|"
    r"letter[\s_-]*of[\s_-]*application|motivation[\s_-]*letter",
    re.IGNORECASE,
)
CERT_NAME = re.compile(
    r"certificate|transcript|kcse|kcpe|diploma|testimonial|recommendation|"
    r"good\s*conduct|academic",
    re.IGNORECASE,
)
IDENTITY_NAME = re.compile(
    r"national[\s_-]*id|identity|passport|kra[\s_-]*pin|\bpin[\s_-]*certificate|"
    r"nssf|nhif|shif|huduma",
    re.IGNORECASE,
)
PHOTO_NAME = re.compile(r"photo|picture|passport\s*photo|image\d*", re.IGNORECASE)

CV_TEXT = (
    "curriculum vitae", "work experience", "professional experience",
    "employment history", "educational background", "career objective",
    "professional summary", "referees", "skills",
)
COVER_TEXT = (
    "dear hiring", "dear sir", "dear madam", "i am writing to",
    "yours faithfully", "yours sincerely", "cover letter",
    "application letter", "i wish to apply",
)
CERT_TEXT = (
    "this is to certify", "certificate of", "is hereby awarded",
    "transcript", "has successfully completed",
)

KIND_LABELS = {
    "cv": "CV",
    "extra_cv": "Extra CV",
    "cover_letter": "Cover letter",
    "certificate": "Certificate",
    "identity": "Identity document",
    "photo": "Photo",
    "other": "Other document",
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}


def classify_filename(filename: str) -> str:
    """Return a kind from the file name, or an empty string when the name is unclear."""
    name = filename or ""
    if CV_NAME.search(name):
        return "cv"
    if COVER_NAME.search(name):
        return "cover_letter"
    if PHOTO_NAME.search(name):
        return "photo"
    if IDENTITY_NAME.search(name):
        return "identity"
    if CERT_NAME.search(name):
        return "certificate"
    extension = os.path.splitext(name)[1].lower()
    if extension in IMAGE_EXTENSIONS:
        return "photo"
    return ""


def classify_text(text: str) -> str:
    """Read the opening of a file when the name does not say what it is."""
    sample = (text or "")[:4000].lower()
    if not sample.strip():
        return "other"
    cv_hits = sum(1 for phrase in CV_TEXT if phrase in sample)
    cover_hits = sum(1 for phrase in COVER_TEXT if phrase in sample)
    cert_hits = sum(1 for phrase in CERT_TEXT if phrase in sample)
    if cert_hits >= 1 and cert_hits >= cv_hits and cover_hits == 0:
        return "certificate"
    if cover_hits >= 1 and cover_hits > cv_hits:
        return "cover_letter"
    if cv_hits >= 2:
        return "cv"
    return "other"


def name_is_only_an_image(filename: str) -> bool:
    """A scan such as IMG_1234.jpg, with no word that says photo or CV."""
    name = filename or ""
    if CV_NAME.search(name) or COVER_NAME.search(name) or IDENTITY_NAME.search(name):
        return False
    if CERT_NAME.search(name) or PHOTO_NAME.search(name):
        return False
    return os.path.splitext(name)[1].lower() in IMAGE_EXTENSIONS


def classify_attachment(filename: str, text: str = "", lone_image: bool = False) -> str:
    named = classify_filename(filename)
    if named == "photo" and lone_image and text:
        sniffed = classify_text(text)
        if sniffed == "cv":
            return "cv"
    if named:
        return named
    return classify_text(text)


def select_cv(files):
    """Pick one CV from an email. Every other file is returned as a side document.

    `files` items need filename, and text when the name is ambiguous.
    """
    labelled = []
    for item in files:
        kind = classify_attachment(
            item.get("filename") or "",
            item.get("text") or "",
            lone_image=bool(item.get("lone_image")),
        )
        labelled.append({**item, "kind": kind})
    cvs = [item for item in labelled if item["kind"] == "cv"]
    if not cvs:
        return None, labelled
    cvs.sort(key=lambda item: (0 if CV_NAME.search(item.get("filename") or "") else 1, -(len(item.get("text") or ""))))
    chosen = cvs[0]
    others = []
    for item in labelled:
        if item is chosen:
            continue
        if item["kind"] == "cv":
            item = {**item, "kind": "extra_cv"}
        others.append(item)
    return chosen, others
