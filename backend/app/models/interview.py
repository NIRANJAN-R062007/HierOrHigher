"""Module 5.3 contracts: categorized interview question generation."""

from typing import Literal

from pydantic import BaseModel, Field

QuestionCategory = Literal["Technical", "Behavioral", "Role-Fit"]


class InterviewQuestion(BaseModel):
    category: QuestionCategory
    question: str


class InterviewQuestions(BaseModel):
    """Gemini structured-output schema for the interview_generator module.

    The 8–10 length constraint lives in the schema itself, so an off-count
    response fails validation and triggers the wrapper's single retry.
    """

    questions: list[InterviewQuestion] = Field(min_length=8, max_length=10)


class InterviewSetRequest(BaseModel):
    resume_id: str
    jd_id: str


class InterviewSetListItem(BaseModel):
    """One entry in a resume's interview-set history — the cheap summary the
    history panel lists. The full question list is fetched on demand."""

    id: str
    jd_id: str
    created_at: str


class InterviewSetResponse(BaseModel):
    """POST /api/interview-sets response — the module 5.3 contract."""

    interview_set_id: str
    resume_id: str
    jd_id: str
    questions: list[InterviewQuestion]
    cached: bool = False
