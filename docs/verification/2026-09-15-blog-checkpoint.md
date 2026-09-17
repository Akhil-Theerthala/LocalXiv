# Blog checkpoint, September 15, 2026

The user asked to park the current version as a local Git checkpoint. This preserves the current Blog and Overview work, retained verification artifacts, README rewrite, and cleanup plans on `akhil/model-authored-svg-overviews`. It does not establish v0.0.11 release readiness. No push, release tag, installed-app update, or new live provider run accompanies this checkpoint.

## Verification recorded before parking

The following offline command passed all 48 tests:

```sh
.venv/bin/python -m unittest \
  tests.test_agent_overviews.ReviewProtocolTests \
  tests.test_agent_overviews.AgentTests \
  tests.test_explanation.BlogReviewContractTests
```

A broader test run was interrupted while waiting in a subprocess. There is no full-suite pass for this checkpoint. The review concerned Markdown and initial in-app content.

The staged whitespace check flagged CRLF lines in the retained matrix CSV, final blank lines in two pilot reports, and trailing whitespace in captured probe output. These evidence files are preserved as captured.

## Two remaining review cases

1. Distinct findings can overwrite each other. `_issue_id()` assigns the same ID to review findings with the same category, path, and passages. `_review_response()` then retains only the last finding under that ID. A reproduction supplied two different mechanism findings on the same article passage and retained one.
2. An omitted figure can bypass attribution validation. `_review_response()` checks anchors for accepted figures, but a target that remains in the plan after omission takes neither validation branch. A reproduction targeting omitted `fig1` with an HBM anchor belonging to surviving `fig2` passed validation. Downstream conversion into a prose issue does not satisfy the plan's requirement to reject incorrect attribution.

These cases are recorded for later work. No fixes were made while creating this checkpoint. The local `.venv` symlink and ignored scratch data are excluded from Git.

The workflow defect plan (plan removed; in git history) preserves the bounded repair scope. The public code cleanup plan (plan removed; in git history) covers later repository preparation.
