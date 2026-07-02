# lutris-antispam

**Private / closed-source.** Deterministic submission-scoring rules for the
Lutris website. This package is kept out of the public `lutris/website` repo on
purpose: the rules must stay unreadable to the spammers who can read that repo.

The public website depends on this package but only ever sees a verdict, a
0-100 score, and the list of matched rule *names* — never the rule logic.

## Contract

```python
from lutris_antispam import assess

result = assess({
    "name": "Monkey Mart free",
    "description": "",
    "website": "",
    "reason": "",
    "user_email": "distant.pony@grr.la",
    "username": "someuser",
    "email_confirmed": False,
    "profile_website": "https://promo.example",
    "account_age_days": 0.2,
    "library_game_count": 0,
})

result.verdict        # Verdict.SPAM | Verdict.UNCERTAIN | Verdict.CLEAN
result.score          # int, 0-100
result.matched_rules  # ["email.disposable_domain", "name.spam_keyword", ...]
result.as_dict()      # JSON-serialisable
```

All input fields are optional; missing signals simply don't score.

## Verdict policy (consumed by the website)

| Verdict     | Website action                                              |
|-------------|-------------------------------------------------------------|
| `spam`      | Snapshot + hard-delete submission, ban user, record IP      |
| `uncertain` | Flag for a moderator; nothing destructive                   |
| `clean`     | Nothing                                                     |

Thresholds live in `engine.py`: `SPAM_THRESHOLD=70`, `UNCERTAIN_THRESHOLD=35`.
The taunt email is only sent when `score >= MAX_CONFIDENCE` (90).

The design is **precision-first on the destructive path**: no single soft
signal can trigger a ban. A domain-shaped name (real games exist: Agar.io) or a
dotted Gmail alias alone stays at/under the review line; the ban path needs a
strong combination (e.g. disposable domain + spam keyword).

## Rules

- `rules/email.py` — disposable-domain blocklist (`data/disposable_domains.txt`),
  random-domain entropy, Gmail dotted-alias / random localpart, localpart echoing
  the game name.
- `rules/name.py` — spam keywords, marketing suffixes (" Game/Free/Online/PC"),
  name-is-a-domain / URL.
- `rules/content.py` — website present on a fresh submission, URLs and promo
  language in description/reason.
- `rules/account.py` — unconfirmed account with a profile website (mirrors the
  website's existing `clear_spammers` signal), brand-new account, empty library.

## Development

```sh
uv run --with pytest python -m pytest
```

Rules are tuned against the live submission corpus; see the maintainer notes for
the sampling procedure (do not commit real submission data — it contains PII).
