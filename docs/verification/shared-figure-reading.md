# Shared text and figure understanding

Verified 2026-09-09 in the source checkout; installed app not rebuilt.

`reading-v3` explicitly reads architecture, framework, mechanism and result images
alongside source text. Its notes distinguish visible details, the authors' explanation,
interpretation, unreadable details and relationships a simplification must preserve.
The whole-paper synthesis identifies the central explanatory figures by citation.
Blog and bento prompts consume these same cached notes. Template availability no
longer makes the weighted-sum Fiziko drawing the preferred attention illustration.

The previous six-image-per-paper cap is gone. Each reading request attaches at most
six images. Additional images in a batch receive a bounded request using nearby
source passages; they do not trigger a second whole-paper reading. This can add
calls for figure-heavy papers, but both output formats reuse the result. The new
reading revision refreshes old caches once.

Live Attention Is All You Need check: four text-and-figure reading batches and one
synthesis, five provider calls, 48,759 reported total tokens. All eight retained
local raster images were attached; no eligible figures were omitted. Notes identify
the encoder/decoder architecture, residual paths, optional masking, the separate
value path, parallel heads, concatenation, final projection and appendix attention
visualizations. No new blog or bento output was generated in this check.

Sanitized traces, cached reading and readable notes are retained in
`.scratch/figure-reading-live`. `paper-understanding.md` presents the generated notes.

19 tests passed via `python3 -m unittest tests.test_reading tests.test_bento`.
The new test proves all eight fixture images are sent in groups of six and two,
their notes enter the shared synthesis, and a later output style reuses the cache.
The UI test, Python compilation and diff whitespace check also passed.

Image reading remains controlled by `overview_vision` for image-capable providers.
This implementation handles local PNG/JPEG assets up to 2 MB each, anchored to
retained XHTML figure passages. It does not inspect PDF-only or SVG-only figures;
unsupported/oversized image assets are recorded as omitted. Generated notes remain
model interpretations, not a verified reconstruction of every diagram.
