# Stable review model for incoming applications.
# It does not call the language model. A parsed CV (or the raw text alone)
# is enough to decide which job they applied for, what they have done,
# and how they sit against the HR officer role.

import re
from datetime import datetime
from typing import Dict, List, Optional

from hr_profile import (
    COMMUNICATION_PHRASES,
    CONFIDENTIALITY_PHRASES,
    CONFLICT_PHRASES,
    HR_PRACTICE_PHRASES,
    HR_TOKEN,
    HRIS_PHRASES,
    INITIATIVE_PHRASES,
    LAW_PHRASES,
    OFFICE_PHRASES,
    RELATED_DEGREE_PHRASES,
    ROLE_KEYWORDS,
)

_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_MONTH = (
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?"
)
_YEAR = r"(?:19|20)\d{2}"
_PRESENT = r"present|current|now|to date"
_RANGE = re.compile(
    rf"(?P<start>(?:{_MONTH})\.?\s+)?(?P<sy>{_YEAR})\s*"
    rf"(?:-|–|—|\bto\b)\s*"
    rf"(?:(?P<end>(?:{_MONTH})\.?\s+)?(?P<ey>{_YEAR}|{_PRESENT}))",
    re.IGNORECASE,
)
_DEGREE = re.compile(
    r"\b(ph\.?d|doctorate|master(?:s)?|mba|bachelor(?:s)?|b\.?\s?sc|"
    r"bsc|b\.?\s?com|bcom|bba|ll\.?b|diploma|higher diploma|certificate)\b",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.IGNORECASE)
_PHONE = re.compile(r"(?:\+254|254|0)7\d{8}|\+\d{10,15}")
_AGE = re.compile(r"\bage\s*[:\-]?\s*(\d{2})\b", re.IGNORECASE)
_DOB_LABEL = re.compile(
    r"(?:date of birth|d\.?\s?o\.?\s?b\.?|birth date|born)\s*[:\-]?\s*([^\n]{4,40})",
    re.IGNORECASE,
)
_APPLYING = re.compile(
    r"(?:applying for|application for|position of|role of|vacancy of)\s+(.{5,80})",
    re.IGNORECASE,
)


def _phrase_found(text: str, phrase: str) -> bool:
    suffix = r"s?" if len(phrase) > 3 else ""
    pattern = rf"(?<!\w){re.escape(phrase)}{suffix}(?!\w)"
    return re.search(pattern, text, re.IGNORECASE) is not None


def _hits(text: str, phrases: List[str]) -> List[str]:
    return [phrase for phrase in phrases if _phrase_found(text, phrase)]


