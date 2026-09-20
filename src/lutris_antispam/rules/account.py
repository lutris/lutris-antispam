"""Rules on the submitting account.

Mirrors the signals the website's existing ``clear_spammers`` heuristic already
trusts (unconfirmed email + a profile website + an empty library), so this
package stays consistent with prior moderation practice.
"""

from __future__ import annotations

from collections.abc import Iterator

from lutris_antispam.models import RuleHit, Submission


def check(sub: Submission) -> Iterator[RuleHit]:
    # The exact combination clear_spammers deletes on: unconfirmed account that
    # nonetheless filled in a promo website.
    if not sub.email_confirmed and sub.profile_website.strip():
        yield RuleHit("account.unconfirmed_with_website", 40, sub.profile_website[:80])

    if sub.account_age_days is not None and sub.account_age_days < 1:
        yield RuleHit("account.brand_new", 10, f"{sub.account_age_days:.2f}d")

    if sub.library_game_count == 0:
        yield RuleHit("account.empty_library", 5)
