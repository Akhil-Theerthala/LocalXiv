# Staged generation verification

The application now controls planning, candidate validation, rendering, evidence review and
completion. Authoring ends at submission. Each repair starts with the current candidate and
corrections in a fresh context. Provider failures stop generation; repeated identical rejected
candidates stop before another render or review. Reviews identify the candidate they checked.

Plans attach passage IDs to each claim and visual relationship. Compact Overview limits and
renderer-compatible guidance remain in place. DeepSeek authoring requests low reasoning effort.
Diagnostics retain bounded provider errors, timing and reported cache/reasoning usage without
repeated request bodies. The parallel layout experiment stays outside the shipped application.

## Local verification

- 82 offline generation, provider, reading, export and app tests completed successfully; one
  optional Keychain test was skipped. This includes terminal HTTP 400 errors, independent repair
  contexts, automatic completion after review, cancellation and saved-generation compatibility.
- Three native WebKit tests passed using a freshly compiled HTMLSnapshot executable. They check
  total Overview height, scaled label readability, and two/three-branch prototype layouts.
- The Node UI suite, Python compilation, source-collector self-check and `git diff --check` passed.
- Earlier compact-preview checks at 320, 640, 1024 and 1440 pixels are recorded in
  `docs/superpowers/plans/2026-09-10-compact-overviews.md`.

The successful mock path uses three provider responses after shared reading: plan, candidate and
review. Evidence reads and distinct repairs can add requests. This is a control-flow regression
check, not a live-provider latency measurement. No paid provider calls, app installation or
publication were performed. New storytelling quality still needs evaluation on generated papers.
