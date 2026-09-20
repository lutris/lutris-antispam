"""Rules on free-text content (description, website, submission reason).

These fields are empty in the admin submissions feed but populated on the live
``Game`` object the website passes at submission time, where the payload URL
usually lives.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from lutris_antispam._util import DOMAIN_RE, URL_RE
from lutris_antispam.models import RuleHit, Submission

_PROMO_PHRASES = re.compile(
    r"\b(best|cheap|buy now|click here|visit|discount|deal|offer|casino|betting|"
    r"escort|loan|seo|backlink|porn|viagra|crypto|forex)\b",
    re.IGNORECASE,
)


def check(sub: Submission) -> Iterator[RuleHit]:
    blob = " ".join(t for t in (sub.description, sub.reason) if t).strip()

    # A website on a submission is context, not evidence: measured over the real
    # submission corpus it fires on 43% of all submissions and 91% of those were
    # accepted by a moderator. Reported for the reviewer, barely scored.
    if sub.website.strip():
        yield RuleHit("content.website_present", 5, sub.website[:80])

    if blob:
        urls = len(URL_RE.findall(blob)) + len(DOMAIN_RE.findall(blob))
        if urls:
            # A bare link is weak evidence — legit games link their own site, so
            # this only supports a verdict rather than driving one.
            yield RuleHit("content.contains_url", 10, f"{urls} url(s)")
        promos = _PROMO_PHRASES.findall(blob)
        if promos:
            # Weak: "best"/"visit" are ordinary words in a game description.
            yield RuleHit(
                "content.promo_language",
                min(10, 5 * len(set(promos))),
                ",".join(sorted(set(p.lower() for p in promos))),
            )
