# Corpus discovery

Discovery and downloads were checked on 5 September 2026. The corpus samples calibration, Bayesian uncertainty, conformal prediction, verbal confidence, semantic uncertainty, and activation steering. It tests document conversion across different publication years and TeX styles; it is not a systematic literature review.

`corpus.json` records exact arXiv versions, download status, SHA-256 hashes, byte sizes, and local directories. Its `year` field means first arXiv submission year, not conference year. Each directory contains the official abstract-page snapshot, the unmodified source response as `source.tar`, and the PDF for the same explicit version. Source responses may be gzip-compressed despite the generic filename. Both arXiv and AlphaXiv input URLs are included; the paired documents are downloaded from arXiv.

The three supplied starting papers with verified arXiv matches are:

- [Ji et al., Calibrating Verbal Uncertainty as a Linear Feature to Reduce Hallucinations](https://aclanthology.org/2025.emnlp-main.187/): [arXiv 2503.14477](https://arxiv.org/abs/2503.14477).
- [Joshi et al., Calibration Across Layers](https://aclanthology.org/2025.emnlp-main.742/): [arXiv 2511.00280](https://arxiv.org/abs/2511.00280).
- [Hedström et al., To Steer or Not to Steer?](https://proceedings.mlr.press/v267/hedstrom25a.html): [arXiv 2510.13290](https://arxiv.org/abs/2510.13290).

The fourth supplied paper, [Li, Kuang, and Botelho, Can We Trust AI's Self-Assessment?](https://www.hichipli.com/publications/conferences/aied-2026/llm-confidence-calibration/), is confirmed on the author's page, which links its [AIED 2026 DOI](https://doi.org/10.1007/978-3-032-29755-6_18). Exact-title searches and the author's page did not establish an arXiv identifier. This is an unresolved match, not proof that no arXiv copy exists. The author-hosted PDF was downloaded to `.verification/corpus/li-aied-2026/paper.pdf`. It is excluded from the arXiv source-conversion denominator. The author page labels the conference AIED 2026; the downloaded Springer typeset PDF prints a 2027 publication/copyright year. This discrepancy is retained rather than silently resolved.

The added papers were identified by exact-title arXiv searches, then verified against their official abstract pages. Gal and Ghahramani's dropout paper was published at ICML 2016 but first submitted to arXiv in 2015. The 2026 expectation-calibrated predictions paper extends the document sample to current work. It is a preprint; inclusion makes no claim about peer review or scientific quality.

The 2024 item is *Semantic Entropy Probes*, a distinct paper from Farquhar et al.'s Nature 2024 *Detecting hallucinations in large language models using semantic entropy*. The latter's publisher and author pages were found, but no matching arXiv source was established during this bounded search. A citation-list arXiv link on a publisher page must not be treated as the paper's own identifier.

The initial 12-paper downloads used explicit version URLs, at least three seconds between requests, at most two attempts per source/PDF, and a 120 MiB per-response cap. The first sandboxed request failed because DNS access was restricted; the permitted network request succeeded. Network failures are recorded separately from source availability and conversion failures.

## Historical regression additions

On 6 September 2026, four previously troublesome inputs were added. Their latest versions and titles were resolved from official arXiv abstract pages before downloading these pinned versions:

- [2505.07309v1: Uncertainty Profiles for LLMs: Uncertainty Source Decomposition and Adaptive Model-Metric Selection](https://arxiv.org/abs/2505.07309v1).
- [2504.18346v4: Comparing Uncertainty Measurement and Mitigation Methods for Large Language Models: A Systematic Review](https://arxiv.org/abs/2504.18346v4).
- [2410.20199v1: Rethinking the Uncertainty: A Critical Review and Analysis in the Era of Large Language Models](https://arxiv.org/abs/2410.20199v1).
- [2606.19868v1: A Systematic Evaluation of Black-Box Uncertainty Estimation Methods for Large Language Models](https://arxiv.org/abs/2606.19868v1).

All four provided readable source archives containing TeX and matching-version PDF files. The corpus therefore contains 16 source/PDF pairs; the existing author-hosted AIED paper remains excluded. Unavailable-source additions would be recorded outside the conversion denominator. These additions were selected as historical regression cases, not as a representative sample of research quality.

The additions use `papers.acquire.acquire`, with a 60-second per-request timeout and 200,000,000-byte source/PDF limit. Its original `source` and `original.pdf` downloads are retained and copied byte-for-byte to the corpus filenames `source.tar` and `paper.pdf`. Download hashes, PDF signatures, and the presence of TeX archive members were checked for all 16 pairs. No HTTP content type is claimed for these four additions because the acquisition helper does not retain response headers.

Author lists for all 16 papers were read from their saved official abstract-page metadata. `author_names` retains the individual arXiv citation-author values; `authors` joins those values with semicolons. No additional downloads were needed to fill the original 12 author lists.
