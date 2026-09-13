# Live structured Overview tests

Test date: 12 September 2026. The user authorized the five providers and use of their named `.env` keys. Tests used isolated copies of public papers retained in the local library. The installed application, user library and saved settings were not modified.

The application now owns SVG geometry, fonts, wrapping and connectors. That boundary works, but these live tests do **not** establish reliable model authoring or repair. No Attention run produced an approved Overview. Gemini completed the PRO pipeline, but independent inspection found narrative gaps that its own reviewer missed.

## Models and scope

| Provider | Verified requested model ID | Vision |
| --- | --- | --- |
| Gemini API | `gemini-3.8-flash` | Enabled |
| OpenRouter | `openai/gpt-5.6-luna` | Enabled |
| DeepSeek API | `deepseek-flash` | Enabled |
| OpenRouter | `z-ai/glm-5.3-flash` | Enabled |
| Groq | `openai/gpt-oss-120b` | Disabled |

Provider catalogs verified the IDs. DeepSeek's current `deepseek-flash` ID serves V4.1 Flash, as documented in its [official announcement](https://www.deepseek.com/en/news/deepseek-v4-1-flash/). The user did not specify a DeepSeek variant. GPT-OSS was tested without images; it still had retained paper text and local geometry validation.

All five received Attention Is All You Need, version `1706.03762v7`, with fresh reading initially. Gemini additionally received PRO, version `2511.07694v1`, with fresh reading. No live survey run or full paper-by-provider matrix was performed. These are diagnostic runs, not repeated quality or latency benchmarks.

Language was semi-formal. Production reasoning options and generation flow were used. The test runner alone imposed a 30-request ceiling and a 20-minute checkpoint ceiling; production limits were not changed. Two unproductive cases were stopped earlier, with an in-flight request outstanding. Their usage is therefore a lower bound and those requests may still be billed. An initial local harness-language typo failed before any completion request and is excluded from the results.

## Results

Times include reading unless marked as using saved reading. Corrected runs reused only that same provider's freshly generated, bibliography-filtered reading notes. These times must not be compared as equivalent cold runs.

| Run | Seconds | Recorded requests | Outcome |
| --- | ---: | ---: | --- |
| Gemini / Attention / initial | 47.18 | 9 | Authoring schema rejected with HTTP 400. |
| Gemini / Attention / corrected, saved reading | 115.53 | 30 | Reached a 960 × 917 render with no native layout issues. Model review rejected missing attention mechanics and transitions. Later repairs exhausted the test request budget. |
| Luna / Attention / initial | 347.17 | 30 | Repeated plans exceeded the unstated text/relationship limits. Test budget exhausted. |
| Luna / Attention / corrected, saved reading | 539.36 | 12 completed, plus an interrupted request | Planning succeeded. Authored flow panels repeatedly included fields belonging to other panel types, including placeholder lanes and unrelated example fields. Stopped without an approved scene. |
| DeepSeek / Attention / initial | 230.42 | 30 | Invalid plans and malformed submissions exhausted the test budget. |
| DeepSeek / Attention / corrected, saved reading | 258.22 | 26 | Eventually reached rendering and review. The review request failed because JSON mode required the word JSON in the prompt. |
| DeepSeek / unchanged draft / isolated review retry | 30.88 | 1 | JSON requirement fixed. Review completed and rejected the draft's mechanics, omissions and misleading connections. This was not a resumed end-to-end run or an accepted output. |
| GLM / Attention / initial | 861.64 | 14 completed, plus an interrupted request | One reading response took 329.712 seconds. Repeated plans exceeded the visual-focus length limit. Stopped during planning. This process had loaded the original schema; the later plan-schema fix was not live-retested on GLM. |
| Groq / Attention / initial | 0.28 | 1 | HTTP 403 from the edge service, initially reported by the application as an authentication error. |
| Groq / Attention / User-Agent fix | 4.58 | 2 | Key and model worked. Second reading request hit HTTP 429 at the account's 8,000-token-per-minute limit. |
| Groq / Attention / requests paced 60 seconds apart | 120.26 | 3 | Third reading request hit HTTP 413: requested 8,660 tokens against an 8,000-token limit. Waiting cannot make this individual request fit. |
| Gemini / PRO / fresh reading | 77.63 | 15 | Completed reading, authoring, rendering and provider review. Render: 960 × 941, no native layout issues. Independent narrative review did not accept this as ready. |

