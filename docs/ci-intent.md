# PR Gate Perfect World

## Invariant Rules

### human approvals

- not required except for files marked with CODEOWNERS

### ci

- auto-run on every push to the PR branch
- is a mandatory check for merge into main

### copilot_code_review

- only run on "read" PRs
- auto-run on every push to the PR branch
- is a mandatory check for merge into main

### review comments

- must be resolved prior to merge into main

### auto-merge

Should trigger when since the latest push to the PR branch:
- ci passed
- copilot_code_review has completed
- no unresolved copilot_code_review comments remain

New pushes invalidate both ci and copilot_code_review.

### skill

- /resolve-pr-review-comments [skill](/home/srg/.claude/skills/resolve-pr-review-comments/SKILL.md) should run in a loop once triggered: should flip PR to draft, assess copilot comments, fix relevant ones, run `just pr` to push fixes changes, respond to all comments and resolve threads, flip pr to ready. Repeat this untill copilot has reviewed with zero comments.

## Observations

- using an action to add @Copilot to the reviewers doesn't start the copilot_code_review - it needs to be manually triggered in using
- copilot_code_review is requested and auto-starts when PR is marked as ready for review after a new push AND branch policy has automatic copilot_code_review setting

## Notes

Because copilot_code_review is a mandatory check and comments must be resolved - it blocks the merge like a ci - which is exactly what we need.
I am flexible in terms of how the above is implemented, as long as it fits the above criteria.
I think we need to flip PR back to "draft" once copilot_code_review is finished and comments are produced. Then, after a new push and conversion to "ready" copilot_code_review will re-trigger.
I think `just pr` should do the flip to draft -> push -> flip to ready.
copilot_code_review is currently enabled via [org wide branch policy](../.github/rulesets/default-branch-baseline.json)
