# ToolCallingAgent restoration

Overview and Blog now use smolagents ToolCallingAgent with native provider function calls. CodeAgent execution was removed. The tools retrieve retained passages and layout references, submit structured HTML/SVG candidates for local rendering, and request separate evidence/image review. Only an approved candidate can finish. Nested candidate fields are explicit in the tool schema.

## Live Gemini verification

Gemini 3.8 Flash, smolagents 1.24.0, short Blog, image review enabled. Each case used a scratch copy and reused saved reading notes; this did not retest initial reading or replace saved library outputs. All six completed and passed automated review in this run.

| Paper | Mode | Calls | Seconds |
|---|---|---:|---:|
| PRO | overview | 14 | 94.8 |
| PRO | blog | 9 | 43.3 |
| Attention Is All You Need | overview | 12 | 93.4 |
| Attention Is All You Need | blog | 14 | 93.8 |
| Black-box uncertainty evaluation | overview | 14 | 119.9 |
| Black-box uncertainty evaluation | blog | 7 | 63.9 |

At the end of that run, all result files identified ToolCallingAgent and prompt revision `smolagents-tool-html-v2`; all accepted figures have empty local geometry-issue lists. The log is `.scratch/tool-agent-live.log` and the six-case status snapshot is `.scratch/toolcalling-six-cases.json`. Later design iterations replace scratch result files. One successful run per case does not establish repeatability.

## Checks and limits

Full suite: 285 tests, OK, one skipped. Follow-up provider/agent checks: 20 tests, OK, one skipped, including native function-call serialization and secret redaction.

The workflow diagram at `docs/overview-workflow.html` passes diagram-design self_check and native rendering checks. Its source is static HTML/CSS with inline SVG, no external assets or JavaScript. It follows the previously approved LocalXiv colors and Arial typography instead of the skill's default skin.

Manual inspection of all three Overview images found dense text, visible passage IDs in PRO, and architecture/taxonomy-heavy explanations. The black-box diagram's row-aligned arrows can misleadingly associate individual method families with action/confidence levels. PRO's wording about probabilities being sufficient is stronger than its bounded results justify. Automated review did not catch these issues. Treat these as integration outputs, not approved final visual designs. Blog prose received automated source review; it has not received a full manual editorial audit.

The runtime switch is verified. Editorial simplification and stronger visual/factual review remain. No release build or installed-app update was performed. CodeAgent/Manim work is deferred.

## Subsequent teaching-design revisions

User feedback requires concrete operations, then combined/parallel blocks, then overall architecture. The previous restriction against architecture was removed. Prompt revision v3 supports connected panels, short introductions, and up to 260 visible words. Overview review no longer incorrectly requests a Blog body.

The first two layered Attention attempts reached their step limits without approval, in `.scratch/attention-layered-live.log` and `.scratch/attention-stacked-live.log`. The latter draft also misroutes Q, K, and V into separate heads; manual inspection caught this beyond the automated review. It must not be treated as a finished illustration. Authoring/review now explicitly check shared inputs for parallel blocks.

Retained Attention passages disagree: p00002 and p00061 say 41.8 EN-FR BLEU; p00063 says 41.0. The reviewer oscillated between values. Updated instructions require omission or qualification of conflicting numbers rather than unsupported corrections. These final prompt safeguards have not had another live Gemini run.

Final full regression run: 287 tests, OK, one skipped. Focused checks cover the corrected mode and figure constraints. Successful six-case integration testing predates these final teaching-design revisions; the latest layered mockup remains unapproved.
