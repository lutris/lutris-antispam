# lutris-antispam

Deterministic submission-scoring rules for the Lutris website, kept in their own
package so they can be tuned and tested on their own, without a Django or
database dependency.

The website depends on this package and receives a verdict, a 0-100 score and
the rules that matched. Keeping the rules readable is a deliberate trade: a
spammer can read them, but so can every moderator and contributor who has to
judge whether a verdict was fair. The rules are weighted against a measured
corpus rather than kept secret, and the destructive path needs signals that are
expensive for a spammer to avoid (a throwaway inbox, an account named after the
thing it advertises) rather than ones that are cheap to reword.

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

Scores alone do not authorise the destructive path. `SPAM` additionally requires
one of `engine.STRONG_SIGNALS` to have fired — the rules measured to be specific
to spam rather than merely typical of a first-time submitter. Without one, a
submission is capped at `UNCERTAIN` no matter how high it scores.

## Tuning against the submission corpus

The weights are calibrated against every submission in the production database,
using moderator acceptance as ground truth (rejection deletes the row, so a
stored submission is either accepted or still pending). Rerunning that
measurement is the only way to change a weight responsibly — the intuitive
signals are the misleading ones:

- A website on the submission fires on 43% of *all* submissions and 91% of those
  were accepted. It is context for the reviewer, not evidence (5 points).
- A brand-new account with an empty library describes every honest first-time
  submitter just as well as a spammer.
- Alias/forwarding addresses (SimpleLogin, Firefox Relay, DuckDuckGo) are not
  throwaway inboxes: 90% of SimpleLogin submissions were accepted. They are kept
  out of `data/disposable_domains.txt` and scored separately.
- A throwaway inbox on its own is a coin flip (59% accepted); one promoting a
  spammy *name* is not (12%).
- Identity coordination — the game name, the account username and the email
  localpart being the same promoted entity — is the signal that actually
  separates spam (90%+ specific).

At the current weights the ban path flags 84 of 11,146 submissions, 5 of which a
moderator had accepted.

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
- `rules/history.py` — the submission's website is a domain the website has
  already banned a submission over (`website_seen_in_spam`). The one signal
  based on a moderator's past decision rather than the shape of the text, so it
  is trusted enough to reach the ban path — but deliberately weighted just under
  the threshold, so it still needs corroboration. The website records those
  domains only from confirmed bans, never from this package's own verdicts, and
  never records shared hosts like itch.io.

## Development

```sh
uv run --with pytest python -m pytest
```

Rules are tuned against the live submission corpus — see "Tuning against the
submission corpus" above for how that measurement is run. Never commit real
submission data: it contains personal information. Keep fixtures synthetic, as
in `tests/test_engine.py`.
