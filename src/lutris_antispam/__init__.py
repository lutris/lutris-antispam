"""lutris-antispam — submission scoring for the Lutris website.

Public API::

    from lutris_antispam import assess
    result = assess({"name": "Monkey Mart free", "user_email": "x@grr.la"})
    result.verdict  # Verdict.SPAM
    result.score    # 90
    result.as_dict()

The website receives a verdict, a 0-100 score and the names of the rules that
matched, and does not reach into the rules themselves.
"""

from lutris_antispam.engine import (
    MAX_CONFIDENCE,
    SPAM_THRESHOLD,
    UNCERTAIN_THRESHOLD,
    assess,
)
from lutris_antispam._util import is_shared_host
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
    "is_shared_host",
]

__version__ = "0.2.0"
