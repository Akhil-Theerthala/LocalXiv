# Fiziko attention illustration

Implemented and checked on 2026-09-09 in the source checkout. The installed app
was not rebuilt. No TeX distribution was added to the app.

The planner now offers a fixed `attention_weighted_sum` illustration when MetaPost
is available. It chooses this only for evidence about attention's weighted sum of
values. Bento selection and blog figure design have separate schema instructions.
The model cannot provide executable MetaPost or image paths.

The drawing uses Fiziko spheres for three value vectors and tubes with widths
proportional to illustrative weights 0.6, 0.3, 0.1. It explicitly marks these as
examples, not measured attention. Alt text explains the weighted sum and omitted
score calculation/softmax. Fiziko source and its GPL license are retained under
`papers/vendor/fiziko`; MetaPost remains an optional host dependency.

Rendering is local. The library, template and label revision determine the cached
asset. Landscape, portrait and standalone blog figures reuse it. SVG/PNG exports
include the illustration; Excalidraw embeds it as one image, with MetaPost source
retained separately. Internal shaded shapes are not individual Excalidraw objects.

## Live evidence

Two Gemini trials used the previously authorized public Attention Is All You Need
paper, its saved reading and generated bento images. Neither repeated paper reading.
Both selected the Fiziko template through the normal content planner.

- First trial: five calls, one schema retry, 30,328 provider-reported total tokens.
  Its mixed blog/bento instructions were separated after inspecting the trace.
- Final trial: four calls, no retries, 23,035 provider-reported total tokens.
  Both rendered orientations passed the model's visual review and local inspection.
- Combined development usage: nine calls, 53,363 provider-reported total tokens.

Artifacts and sanitized traces are in `.scratch/bento-fiziko-live`.
The final result is `bento.json`; standalone reuse is `blog-illustration.json`.
The full live blog-writing and narration-review pipeline was not rerun.

## Local checks

`python3 -m unittest tests.test_reading tests.test_bento`: 18 tests passed.
The new check renders all three formats, verifies embedded SVG/PNG/Excalidraw
assets, confirms cache reuse and rejects unknown templates/missing runtimes.
`node tests/test_app_ui.js`, Python compilation and `git diff --check` passed.

The fine shading is clearest in the larger blog illustration. The small bento
version retains explicit numeric weights and a text transcript. A passed visual
review does not establish that every generated claim is scientifically exact.
