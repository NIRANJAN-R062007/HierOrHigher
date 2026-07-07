"""Rule-based ATS scoring — deterministic, no LLM involved (spec 5.1, 12).

The ATS score is intentionally NOT produced by Gemini: identical input must
always yield an identical score, at zero API cost. Each check carries a
weight; the score is the sum of the weights of passing checks (0–100).

Inputs: raw resume text, the count of structured fields the parser extracted,
and the detected file kind. Uses no Gemini key.
"""

import re

from app.models.resume import ATSCheck, ATSScore

SECTION_HEADERS = [
    "experience",
    "work experience",
    "employment",
    "education",
    "skills",
    "projects",
    "certifications",
    "summary",
    "objective",
]

ACTION_VERBS = {
    "built", "led", "designed", "launched", "improved", "reduced",
    "increased", "created", "developed", "implemented", "automated",
    "migrated", "optimized", "delivered", "shipped", "owned", "drove",
    "architected", "mentored", "analyzed", "streamlined", "engineered",
}

BULLET_PREFIXES = ("-", "•", "*", "–", "▪", "·")

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
_METRIC_RE = re.compile(r"\d")


def _bullet_lines(raw_text: str) -> list[str]:
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    bullets = [ln.lstrip("".join(BULLET_PREFIXES)).strip()
               for ln in lines if ln.startswith(BULLET_PREFIXES)]
    if bullets:
        return bullets
    # Fallback for resumes without bullet glyphs: treat action-verb lines as bullets.
    return [ln for ln in lines if ln.split()[0].lower() in ACTION_VERBS]


def score_resume(raw_text: str, parsed_field_count: int, file_kind: str) -> ATSScore:
    """Run every deterministic ATS check and return the weighted score."""
    text_lower = raw_text.lower()
    lines_lower = [ln.strip().lower() for ln in raw_text.splitlines() if ln.strip()]
    checks: list[tuple[ATSCheck, int]] = []

    # 1. File format compatibility (weight 5) — PDF/DOCX both parse in ATS systems.
    checks.append((
        ATSCheck(
            check="file_format",
            passed=file_kind in ("pdf", "docx"),
            detail=f"{file_kind.upper()} is an ATS-compatible format",
        ),
        5,
    ))

    # 2. Standard section headers present (weight 20).
    found_sections = sorted({
        header for header in SECTION_HEADERS
        if any(ln.startswith(header) or ln == header for ln in lines_lower)
    })
    checks.append((
        ATSCheck(
            check="section_headers",
            passed=len(found_sections) >= 3,
            detail=f"found {len(found_sections)} standard section header(s): "
                   + (", ".join(found_sections) or "none"),
        ),
        20,
    ))

    # 3. Contact information detectable (weight 15).
    has_email = bool(_EMAIL_RE.search(raw_text))
    has_phone = bool(_PHONE_RE.search(raw_text))
    contact_bits = [b for b, ok in (("email", has_email), ("phone", has_phone)) if ok]
    checks.append((
        ATSCheck(
            check="contact_info",
            passed=has_email and has_phone,
            detail=("found " + " and ".join(contact_bits)) if contact_bits
                   else "no email or phone number detected",
        ),
        15,
    ))

    # 4. Quantified achievements in bullets (weight 20).
    bullets = _bullet_lines(raw_text)
    with_metrics = [b for b in bullets if _METRIC_RE.search(b)]
    missing_metrics = len(bullets) - len(with_metrics)
    checks.append((
        ATSCheck(
            check="quantified_achievements",
            passed=bool(bullets) and len(with_metrics) / len(bullets) >= 0.4,
            detail=(f"missing metrics in {missing_metrics} of {len(bullets)} bullet points"
                    if bullets else "no bullet points detected"),
        ),
        20,
    ))

    # 5. Action-verb-led bullets (keyword strength, weight 15).
    verb_led = [b for b in bullets if b.split() and b.split()[0].lower() in ACTION_VERBS]
    checks.append((
        ATSCheck(
            check="action_verbs",
            passed=bool(bullets) and len(verb_led) / len(bullets) >= 0.5,
            detail=(f"{len(verb_led)} of {len(bullets)} bullets start with a strong action verb"
                    if bullets else "no bullet points detected"),
        ),
        15,
    ))

    # 6. Appropriate length (weight 10).
    word_count = len(raw_text.split())
    checks.append((
        ATSCheck(
            check="length",
            passed=250 <= word_count <= 1100,
            detail=f"{word_count} words (target 250–1100)",
        ),
        10,
    ))

    # 7. Parseable structure (weight 15) — did structured extraction succeed?
    checks.append((
        ATSCheck(
            check="parseable_structure",
            passed=parsed_field_count >= 4,
            detail=f"{parsed_field_count} of 7 structured field groups extracted",
        ),
        15,
    ))

    value = sum(weight for check, weight in checks if check.passed)
    return ATSScore(value=value, breakdown=[check for check, _ in checks])
