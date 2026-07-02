"""Rule modules. Each ``check(submission)`` yields ``RuleHit`` objects.

The engine imports ``ALL_CHECKS`` and runs every check over a submission,
accumulating the hits. Keeping each rule a small generator makes them easy to
unit-test and reorder without touching the engine.
"""

from lutris_antispam.rules import account, content, email, name, platform

# Order is cosmetic (it only affects the order hits are reported in).
ALL_CHECKS = (
    email.check,
    name.check,
    content.check,
    account.check,
    platform.check,
)
