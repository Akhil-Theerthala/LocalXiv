# Gemini CodeAgent live verification

Tested the production `generate_overview` entry point with Gemini `gemini-3.8-flash`, smolagents 1.24.0 CodeAgent, saved retained reading notes, vision review enabled, and short Blog length. Tests used scratch copies of three library papers. No saved library generation was replaced.

## Live results

| Paper | Mode | Result | Calls | Seconds |
|---|---|---|---:|---:|
| 2511.07694v1 | overview | failed | 1 | 3.3 |
| 2511.07694v1 | blog | failed | 1 | 7.4 |
| 1706.03762v7 | overview | failed | 1 | 6.2 |
| 1706.03762v7 | blog | failed | 1 | 4.2 |
| 2606.19868v1 | overview | failed | 1 | 5.3 |
| 2606.19868v1 | blog | failed | 2 | 49.1 |

All six failed with Gemini's `function_call_filter: MALFORMED_FUNCTION_CALL`. Five failed before authoring a candidate. The black-box evaluation Blog generated a candidate, encountered rejected HTML comments, then failed at the next model response. No newly approved image or Blog was produced, so visual quality cannot be assessed from this run. Older scratch artifacts are not evidence of current success.

Two ordinary Gemini smoke requests succeeded: plain text and Python constructing HTML with inline SVG. This rules out a total credential/connectivity failure, but does not establish the precise cause of the CodeAgent incompatibility. Disabling native function calling did not resolve it. Experiments with built-in structured CodeAgent outputs and a shorter system prompt also failed and were reverted.

The provider now reports this specific Gemini error rather than suggesting an output-token increase. Harmless HTML comments are removed before validation; declarations and active markup remain rejected.

## Local checks

Full regression suite: 285 tests, OK, one skipped. This run preceded the small comment-handling regression addition. A subsequent focused provider/agent suite passed, including that addition. These scripted tests do not establish live-model success.

Raw six-case outcomes: `.scratch/smolagents-live/summary.json`. Live log: `.scratch/gemini-six-cases.log`. Regression logs: `.scratch/gemini-full-tests.log` and `.scratch/gemini-focused-tests.log`.

## Remaining issue

The Gemini-to-CodeAgent integration requires further diagnosis before acceptance. No release or installed-app validation was performed.
