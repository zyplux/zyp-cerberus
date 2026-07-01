# Copilot code review instructions

Only post medium- and high-severity review comments. Do not post low-severity or nitpick comments.

This project targets Python 3.14 and uses modern syntax. Before flagging any syntax as invalid, verify it against Python 3.14 — recent additions such as PEP 758 unparenthesized `except A, B, C:` clauses and the `type` alias statement are valid here.