def _normalize(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_loose_date(value: str, as_end: bool = False):
    """Return (datetime, is_present) or (None, False)."""
    if not value:
        return None, False
    raw = value.strip().strip(".").lower()
    if re.fullmatch(rf"(?:{_PRESENT})", raw):
        now = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return now, True
    month = None
    for name, number in sorted(_MONTHS.items(), key=lambda item: len(item[0]), reverse=True):
        if raw.startswith(name):
            month = number
            raw = raw[len(name):].strip(" .")
            break
    year_match = re.search(r"(19|20)\d{2}", raw)
    if not year_match:
        return None, False
    year = int(year_match.group())
    if month is None:
        month = 12 if as_end else 1
        day = 28 if as_end else 1
    else:
        day = 1
    try:
        return datetime(year, month, day), False
    except ValueError:
        return None, False


def _years_between(start: datetime, end: datetime) -> float:
    if not start or not end or end < start:
        return 0.0
    return round((end - start).days / 365.25, 1)


def _duration_label(start: Optional[datetime], end: Optional[datetime], present: bool) -> str:
    if not start or not end:
        return ""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if months < 0:
        return ""
    years, months = divmod(months, 12)
    parts = []
    if years:
        parts.append(f"{years} yr" + ("s" if years != 1 else ""))
    if months:
        parts.append(f"{months} mo")
    label = " ".join(parts) or "Less than a month"
    if present:
        label += " · current"
    return label


def _iso(value: Optional[datetime], present: bool = False) -> str:
    if present:
        return "Present"
    if not value:
        return ""
    return value.strftime("%Y-%m")


def _split_role(prefix: str):
    prefix = re.sub(r"\s+", " ", prefix or "").strip(" |-–—•·,")
    if not prefix:
        return "", ""
    for separator in (" | ", " – ", " — ", " - ", " at "):
        if separator in prefix:
            left, right = prefix.split(separator, 1)
            return left.strip(" ,")[:80], right.strip(" ,")[:80]
    if "," in prefix:
        left, right = prefix.split(",", 1)
        return left.strip()[:80], right.strip()[:80]
    return prefix[:80], ""


def _looks_like_education(context: str) -> bool:
    lowered = context.lower()
    education_words = (
        "bachelor", "master", "diploma", "university", "college",
        "degree", "kcse", "kcsE", "certificate", "polytechnic",
    )
    job_words = (
        "assistant", "officer", "engineer", "manager", "executive",
        "intern", "coordinator", "representative", "consultant",
    )
    has_education = any(word in lowered for word in education_words)
    has_job = any(word in lowered for word in job_words)
    return has_education and not has_job


def _previous_lines(text: str, line_start: int) -> List[str]:
    lines = []
    cursor = line_start - 1
    while cursor > 0 and len(lines) < 2:
        earlier = text.rfind("\n", 0, cursor)
        line = text[earlier + 1:cursor].strip(" |-–—•·")
        cursor = earlier
        if line:
            lines.append(line)
    return lines


def _following_text(text: str, end: int) -> str:
    rest = text[end:].lstrip(" \t-–—:•")
    stop = len(rest)
    blank = rest.find("\n\n")
    if blank != -1:
        stop = min(stop, blank)
    nxt = _RANGE.search(rest)
    if nxt:
        stop = min(stop, nxt.start())
    return re.sub(r"\s+", " ", rest[:stop]).strip(" -–—")[:240]


def _extract_roles_from_text(text: str) -> List[dict]:
    roles = []
    seen = set()
    for match in _RANGE.finditer(text):
        start_raw = f"{match.group('start') or ''} {match.group('sy')}".strip()
        end_raw = match.group("ey") or ""
        end_month = match.group("end") or ""
        if end_month and not re.fullmatch(rf"(?:{_PRESENT})", end_raw, re.IGNORECASE):
            end_raw = f"{end_month} {end_raw}".strip()
        start, _ = _parse_loose_date(start_raw, as_end=False)
        present = bool(re.fullmatch(rf"(?:{_PRESENT})", match.group("ey") or "", re.IGNORECASE))
        end, end_present = _parse_loose_date(end_raw, as_end=True)
        present = present or end_present
        if not start or not end:
            continue
        line_start = text.rfind("\n", 0, match.start()) + 1
        prefix = text[line_start:match.start()].strip(" |-–—•·")
        position, company = _split_role(prefix)
        if len(prefix) < 3:
            earlier = [
                line for line in _previous_lines(text, line_start)
                if not _RANGE.search(line)
            ]
            if len(earlier) >= 2:
                position, company = earlier[1][:80], earlier[0][:80]
            elif earlier:
                position, company = _split_role(earlier[0])
        context = f"{position} {company} " + text[max(0, match.start() - 80):match.end() + 40]
        if _looks_like_education(context):
            continue
        if len(position) < 2 and len(company) < 2:
            continue
        key = (position.lower(), company.lower(), start.year, end.year)
        if key in seen:
            continue
        seen.add(key)
        description = _following_text(text, match.end())
        blob = f"{position} {company} {description}"
        roles.append({
            "position": position,
            "company": company,
            "start_date": _iso(start),
            "end_date": _iso(end, present),
            "duration": _duration_label(start, end, present),
            "description": description,
            "years": _years_between(start, end),
            "hr_relevant": _is_hr_related(blob),
            "_start": start,
            "_end": end,
        })
    roles.sort(key=lambda role: role["_start"], reverse=True)
    return roles[:12]


def _is_hr_related(blob: str) -> bool:
    if _phrase_found(blob, HR_TOKEN):
        return True
    phrases = HR_PRACTICE_PHRASES + ROLE_KEYWORDS["Human Resources"] + ROLE_KEYWORDS["Administration"]
    return bool(_hits(blob, phrases))


def _roles_from_extracted(items) -> List[dict]:
    roles = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        position = str(item.get("position") or item.get("title") or "").strip()
        company = str(item.get("company") or item.get("employer") or "").strip()
        if not position and not company:
            continue
        start, _ = _parse_loose_date(str(item.get("start_date") or ""), as_end=False)
        end_raw = str(item.get("end_date") or "")
        present = bool(re.fullmatch(rf"(?:{_PRESENT})", end_raw.strip(), re.IGNORECASE))
        end, end_present = _parse_loose_date(end_raw, as_end=True)
        present = present or end_present
        description = str(item.get("description") or "").strip()
        blob = f"{position} {company} {description}"
        roles.append({
            "position": position[:80],
            "company": company[:80],
            "start_date": _iso(start) if start else str(item.get("start_date") or ""),
            "end_date": "Present" if present else (_iso(end) if end else str(item.get("end_date") or "")),
            "duration": item.get("duration") or _duration_label(start, end, present),
            "description": description[:240],
            "years": _years_between(start, end) if start and end else 0,
            "hr_relevant": _is_hr_related(blob),
            "_start": start,
            "_end": end or (datetime.now() if present else None),
        })
    return roles


def _career_span(roles: List[dict]) -> float:
    starts = [role["_start"] for role in roles if role.get("_start")]
    ends = [role["_end"] for role in roles if role.get("_end")]
    if not starts or not ends:
        return 0.0
    return _years_between(min(starts), max(ends))


def _hr_years(roles: List[dict]) -> float:
    relevant = [
        role for role in roles
        if role.get("hr_relevant") and role.get("_start") and role.get("_end")
    ]
    if not relevant:
        return 0.0
    start = min(role["_start"] for role in relevant)
    end = max(role["_end"] for role in relevant)
    return _years_between(start, end)


def _stated_years(text: str):
    """Return (total_years or None, hr_years or None) from explicit sentences."""
    total = None
    hr_specific = None
    patterns = [
        r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s+of\s+experience(?:\s+in\s+([^.\n]{0,50}))?",
        r"experience\s*[:\-]\s*(\d+(?:\.\d+)?)\s*\+?\s*years?(?:\s+in\s+([^.\n]{0,50}))?",
        r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s+in\s+([^.\n]{0,50})",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            years = float(match.group(1))
            context = match.group(2) or ""
            if _is_hr_related(context):
                hr_specific = max(hr_specific or 0, years)
            elif total is None:
                total = years
    return total, hr_specific


def _extract_education(text: str) -> List[dict]:
    lines = [line.strip(" •-\t") for line in text.splitlines() if line.strip()]
    if text.count("\n") < 4:
        lines = [part.strip() for part in re.split(r"(?<=\.)\s+|\s{2,}", text) if part.strip()]
    found = []
    seen = set()
    for index, line in enumerate(lines):
        if not _DEGREE.search(line):
            continue
        window = " ".join(lines[index:index + 3])
        institution = ""
        inst = re.search(
            r"\b((?:University|College|Institute|Polytechnic)\s+of\s+[A-Z][A-Za-z]+)\b",
            window,
        )
        if inst:
            institution = inst.group(1).strip()
        elif index + 1 < len(lines) and re.search(r"\b(University|College|Institute|Polytechnic)\b", lines[index + 1]):
            institution = lines[index + 1][:80]
        year_match = re.search(r"\b((?:19|20)\d{2})\b", window)
        degree = re.sub(r"\s+", " ", line)[:140]
        key = degree.lower()
        if key in seen:
            continue
        seen.add(key)
        found.append({
            "institution": institution,
            "degree": degree,
            "field": "",
            "year": year_match.group(1) if year_match else "",
        })
    return found[:6]


def _education_from_extracted(items) -> List[dict]:
    rows = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        degree = str(item.get("degree") or item.get("qualification") or "").strip()
        institution = str(item.get("institution") or item.get("school") or "").strip()
        if not degree and not institution:
            continue
        rows.append({
            "institution": institution,
            "degree": degree,
            "field": str(item.get("field") or ""),
            "year": str(item.get("year") or ""),
        })
    return rows


def _score_education(education: List[dict]) -> dict:
    blob = " ".join(
        f"{item.get('degree', '')} {item.get('field', '')} {item.get('institution', '')}"
        for item in education
    )
    related = bool(_hits(blob, RELATED_DEGREE_PHRASES))
    has_bachelor = bool(re.search(r"\b(bachelor|bsc|b\.?\s?sc|bcom|bba|ba|degree)\b", blob, re.I))
    has_master = bool(re.search(r"\b(master|mba|phd|doctorate)\b", blob, re.I))
    has_diploma = bool(re.search(r"\bdiploma\b", blob, re.I))
    evidence = ""
    if education:
        first = education[0]
        evidence = ", ".join(part for part in (first.get("degree"), first.get("institution")) if part)
    if (related and (has_bachelor or has_master)) or (related and has_master):
        score = 1.0
    elif related and has_diploma:
        score = 0.75
    elif has_bachelor or has_master:
        score = 0.5
    elif has_diploma:
        score = 0.35
    else:
        score = 0.0
    if not evidence and related:
        evidence = "Related field mentioned"
    return {
        "key": "education",
        "label": "Relevant degree",
        "weight": 18,
        "score": score,
        "evidence": evidence or "No degree found",
    }


def _score_hr_experience(hr_years: float, roles: List[dict]) -> dict:
    admin_years = sum(role.get("years") or 0 for role in roles if role.get("hr_relevant"))
    years = hr_years or admin_years
    if years >= 1:
        score = 1.0 if years < 6 else 0.9
        evidence = f"{years:g} years in HR or administration"
    elif years >= 0.4:
        score = 0.6
        evidence = f"{years:g} years in HR or administration"
    elif any(not role.get("hr_relevant") for role in roles):
        score = 0.2
        evidence = "Work history is outside HR and administration"
    else:
        score = 0.0
        evidence = "No HR or administrative experience found"
    return {
        "key": "hr_experience",
        "label": "HR or admin experience",
        "weight": 22,
        "score": score,
        "evidence": evidence,
    }


def _keyword_criterion(key, label, weight, text, phrases, empty_evidence, hit_prefix) -> dict:
    found = _hits(text, phrases)
    if not phrases:
        ratio = 0
    else:
        # A few real mentions are enough. Don't demand every synonym.
        ratio = min(1.0, len(found) / 2)
    if key == "office_systems":
        office = _hits(text, OFFICE_PHRASES)
        systems = _hits(text, HRIS_PHRASES)
        if office and systems:
            ratio = 1.0
            found = office[:2] + systems[:1]
        elif office:
            ratio = 0.75
            found = office
        elif systems:
            ratio = 0.7
            found = systems
        else:
            ratio = 0.0
    evidence = f"{hit_prefix}: {', '.join(found[:4])}" if found else empty_evidence
    return {
        "key": key,
        "label": label,
        "weight": weight,
        "score": round(ratio, 2),
        "evidence": evidence,
    }


def _age_from_text(text: str, education: List[dict]):
    labelled = _AGE.search(text)
    if labelled:
        age = int(labelled.group(1))
        if 18 <= age <= 70:
            return age, False, "Stated on the CV"
    for match in _DOB_LABEL.finditer(text):
        age = _age_from_dob_fragment(match.group(1))
        if age is not None:
            return age, False, "Date of birth"
    grad_years = []
    for item in education:
        if re.search(r"bachelor|bsc|bcom|bba|diploma|master", item.get("degree", ""), re.I):
            if str(item.get("year", "")).isdigit():
                grad_years.append(int(item["year"]))
    if grad_years:
        # First degree, assumed around age 22. Marked as an estimate.
        estimated_birth_year = min(grad_years) - 22
        age = datetime.now().year - estimated_birth_year
        if 18 <= age <= 70:
            return age, True, f"Estimated from a {min(grad_years)} graduation"
    return None, False, ""


def _age_from_dob_fragment(fragment: str):
    fragment = fragment.strip()
    iso = re.search(r"\b((?:19|20)\d{2})-(\d{1,2})-(\d{1,2})\b", fragment)
    dmy = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-]((?:19|20)\d{2})\b", fragment)
    month_name = re.search(
        rf"\b(\d{{1,2}})\s+({_MONTH})\.?\s+((?:19|20)\d{{2}})\b",
        fragment,
        re.IGNORECASE,
    )
    try:
        if iso:
            year, month, day = int(iso.group(1)), int(iso.group(2)), int(iso.group(3))
        elif month_name:
            day = int(month_name.group(1))
            month = _MONTHS[month_name.group(2).lower()[:3]]
            year = int(month_name.group(3))
        elif dmy:
            day, month, year = int(dmy.group(1)), int(dmy.group(2)), int(dmy.group(3))
            if month > 12 and day <= 12:
                day, month = month, day
        else:
            return None
        born = datetime(year, month, day)
    except (ValueError, KeyError):
        return None
    today = datetime.now()
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    if 18 <= age <= 70:
        return age
    return None


def _detect_role(subject: str, body: str, cv_text: str) -> dict:
    subject_l = subject or ""
    body_l = body or ""
    head = cv_text[:1800]
    applying = " ".join(_APPLYING.findall(subject_l + "\n" + body_l + "\n" + head))
    scores = {category: 0 for category in ROLE_KEYWORDS}
    evidence = {category: [] for category in ROLE_KEYWORDS}

    def add(category, phrase, points):
        scores[category] += points
        if phrase not in evidence[category]:
            evidence[category].append(phrase)

    zones = ((subject_l, 8), (body_l[:2500], 2), (head, 1), (applying, 6))
    for category, phrases in ROLE_KEYWORDS.items():
        for phrase in phrases:
            for zone, points in zones:
                if zone and _phrase_found(zone, phrase):
                    add(category, phrase, points)
                    break
    for zone, points in zones:
        if zone and _phrase_found(zone, HR_TOKEN):
            add("Human Resources", "hr", points)
            break

    # An internship subject should stay an internship even if the field is HR.
    subject_is_internship = any(
        _phrase_found(subject_l, phrase) for phrase in ROLE_KEYWORDS["Internship"]
    )
    best = max(scores, key=lambda category: scores[category])
    best_score = scores[best]
    if best_score <= 0:
        category = "Other"
        confidence = 0.2
        matched = []
    else:
        category = "Internship" if subject_is_internship and scores["Internship"] > 0 else best
        runner_up = max(value for key, value in scores.items() if key != category)
        confidence = min(0.98, 0.5 + min(scores[category], 16) / 40 + max(0, scores[category] - runner_up) / 30)
        matched = evidence[category][:6]
    display = re.sub(r"\s+", " ", subject or "").strip()
    if not display or len(display) < 3:
        display = applying.strip() or category
    return {
        "applied_role": display[:140],
        "applied_role_category": category,
        "role_confidence": round(confidence, 2),
        "role_evidence": matched,
    }


def _public_role(role: dict) -> dict:
    public = dict(role)
    public.pop("_start", None)
    public.pop("_end", None)
    return public


def _fit_band(score: float) -> str:
    if score >= 80:
        return "Strong fit"
    if score >= 65:
        return "Good fit"
    if score >= 50:
        return "Possible fit"
    if score >= 35:
        return "Weak fit"
    return "Not a fit"


def _career_level(years: float) -> str:
    if years >= 7:
        return "Senior"
    if years >= 3:
        return "Mid-level"
    if years > 0:
        return "Early career"
    return ""


class ApplicantFitModel:
    """Score one application against the HR officer role."""

    def analyze(
        self,
        cv_text: str,
        email_subject: str = "",
        email_body: str = "",
        email_sender: str = "",
        extracted: Optional[dict] = None,
    ) -> dict:
        extracted = extracted if isinstance(extracted, dict) else {}
        text = _normalize(cv_text)
        role = _detect_role(email_subject or "", email_body or "", text)

        extracted_roles = _roles_from_extracted(extracted.get("experience"))
        parsed_roles = _extract_roles_from_text(text)
        roles = extracted_roles or parsed_roles
        if extracted_roles and _career_span(extracted_roles) == 0 and parsed_roles:
            roles = parsed_roles

        education = _education_from_extracted(extracted.get("education")) or _extract_education(text)
        stated_total, stated_hr = _stated_years(text)
        span = _career_span(roles)
        try:
            gemini_years = float(extracted.get("estimated_years_experience") or 0)
        except (TypeError, ValueError):
            gemini_years = 0.0
        year_options = [value for value in (span, stated_total, gemini_years) if value and value > 0]
        years = max(year_options) if year_options else 0.0
        if span > 0 and years > span + 5:
            years = span
        years = round(min(years, 45), 1)

        hr_years = _hr_years(roles)
        if stated_hr:
            hr_years = round(max(hr_years, stated_hr), 1)
        elif hr_years == 0 and role["applied_role_category"] == "Human Resources" and stated_total:
            hr_years = round(stated_total, 1)

        full_text = "\n".join([
            text,
            email_subject or "",
            " ".join(
                f"{item.get('degree', '')} {item.get('description', '')}"
                for item in education
            ),
            " ".join(f"{item.get('position', '')} {item.get('description', '')}" for item in roles),
        ])

        criteria = [
            _score_education(education),
            _score_hr_experience(hr_years, roles),
            _keyword_criterion(
                "hr_practices", "HR practices", 15, full_text, HR_PRACTICE_PHRASES,
                "No recruitment, records, leave, or employee-relations work found",
                "Mentioned",
            ),
            _keyword_criterion(
                "communication", "Communication and organisation", 8, full_text,
                COMMUNICATION_PHRASES,
                "Communication and organisation not described",
                "Mentioned",
            ),
            _keyword_criterion(
                "office_systems", "Office and HR systems", 10, full_text,
                OFFICE_PHRASES + HRIS_PHRASES,
                "Microsoft Office or an HR system not mentioned",
                "Tools",
            ),
            _keyword_criterion(
                "employment_law", "Employment law and compliance", 12, full_text,
                LAW_PHRASES,
                "Employment law, statutory bodies, or compliance not mentioned",
                "Mentioned",
            ),
            _keyword_criterion(
                "confidentiality", "Confidentiality", 5, full_text,
                CONFIDENTIALITY_PHRASES,
                "Confidential handling not mentioned",
                "Mentioned",
            ),
            _keyword_criterion(
                "conflict", "Problem solving and conflict", 5, full_text,
                CONFLICT_PHRASES,
                "Conflict resolution not mentioned",
                "Mentioned",
            ),
            _keyword_criterion(
                "initiative", "Initiative across departments", 5, full_text,
                INITIATIVE_PHRASES,
                "Independent work across departments not described",
                "Mentioned",
            ),
        ]
        for item in criteria:
            item["points"] = round(item["weight"] * item["score"], 1)
            item["met"] = item["score"] >= 0.75
        fitness = round(min(100.0, sum(item["points"] for item in criteria)), 1)

        name = str(extracted.get("full_name") or "").strip() or _guess_name(text, email_sender)
        email = str(extracted.get("email") or "").strip() or _first(_EMAIL.findall(text)) or _sender_email(email_sender)
        phone = str(extracted.get("phone") or "").strip() or _first(_PHONE.findall(text))
        location = str(extracted.get("location") or "").strip() or _guess_location(text)
        summary = str(extracted.get("professional_summary") or "").strip() or _guess_summary(text)
        skills = _merge_skills(extracted.get("skills"), full_text)
        age, age_estimated, age_source = _age_from_text(text, education)

        filled = sum(bool(value) for value in (name, email, phone, education, roles))
        completeness = filled / 5
        experience_component = min(years, 3) / 3 * 100 if years else 0
        general = round(min(100.0, 0.75 * fitness + 0.15 * experience_component + 0.10 * completeness * 100), 1)

        strengths, gaps = _strengths_and_gaps(criteria, role)
        band = _fit_band(fitness)
        experience_summary = _experience_summary(roles)
        public_roles = [_public_role(item) for item in roles]
        fitness_summary = (
            f"{band} for the HR officer role ({fitness:g}/100). "
            f"Applied for {role['applied_role_category']}. "
            f"{years:g} years in work, {hr_years:g} in HR or administration. "
            f"{strengths[0] if strengths else 'No strong HR signal.'} "
            f"{gaps[0] if gaps else ''}"
        ).strip()

        return {
            "full_name": name,
            "email": email,
            "phone": phone,
            "location": location,
            "professional_summary": summary[:600],
            "skills": skills,
            "education": education,
            "experience": public_roles,
            "certifications": extracted.get("certifications") if isinstance(extracted.get("certifications"), list) else [],
            "estimated_years_experience": years,
            "career_level": str(extracted.get("career_level") or "").strip() or _career_level(years),
            "applied_role": role["applied_role"],
            "applied_role_category": role["applied_role_category"],
            "role_confidence": role["role_confidence"],
            "role_evidence": role["role_evidence"],
            "age": age,
            "age_estimated": bool(age_estimated),
            "age_source": age_source,
            "years_experience": years,
            "hr_years": hr_years,
            "experience_summary": experience_summary,
            "previous_roles": public_roles,
            "fitness_score": fitness,
            "general_rating": general,
            "fit_band": band,
            "strengths": strengths,
            "gaps": gaps,
            "fitness_summary": fitness_summary,
            "criteria": criteria,
        }


def _strengths_and_gaps(criteria: List[dict], role: dict):
    strengths = []
    gaps = []
    if role["applied_role_category"] == "Human Resources":
        strengths.append("Applied for the HR role.")
    elif role["applied_role_category"] == "Internship":
        gaps.append("This is an internship application, not the 1–2 year HR role.")
    elif role["applied_role_category"] != "Other":
        gaps.append(
            f"Applied for {role['applied_role_category']}, not the HR vacancy."
        )
    else:
        gaps.append("Could not tell which job they applied for.")

    hard = {"education", "hr_experience", "hr_practices", "office_systems", "employment_law"}
    for item in sorted(criteria, key=lambda row: row["points"], reverse=True):
        if item["score"] >= 0.75 and len(strengths) < 4:
            strengths.append(f"{item['label']}: {item['evidence']}")
    for item in sorted(criteria, key=lambda row: row["score"]):
        if item["key"] in hard and item["score"] < 0.5 and len(gaps) < 4:
            gaps.append(f"{item['label']}: {item['evidence']}")
    return strengths[:4], gaps[:4]


def _experience_summary(roles: List[dict]) -> str:
    if not roles:
        return "No structured work history found in the CV."
    parts = []
    for role in roles[:5]:
        label = role.get("position") or "Role"
        if role.get("company"):
            label += f" at {role['company']}"
        if role.get("duration"):
            label += f" ({role['duration']})"
        parts.append(label)
    return "; ".join(parts)


def _merge_skills(extracted_skills, text: str) -> List[dict]:
    names = []
    for item in extracted_skills or []:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict):
            names.append(str(item.get("name") or item.get("skill") or ""))
    catalogue = (
        HR_PRACTICE_PHRASES + OFFICE_PHRASES + HRIS_PHRASES
        + LAW_PHRASES + ["communication", "employee relations"]
    )
    names.extend(_hits(text, catalogue))
    cleaned = []
    seen = set()
    for name in names:
        label = re.sub(r"\s+", " ", str(name)).strip()
        if not label or label.lower() in seen:
            continue
        seen.add(label.lower())
        cleaned.append({"name": label[:60], "years": 0})
    return cleaned[:30]


