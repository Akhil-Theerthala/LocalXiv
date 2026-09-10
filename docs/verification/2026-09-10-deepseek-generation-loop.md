# DeepSeek generation loop diagnosis

Read-only inspection of the installed library and current source. No provider requests or setting changes were made.

The cancelled Attention Is All You Need Overview job ran for 22.03 minutes. Its trace `papers/4245fa9d10d6cc02fc6ded171d62108112d2558e7761193fe74c2bdbb41be03f/reader/overview-figures/6bab9dc2b45e4b7da142f2dc5ffdae36/agent-trace.json` under the user's LocalXiv library contains:

- 253 completed authoring requests, six candidate submissions, five review tool attempts, and 121 final-answer tool calls.
- The final candidate passed geometry checks. All five review attempts returned HTTP 400; no evidence review completed.
- After review failed, final-answer attempts alternated with prose that could not be parsed as tool calls. The latest job state is cancelled by the user.
- Provider-reported input grew from 9,628 to 257,940 tokens per request. Summed trace usage is 54,305,727 input tokens and 187,557 completion tokens. These are repeated-context totals, not unique content or a dollar-cost estimate. Cache and reasoning breakdowns are discarded by the current provider adapter.
- The trace file is 119.12 MB because each event includes prior request history. Failed provider requests are absent from that event list.

The immediately preceding successful Gemini Overview trace has 14 completed author/review requests and the corresponding job lasted 3.35 minutes. This is an operational observation, not a controlled provider benchmark.

## Confirmed causes and unresolved question

`papers/agent_overviews.py` permits unlimited agent steps. Tool exceptions are converted by smolagents into retryable observations. A persistent provider request failure can therefore remain inside the agent loop indefinitely.

The custom native-history replay adds `step.error` only when the assistant did not emit tool calls. A failed final-answer approval check happens after the final-answer tool returns, so its rejection is omitted from the native conversation: the model receives its own final-answer tool output without the failed check. This explains the repeated claims that the final answer was recorded.

Every turn replays earlier candidates and observations. smolagents also includes the whole rejected candidate in validation errors. The layout reference contains attributes such as `font-family` that the renderer rejects, although authoring instructions state that LocalXiv restrictions take precedence.

Gemini Flash gets explicit low thinking effort. DeepSeek gets no explicit effort setting. The current official API reference documents enabled thinking and high effort by default. The first DeepSeek author response reported 64,356 completion tokens while its visible text only introduced a layout-reference call; the discarded reasoning-token breakdown prevents a precise attribution.

The HTTP 400 cause is unconfirmed: `papers/ai.py` discards the provider error body. Vision review was enabled. Current DeepSeek documentation now supports image input for the Flash API, so lack of vision support must not be assumed from older documentation. Retain a bounded, credential-redacted provider error message before diagnosing the rejected request.

## Recommended sequence

1. Make terminal provider failures terminate the job, retain the draft, and preserve final-answer rejection feedback. Do not reinstate arbitrary whole-job request caps in place of correct failure handling.
2. Let application code control render, review, repair and completion. Bind each review to an immutable candidate revision, distinguish content issues from provider failures, and skip redundant final-answer negotiation after approval.
3. Keep original evidence, one current candidate and current repair issues in each stage's context. Preserve required native reasoning within a tool round; begin clean stage requests rather than truncating provider protocol state. Log per-call events once.
4. Use an evidence-linked explanation plan before geometry: main contribution, mechanism relationships, supported finding and scope. Render reusable visual structures locally, with contribution-specific composition. Start with one layout family and compare quality before replacing freeform authoring.
5. Make guidance match the supported renderer subset, return concise located errors, and test low-effort DeepSeek for authoring/layout work. Measure scientific acceptance and readability alongside calls, elapsed time, cache usage and reasoning tokens.

Official documentation checked: https://api-docs.deepseek.com/api/create-chat-completion/ and https://api-docs.deepseek.com/ . The source and installed generation workflow have not been changed by this diagnosis.
