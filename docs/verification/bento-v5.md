# Shared paper reading and bento composition

Implemented in the workspace; the installed application has not been rebuilt.

## Reading and cost

Both outputs now use `papers/reading.py`. A successful reading is stored atomically
in the paper's `reader/paper-reading.json` before output generation. Blog and bento
reuse it, including after an output-stage failure. The cache identity includes the
document digest, provider endpoint, model, reading revision, context/output limits,
vision setting and selected image digests. Output length and prose style do not
invalidate reading. Reused reading costs are not added to the new output's usage.

Each reading batch receives up to 12,000 characters of earlier notes. A final
synthesis connects the sections. This is bounded continuity, not unlimited recall.
On an uncached paper the synthesis adds one model call. Generating both outputs
then avoids repeating the reading batches and synthesis. Reviews receive cited
original passages as well as notes; citation validation still does not prove
scientific entailment.

## Figure inspection

The new explicit setting requires an image-capable compatible provider. Existing
settings remain text-only. With it enabled, reading sends up to six local PNG/JPEG
images found inside linked figure elements, at most 2 MB each. Remote URLs and
paths escaping the reader directory are excluded. Selected passage IDs and omitted
figure IDs are recorded in reading provenance. The current selection follows paper
order, not a model-ranked selection. SVG-only figures and PDF page figures are not
visually inspected by this implementation.

The blog gets a final narration pass with its rendered diagrams attached. The
bento gets a final landscape/portrait visual approval check; rejection fails the
new generation while preserving cached reading and the previously saved output.
These checks require extra calls only when figure inspection is enabled.

The payload follows the compatible chat API's text and image_url content parts,
including Gemini's documented image input format:
https://ai.google.dev/gemini-api/docs/openai

## Composition

The content planner now specifies bands of unequal-width columns, with one or two
stacked cards per column. Indices must cover every card exactly once. Narrow
three-column bands allow only short text without visuals. Portrait reflows into
one column in the planned reading order. Role-based colors distinguish mechanism,
evidence, context and limitations. Numeric comparisons use labeled bars with a
zero baseline; values with units or other nonnumeric text retain labeled values.

The retained preview uses manually curated, source-checked Transformer content to
exercise this renderer. It is not evidence of live model prompt quality.

## Verification

- 10 bento tests and 4 reading tests passed across the focused runs.
- 12 library tests passed, including the local HTTP regression test.
- UI tests and Python/JavaScript syntax checks passed.
- Landscape and portrait previews rendered and inspected visually.
- Cache tests cover reuse across output styles, source/model/vision invalidation,
  corrupt cache recovery, and no reading calls when switching from bento to blog.
- Image tests inspect the actual multimodal request structure and local path rules.
- Composition tests check unequal spans, stacked cards, containment and non-overlap.
- A mocked visual review tests acceptance and rejection of rendered output.

The initial implementation was tested locally without provider calls. After explicit
user approval, live orchestration testing and further fixes were completed; see
[bento-orchestration-trace.md](bento-orchestration-trace.md) for current results.