def _guess_name(text: str, sender: str) -> str:
    skipped = {"curriculum vitae", "cv", "resume", "personal profile", "biodata", "personal information"}
    for line in text.splitlines()[:12]:
        candidate = line.strip()
        if not candidate or "@" in candidate or any(char.isdigit() for char in candidate):
            continue
        if candidate.lower() in skipped:
            continue
        words = candidate.split()
        if 2 <= len(words) <= 4 and all(re.fullmatch(r"[A-Za-z][A-Za-z'\-]*\.?", word) for word in words):
            return candidate[:80]
    sender_name = re.sub(r"<[^>]+>", "", sender or "").replace('"', "").strip()
    if sender_name and "@" not in sender_name:
        return sender_name[:80]
    return ""


def _sender_email(sender: str) -> str:
    match = _EMAIL.search(sender or "")
    return match.group(0) if match else ""


def _guess_location(text: str) -> str:
    labelled = re.search(r"(?:location|address|city)\s*[:\-]\s*([^\n,]{3,40})", text, re.IGNORECASE)
    if labelled:
        return labelled.group(1).strip()
    for city in ("Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Thika"):
        if re.search(rf"\b{city}\b", text):
            return f"{city}, Kenya" if re.search(r"\bKenya\b", text, re.I) else city
    return ""


def _guess_summary(text: str) -> str:
    match = re.search(
        r"(?:professional summary|profile|objective)\s*[:\-]?\s*(.+)",
        text,
        re.IGNORECASE,
    )
    if not match:
        return ""
    snippet = match.group(1).strip()
    snippet = re.split(r"\n\s*\n", snippet)[0]
    return re.sub(r"\s+", " ", snippet)[:400]


def _first(values):
    return values[0] if values else ""
