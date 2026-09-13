# Workflow revision 2 geometry implementation

Date: 2026-09-12  
Compiler and schema revision: `overview-scene-v3`

## Outcome

The scene compiler now measures nested content before allocating space and uses the accepted measurements for drawing. Feasible flow bars and lane connectors fit without changing authored content. Infeasible rows return structured, path-specific width constraints. Complete-page height failures remain failures.

No live provider calls, dependency installation, publication, or release occurred. `papers/html_figures.py` and `papers/HTMLSnapshot.swift` needed no geometry changes.

## Implementation

- `papers/overview_scene.py` measures text at its rendered style, includes wrapping safety and padding in minimum widths, allocates each flow step and lane independently, reserves lane-label height, and draws from the measured layout. It checks every row before SVG serialization and reports all independently measurable width failures.
- `papers/agent_overviews.py` preserves `constraint`, `path`, `actual`, and `limit` through compilation and native checks. Mechanical no-progress counters now depend on a smaller measured violation, not changed captions or evidence.
- The saved-fixture corpus includes the original flow-bar and `Memory K,V` connector failures plus an infeasible multi-row width case. The fixtures contain provenance and failure text, not credentials or provider reasoning.

## Native results

All accepted scenes use a 960 px source width, remain within the 960 px page-height gate, and retain a minimum displayed label size of at least 14 px at 640 px reading width.

| Case | Previous height or failure | Revision 3 result | Authored content |
| --- | ---: | ---: | --- |
| Reference D | 959 px | 946 px, no native issues | Unchanged |
| Reference E | 930 px | 955 px, no native issues | Unchanged |
| Reference F | 774 px | 803 px, no native issues | Unchanged |
| Nested flow bars | `The`: 37.9 px required, 24.9 px supplied; `0.1`: 30.6 px required, 25.7 px supplied | 386 px, no native issues | `The`, `0.1`, and `512` retained; topology unchanged |
| Lane connector | `Memory`: 79.4 px required, 42 px supplied | 544 px, no native issues | `Memory K,V`, endpoints, and both directions retained |

Complete PNG and PDF inspection found no clipping, overlap, or misplaced arrows. The lane label clears the arrow route in both directions. Each case also completed the local Kindle export, and all five EPUBs passed EPUBCheck 5.3.0 with zero warnings and zero errors.

The infeasible fixture reports both independent rows before serialization:

```text
scene.rows[0]: min_width actual 939, limit 800
scene.rows[1]: min_width actual 972, limit 800
```

No text is shrunk, truncated, or removed.

## Full saved-candidate replay

The complete saved candidates were replayed unchanged with native text measurement. Correcting nested sizing did not make either candidate acceptable.

| Candidate | Source identity | Previous height | Revision 3 height | Remaining issue |
| --- | --- | ---: | ---: | --- |
| Gemini | `a0609a99f0b3e68ecc5e56b1c8a97aba096833fb23a5f6838a4e24798ea082c0` | 1,173 px | 1,165 px | `max_height`, limit 960; minimum displayed label 12.5 px |
| DeepSeek | `5762036b0ef909dab2ab6c0b2c842200650835fedf222830538dd5447208f057` | 1,087 px | 1,079 px | `max_height`, limit 960; minimum displayed label 13.5 px |

Both replays preserve the source scene and its `overview-scene-v2` candidate identity. Their eight-pixel height reductions are measured improvements, not acceptance. The candidates still require model-authored recomposition or shorter content.

## Agent-loop result

The feasible nested-flow candidate completed the real local agent loop with four scripted responses: selection, narrative planning, authoring, and approval. It requested no geometry repair and retained its citations and scene. The red-phase regression showed that the previous compiler stopped on the avoidable width failure, so this scripted path avoids one geometry-repair request. The lane fixture proves the same preflight class locally, but it was not used to infer another provider call. Scripted responses provide no evidence about provider latency or token savings.

## Verification

```sh
.scratch/overview-agent-env/bin/python -m unittest \
  tests.test_overview_scene.SceneTests \
  tests.test_agent_overviews.AgentTests
# Ran 51 tests: OK

LOCALXIV_HTML_RENDERER="$PWD/papers/html-snapshot" \
  .scratch/overview-agent-env/bin/python -m unittest \
  tests.test_overview_scene.NativeSceneTests \
  tests.test_figure_readability
# Ran 7 tests: OK

epubcheck --failonwarnings <each-of-five-generated-books>
# EPUBCheck 5.3.0: 0 errors, 0 warnings for every book

.scratch/overview-agent-env/bin/python -m compileall -q \
  papers/overview_scene.py papers/agent_overviews.py \
  tests/test_overview_scene.py tests/test_agent_overviews.py
# Passed

git diff --check
# Passed
```

The native renderer timed out in the restricted execution sandbox. The same tests passed in the normal macOS WebKit environment; the sandbox timeout is recorded as an environment boundary, not a layout defect.
