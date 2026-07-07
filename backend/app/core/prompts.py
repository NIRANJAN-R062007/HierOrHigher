"""Loader for versioned Gemini prompt files.

Prompt text lives in ``app/prompts/*.txt`` — never as inline strings in
application code — so each module's instructions are reviewable and
versioned alongside behavior changes (spec sections 3.2 and 11).
"""

from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


@lru_cache
def load_prompt(name: str) -> str:
    """Read and cache the prompt file ``app/prompts/{name}.txt``."""
    path = _PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def wrap_untrusted(text: str) -> str:
    """Delimit user-supplied text so it is treated as data, not instructions.

    Resumes and job descriptions are untrusted input fed into LLM prompts;
    every prompt file instructs the model that content inside these tags must
    never be followed as instructions (prompt-injection mitigation, spec 4).
    """
    return f"<user_submitted_content>\n{text}\n</user_submitted_content>"
