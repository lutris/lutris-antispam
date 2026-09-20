"""lutris-antispam — closed-source submission scoring for the Lutris website.

Public API::

    from lutris_antispam import assess
    result = assess({"name": "Monkey Mart free", "user_email": "x@grr.la"})
    result.verdict  # Verdict.SPAM
    result.score    # 90
    result.as_dict()

The website depends on this package but never sees the rules; only the verdict,
a 0-100 score, and the list of matched rule names cross the boundary.
"""

from lutris_antispam.engine import (
    MAX_CONFIDENCE,
    SPAM_THRESHOLD,
    UNCERTAIN_THRESHOLD,
    assess,
)
from lutris_antispam.models import Assessment, RuleHit, Submission, Verdict

__all__ = [
    "assess",
    "Assessment",
    "Submission",
    "Verdict",
    "RuleHit",
    "MAX_CONFIDENCE",
    "SPAM_THRESHOLD",
    "UNCERTAIN_THRESHOLD",
]

__version__ = "0.2.0"
