# Structured Overview prototype and bibliography filtering

The work began as a visual prototype and bibliography filter. The user subsequently authorized integrating structured authoring into the Overview workflow. No live provider requests, installed-app changes, publication, or release were performed.

## Visual prototype

Run from the repository root:

```sh
xcrun swiftc -O papers/HTMLSnapshot.swift -o .scratch/structured-html-snapshot
LOCALXIV_HTML_RENDERER="$PWD/.scratch/structured-html-snapshot" \
  .scratch/overview-agent-env/bin/python -m papers.prototypes.structured_overview
```

Open `.scratch/structured-overview-prototype/index.html`. The preview switches among D, E and F with buttons or arrow keys and supports a 640px reading view. Each uses the existing Overview export frame. Its expandable details show the scene description and supporting passages or source URLs.

The initial paper-type examples followed these content requirements:

- D, architecture: attention operation → parallel heads → connected encoder and decoder. The cross-attention connection carries encoder keys and values. Learned head roles are not invented. Source passages come from the bundled Attention paper.
- E, survey: four approach families with small examples of what each observes. The taxonomy follows [Shorinwa et al.'s survey](https://arxiv.org/html/2412.05563), especially its introduction and sections 3–6. The numbers and responses in the mini-examples are illustrative.
- F, methodology: the coastline example is carried through candidate scoring, threshold selection, and PRO calculation. [PRO equation 8 and Table 5](https://arxiv.org/html/2511.07694v1) support the operations. Five generations survive at 0.1, including repeated answers. Calculating with the table's rounded probabilities gives 2.086188, which is labeled as a recomputation rather than copied as the exact reported result.

The scene descriptions use rows, stacks, relative weights, flows, parallel branches, linked lanes, family examples, candidate sets and calculations. Code supplies geometry and arrow routing. The examples are hand-authored fixtures. Their production integration is described below. Live provider compliance and latency have not been measured.

Final native checks report no text overlap, clipping, or undersized SVG labels at 640px. After the beginner-explanation revision, D is 960 × 948 pixels, E is 960 × 924, and F is 960 × 911. All remain within the existing 180-word and 45-word-caption budgets. Browser inspection covered all three examples, variant switching, and compact reading. The initial simple-comparison examples were attractive but did not explain architectural stages, so the current preview replaces them. The later integration replaces the separate prototype compiler; the local review page remains outside app routes.

## Beginner-explanation revision

The user's next review asked for the missing transitions, actual survey methods and insights, and an explanation of PRO's negative logarithm. D now follows an illustrative token through matching, normalized weights and value mixing. Its head diagram explains learned maps that mix all 512 inputs into 64 numbers per Q/K/V, with every head processing every token. The encoder–decoder content is unchanged. E includes MARS, CCP, SaySelf, semantic entropy, probes and sparse autoencoders, paired with tradeoffs and the survey's factuality warning. F identifies 0.114 as the smallest retained probability, introduces negative log-probability as surprise, and explains the correction before showing the score. Four decimal places in intermediate values avoid an apparent rounding contradiction.

Sources were rechecked in Attention sections 3.2.1–3.2.3, the survey sections 3–6 and 10, and PRO equation 8 and Table 5. Native render checks were repeated for all three revised artifacts. Source and tests for the bibliography filter were not changed in this revision; the regression results below belong to the earlier implementation.

## Production integration and narrative correction

The user emphasized that an Overview tells the story of the uploaded paper. A relevant collection of terms is insufficient. The revised survey begins with the paper’s question, explains what representative approaches do, states their tradeoffs, and ends with the survey’s synthesis. A probe is defined at its point of use. MARS is explained through the words it weights; CCP and sparse autoencoder name-dropping were removed from the example.

Overview candidates now require `scene` instead of authored `html`. `papers/overview_scene.py` validates a finite vocabulary of rows, flows, parallel branches, linked lanes, concepts with examples, candidates, calculations and notes. Content and relative widths remain model choices; geometry and text layout are application-owned. Native Arial metrics are obtained once per scene through `HTMLSnapshot.swift --measure-text`. The source renderer was compiled at `papers/html-snapshot`, which is ignored by Git. Build and install scripts already include the module and example JSON and compile the native helper.

The author, fresh repair requests and semantic review use scene data. The compiler’s HTML and scene both persist, and evidence review still records the complete compiled candidate’s digest. Old readable figures remain supported. Blog keeps its existing authoring format and can inspect newly saved scene data as reference. No fallback accepts raw model-authored SVG for an Overview.

`papers/overview-examples.json` supplies the production reference tool and the local preview. The preview calls the production compiler, with no paper-specific drawing logic. Its final examples remain inside the 180-word and 960px limits. Final dimensions are D 960 × 959, E 960 × 905, and F 960 × 793. Native checks report no clipped, overlapping or undersized SVG labels. Browser inspection covers the updated narratives and local variant controls.

Verification used real native rendering with scripted provider responses, not live model generation. The native integration test runs generation, saves and reloads the scene through `Library`, makes it available as Blog reference, and exports PDF, PNG and a Kindle EPUB. Additional tests cover unsupported geometry/code fields, invalid links, excessive structure, wide and Japanese glyphs, unmutated scene inputs, deterministic layout, fresh repairs, omission of generated SVG from author/reviewer context, and preservation of the existing bibliography and cancellation boundaries.

The broader relevant regression command was:

```sh
LOCALXIV_HTML_RENDERER="$PWD/papers/html-snapshot" \
  .scratch/overview-agent-env/bin/python -m unittest \
  tests.test_overview_scene tests.test_agent_overviews tests.test_library tests.test_app \
  tests.test_explanation tests.test_reading_bibliography tests.test_reading tests.test_ai \
  tests.test_overview tests.test_pdf_fallback tests.test_figure_readability
```

111 tests ran: 110 passed and the opt-in Keychain smoke test was skipped. The first broad run exposed a historical sample test that expected bibliography-contaminated Overview context to remain reusable by Blog. Its expectation now matches the bibliography rule while still checking that the saved sample is readable. Focused native and agent tests were repeated after final wording changes. No general guarantee of model compliance, scientific correctness, or faster generation follows from these local checks. Unsupported complex layouts must be simplified or reorganized within the scene vocabulary.

## Bibliography filter

`evidence_document()` in `papers/reading.py` supplies a non-mutating evidence view to import-time reading and Overview/Blog generation. It filters reference-section headings and standard LaTeXML, CSL, and EPUB bibliography markers. Inline citations and original passage IDs remain. Source document digests still identify the complete retained paper.

For PDF pages, the filter excludes text between recognized reference and appendix headings. Figure or table pages following the reference list resume body evidence when they contain no numbered reference entries, including when PDFKit puts captions before the section title. It does not infer reference lists without markers. Unusual headings and extraction order still require caution; this is not a universal PDF bibliography parser.

The reading revision invalidates old notes on the next read. The filter also applies to agent passage retrieval, claim validation, and review. Potentially contaminated older Overview references are unavailable to Blog, including a mixed PDF page whose passage ID still exists after trimming.

The bundled Attention paper provided two real-document checks:

- XHTML: 124 original passages, 84 retained for AI, 40 excluded reference entries. Later attention visualizations remain available.
- PDF: 15 original pages, 13 retained for AI. The reference portion of page 10 is removed; reference-only pages 11–12 are excluded; visualization pages 13–15 are preserved exactly. The initial PDF check caught loss of those unnumbered visualizations, and a regression fixture now covers that extraction order.

Final regression command:

```sh
LOCALXIV_HTML_RENDERER="$PWD/.scratch/structured-html-snapshot" \
  .scratch/overview-agent-env/bin/python -m unittest \
  tests.test_reading_bibliography tests.test_reading tests.test_agent_overviews \
  tests.test_ai tests.test_explanation tests.test_pdf_fallback tests.test_figure_readability
```

59 tests ran: 58 passed and the opt-in Keychain smoke test was skipped. Native rendering and the fixture HTTP server required normal macOS execution outside the restricted sandbox. `git diff --check` passed.

## Architecture narration in production

The final feedback requested implementation without another prototype round. Overview planning, authoring, fresh repair and review now share paper-type narrative guidance. Architecture plans describe each selected module's input, transformation and output, and how transitions connect those modules to the proposed system. Review instructions require specific corrections for missing bridges. Teaching order must not imply a false data-flow edge. Existing panel titles, text and captions carry transitions within the same size limits.

The production Attention reference now names the proposed Transformer, repeats attention through multiple learned views, then stacks attention in the encoder and decoder. Q, K and V are introduced locally. Survey and PRO reference content is unchanged. Prompt provenance is `smolagents-staged-scene-v2`; the scene format and renderer revision remain unchanged.

Final validation: all 29 tests in `tests.test_overview_scene` and `tests.test_agent_overviews` passed with the native renderer enabled. This includes all three production example layouts, saved scene reuse, PDF/PNG/Kindle export, and the shared guidance reaching planning, authoring, review and repair. An earlier check caught a 987px architecture page; shortening its introduction restored the existing 960px limit. These scripted checks verify integration and rendering, not live model adherence to narrative instructions. `git diff --check` passed.