## Independent artifact inspection

The Gemini Attention draft looks orderly but does not meet the requested teaching standard. Its first panel describes attention mostly in prose beside bars. The narrow multi-head input visibly splits `512` across lines. The explanation lacks clear bridges into the encoder and decoder. Its subtitle says “constant operations” without qualifying sequential depth. Native geometry acceptance alone missed the broken numeric label; provider review caught that defect and the missing explanatory connections.

Gemini's PRO output is a readable three-stage composition. It retains the repeated Canada and Indonesia generations and the probability cutoff. However, it never states the coastline question, so the country answers and “wrong/correct” labels lack context. “Base surprise -log(p*_K)” and the adjustment still arrive without the beginner explanation requested by the user. Its introduction assumes familiarity with predictive entropy and NLI. The provider approved this candidate, demonstrating that model self-review is not a sufficient acceptance gate for narrative quality.

The isolated DeepSeek review rejected the unchanged generated draft for failing to illustrate query/key comparison and value mixing, showing multiple heads as a sequential strip, omitting or failing to qualify decoder components, and presenting a rationale sequence as data flow. Its findings are retained as model review evidence, not treated as an independent proof that every requested correction is necessary at Overview scope.

## Bibliography and credential checks

Attention contained 124 retained passages. The AI evidence view retained 84 and excluded 40 reference-list passages. Every recorded outgoing completion context was checked for those excluded passage IDs; none appeared. The complete retained paper was preserved. PRO's retained document had 71 passages before and after this evidence filter; this particular document adds no further reference-removal evidence.

The final artifact audit inspected 2,140 files in the test directory and found no occurrences of the four API keys. Keys were read locally and sent only to their matching provider endpoints. No key values are included in the report, logs or browser index.

## Focused production fixes

- `papers/ai.py` now sends the existing LocalXiv User-Agent convention. A live Groq model-list comparison established that Python's default identifier received edge error 1010 while the application identifier succeeded. Live completion then confirmed working credentials.
- Gemini uses automatic tool selection with the full schema. A minimal live comparison established that forced selection rejected this bounded scene schema, while automatic selection accepted it and produced a structured submission. Application validation remains mandatory. This did not solve Gemini's subsequent content/repair failures.
- The plan tool schema now advertises the existing 1,200-character field limit and 1–12 relationship limit. The planning prompt states them too. Saved-reading reruns moved Luna and DeepSeek into authoring instead of spending the test budget on oversized plans.
- The review system instruction explicitly requests a JSON object. An isolated live DeepSeek review verified that this resolves the JSON-mode protocol rejection.

No account upgrade, provider substitution, installed-app update, global timeout or retry-policy change was made. Production review and shape/size validation were not relaxed to obtain a pass.

Final local regression command:

```sh
LOCALXIV_HTML_RENDERER="$PWD/papers/html-snapshot" \
  .scratch/overview-agent-env/bin/python -m unittest \
  tests.test_ai tests.test_agent_overviews tests.test_explanation \
  tests.test_overview_scene tests.test_reading_bibliography
```

53 tests ran: 52 passed; the optional Keychain smoke test was skipped. These tests cover the provider options and headers, scene contract, scripted repair, native rendering, persistence/exports and bibliography boundary. `git diff --check` passed.

## Evidence and next work

Local evidence is under `.scratch/structured-live-2026-09-12/`. `index.html` links to rendered drafts; `results.json` records run outcomes; `bibliography-audit.json` records outgoing-context checks; `credential-audit.json` records the secret scan. Per-run directories retain reading notes, calls, timings, submitted plans/scenes and reviewer results. `run.py` and the diagnostic scripts make the checks reproducible using locally supplied keys. Drafts are not approved user-library outputs.

The main remaining work is to make each panel's allowed content unambiguous to the model and make repairs less repetitive. The current broad optional-field schema allows a syntactically valid response that the panel-specific validator then rejects. The live runs also show that the planner and author can drift away from the accepted example's narrative even when geometry is application-owned. Readiness requires successful live generation and independent inspection across the architecture, methodology and survey cases after those issues are addressed.
