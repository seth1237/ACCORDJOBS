# The HR officer role this review model scores against, and the other
# application types that show up in the same mailbox.

ROLE_CATEGORIES = (
    "Human Resources",
    "Medical Engineer",
    "Technical Sales",
    "Administration",
    "Internship",
    "Other",
)

REVIEW_MARKS = (
    "unmarked",
    "shortlisted",
    "interview",
    "on_hold",
    "maybe",
    "rejected",
)

MARK_STATUS = {
    "unmarked": "pending",
    "shortlisted": "shortlisted",
    "interview": "interview",
    "on_hold": "on_hold",
    "maybe": "consider",
    "rejected": "rejected",
}

HR_JOB = {
    "title": "Human Resources Officer",
    "experience_target": "1–2 years in HR or a related administrative role",
    "education_target": (
        "Bachelor's degree in Human Resource Management, "
        "Business Administration, or a related field"
    ),
    "responsibilities": [
        "Manage and maintain accurate employee records and HR documentation.",
        "Coordinate recruitment, including job postings, interview scheduling, and candidate communication.",
        "Support employee onboarding.",
        "Manage leave, attendance, and other routine HR processes.",
        "Support employee relations and address workplace concerns.",
        "Ensure HR policies and procedures are communicated and followed.",
        "Assist with employment-law and statutory compliance.",
        "Coordinate with other departments on HR matters.",
        "Keep employee information and HR records confidential.",
        "Support management on employee issues and HR initiatives.",
        "Handle day-to-day HR administration.",
    ],
    "requirements": [
        "Bachelor's degree in Human Resource Management, Business Administration, or a related field.",
        "1–2 years of experience in HR or a related administrative role.",
        "Knowledge of HR practices, employee relations, and workplace policies.",
        "Communication, interpersonal, and organizational skills.",
        "Proficiency in Microsoft Office and HR management systems.",
        "Understanding of employment laws, statutory requirements, and workplace compliance.",
        "Ability to handle confidential employee information.",
        "Problem-solving and conflict-resolution skills.",
        "Works independently, takes initiative, and coordinates across departments.",
        "Builds relationships with employees and management.",
    ],
}

# Phrases that identify which vacancy an email or CV is aimed at.
# Matched with word boundaries. Longer, specific phrases only.
ROLE_KEYWORDS = {
    "Human Resources": [
        "human resources",
        "human resource",
        "hr officer",
        "hr assistant",
        "hr manager",
        "hr executive",
        "hr administrator",
        "hr coordinator",
        "hr intern",
        "personnel officer",
        "people operations",
        "talent acquisition",
        "hr role",
        "hr position",
        "hr department",
    ],
    "Medical Engineer": [
        "biomedical engineer",
        "biomedical engineering",
        "biomedical",
        "medical engineer",
        "medical engineering",
        "clinical engineer",
        "clinical engineering",
        "medical equipment",
    ],
    "Technical Sales": [
        "technical sales",
        "sales engineer",
        "medical sales",
        "sales executive",
        "sales representative",
        "business development",
        "territory sales",
        "sales position",
        "sales role",
    ],
    "Administration": [
        "office administrator",
        "administrative assistant",
        "admin assistant",
        "office assistant",
        "receptionist",
        "office administrator",
    ],
    "Internship": [
        "internship",
        "intern",
        "industrial attachment",
        "trainee",
    ],
}

# Bare "hr" is scored separately so it does not match inside ordinary words.
HR_TOKEN = "hr"

RELATED_DEGREE_PHRASES = [
    "human resource",
    "human resources",
    "hrm",
    "business administration",
    "business management",
    "bachelor of business",
    "bba",
    "bcom",
    "b.com",
    "b.comm",
    "commerce",
    "public administration",
    "personnel management",
    "industrial relations",
    "psychology",
    "bachelor of laws",
    "llb",
]

HR_PRACTICE_PHRASES = [
    "recruitment",
    "interview scheduling",
    "interview",
    "onboarding",
    "induction",
    "leave management",
    "annual leave",
    "attendance",
    "employee relations",
    "employee records",
    "personnel records",
    "hr policy",
    "hr policies",
    "workplace policy",
    "disciplinary",
    "grievance",
    "payroll",
    "job posting",
]

OFFICE_PHRASES = [
    "microsoft office",
    "ms office",
    "microsoft excel",
    "microsoft word",
    "microsoft powerpoint",
    "microsoft outlook",
    "excel",
    "powerpoint",
    "google workspace",
]

HRIS_PHRASES = [
    "hris",
    "human resource information",
    "sap hr",
    "bamboo",
    "zoho people",
    "workday",
    "sage hr",
]

LAW_PHRASES = [
    "employment act",
    "employment law",
    "labour law",
    "labor law",
    "statutory",
    "nssf",
    "nhif",
    "shif",
    "paye",
    "compliance",
    "data protection",
]

COMMUNICATION_PHRASES = [
    "communication",
    "interpersonal",
    "organizational",
    "organisation",
    "coordination",
    "stakeholder",
]

CONFIDENTIALITY_PHRASES = [
    "confidential",
    "confidentiality",
    "discretion",
]

CONFLICT_PHRASES = [
    "conflict",
    "grievance",
    "problem-solving",
    "problem solving",
    "dispute",
]

INITIATIVE_PHRASES = [
    "initiative",
    "independently",
    "cross-functional",
    "across departments",
    "other departments",
]
