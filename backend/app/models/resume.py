"""Module 5.1 contracts: parsed resume, dual scores, and the upload response.

``ResumeAnalysis`` doubles as the Gemini structured-output schema (JSON mode),
so the model's response parses directly into these types — no free-text
parsing anywhere (spec 3.2).
"""

from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""


class ExperienceItem(BaseModel):
    title: str = ""
    company: str = ""
    start_date: str = ""
    end_date: str = ""
    bullets: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    degree: str = ""
    institution: str = ""
    year: str = ""


class ProjectItem(BaseModel):
    name: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)


class ParsedResume(BaseModel):
    name: str = ""
    contact: ContactInfo = Field(default_factory=ContactInfo)
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)

    def structured_field_count(self) -> int:
        """How many top-level fields were actually extracted — used for the
        garbled-parse guard (spec 9: fewer than 2 means ask for re-upload)."""
        contact_present = any(
            v.strip() for v in self.contact.model_dump().values()
        )
        return sum(
            [
                bool(self.name.strip()),
                contact_present,
                bool(self.skills),
                bool(self.experience),
                bool(self.education),
                bool(self.certifications),
                bool(self.projects),
            ]
        )


class ATSCheck(BaseModel):
    check: str
    passed: bool
    detail: str = ""


class ATSScore(BaseModel):
    value: int = Field(ge=0, le=100)
    breakdown: list[ATSCheck]


class HumanScore(BaseModel):
    value: int = Field(ge=0, le=100)
    breakdown: list[str]


class ResumeAnalysis(BaseModel):
    """Gemini structured-output schema for the resume_parser module."""

    parsed: ParsedResume
    human_score: HumanScore


class ResumeResponse(BaseModel):
    """POST /api/resumes response — the module 5.1 contract."""

    resume_id: str
    parsed: ParsedResume
    ats_score: ATSScore
    human_score: HumanScore
    cached: bool = False
    file_url: str | None = None


class ResumeListItem(BaseModel):
    id: str
    content_hash: str
    ats_score: ATSScore
    human_score: HumanScore
    created_at: str
