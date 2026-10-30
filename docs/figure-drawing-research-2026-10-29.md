# How to draw one figure that carries a Paper: research for the drawing prompts

Date: 2026-10-29. Branch `akhil/hopeful-curie-113b6a`. `DIAGRAM_PROMPT` read at `533ba1f`; `FIGURE_PROMPT` and the brief fields read at main `db04d39` (the two commits have the same `FIGURE_PROMPT`).

**Purpose.** The model draws each Overview and each Blog figure as Mermaid. This note gives the evidence for how to draw one figure so that it carries the essence of the Paper: emphasis, contrast with the prior approach, grouping, arrows, labels, numbers, diagram type, colour, and how a pipeline can make model-drawn figures better. It ends with ranked changes for the owner to accept or reject. This note changes no prompt and no code. It covers the drawing step only. What the Overview plan chooses is in [the 2026-10-28 note](overview-plan-research-2026-10-28.md), and this note does not repeat it.

**Inputs.**
- `DIAGRAM_PROMPT` in [`papers/overview_workflow.py`](../papers/overview_workflow.py); `FIGURE_PROMPT` and `OUTLINE_PROMPT` section "5. figures" in `papers/blog_prompts.py` at `db04d39`; `check()` in [`papers/diagrams.py`](../papers/diagrams.py); [`papers/blog_figures.py`](../papers/blog_figures.py); `papers/mermaid.js`.
- The Excalidraw look: branch `excalidraw-look`, commit `158389c` (2026-10-29). It is not on main or on this branch. I read its `app/static/sketch.js` and `papers/mermaid.js`, and rendered with them in a scratch folder.
- The PRO Paper (`2511.07694v1`, "Probabilities Are All You Need") in the session library: its Overview and Blog values, and its run folders (`events.jsonl`, `requests/`). The spike outputs in `spikes/mermaid-overview/out*` (not in git), for three Papers.
- Probes: I drew 15 small Mermaid sources with `papers/mermaid.js` (Pele 1.12.0) and ran `check()` on two of them. L10 to L13 give the results.
- 22 published sources read on 2026-10-29 through Exa (S47 to S68), plus deeper reads of S5, S22, S23, and S24 of the 2026-10-28 note.

**Rules.**
- Each claim has a citation key. S keys are published sources. L keys are facts from this repository, the local library, and the probes.
- This note continues the key numbers of the 2026-10-28 note. A key from that note is written "[2026-10-28 note, S21]". New keys start at S47.
- *Unconfirmed* marks an inference that no source states directly, or a claim with thin evidence.
- Evidence strength: **strong** is a controlled experiment, a meta-analysis, or a large annotated dataset. **Moderate** is a peer-reviewed study with a small sample, an interview study, or a benchmark with a model judge. **Weak** is expert opinion, a style guide, or a tool's documentation used as evidence of practice.
- Mermaid syntax facts come from mermaid.js.org [S65]. Pele behaviour comes from probes [L10 to L13], because Pele has its own layout [S66].

**Caveat on the local data.** The Mermaid pipeline has few runs: one Overview and three Blog figures for PRO, and the spike answers for three Papers (L4 counts `out-v3` and `out-v4`). The local facts show failure types. They do not give failure rates.

## 1. Summary

- **Arrows break the prompt's own rule.** `DIAGRAM_PROMPT` says "Every arrow means the output of one node goes into the next." The PRO Overview draws arrows from the problem into the method group, from the NLL baseline into "AUC evaluation", and from the method group into the result group [L1]. Readers read arrows as steps and causes, and enclosures as containers [2026-10-28 note, S21; S54]. Give the problem, the comparator, and the numbers places of their own, with no arrows into the path.
- **One strong colour, on the new part.** The PRO Overview uses 6 fill colours on 10 nodes, with two competing highlights and a red–green pair [L1; L9]. A unique item stands out only when the rest of the view has little variety [S49]. Highlighting one group guides the first comparison [S47; S23]. Signaling helps learning (g = 0.53 for retention) [S48]. Readers who see colour without meaning are confused [2026-10-28 note, S22].
- **Charts mislead at their axis.** The Overview chart starts its axis at 0.65. The PRO bar draws 1.37 times as high as the NLL bar; the true ratio is 1.034 [L2]. Truncated axes make differences look larger, even with labels [2026-10-28 note, S35; S56]. Write the difference as text [S47].
- **The checks reject correct math and force meaning changes.** The asterisk check rejects the paper's notation `p*_K` and valid `$$p^*_K$$` TeX [L5]. The shape check made the model replace node-to-node arrows with group-to-group arrows, because Mermaid ignores a subgraph's direction when its nodes link outside it [L3; S65]. Fix the checks; give the model the row layout that passes.
- **Contrast with the usual approach helps when it is aligned.** Case comparison gives d = 0.50 over single cases [S53]. Aligned placement makes comparison faster and more accurate [S52]. Side-by-side placement puts the burden on memory unless the difference is shown [S51]. *Unconfirmed* for a 30-second figure: one small grey row for the usual approach, aligned above the paper's row.
- **Self-critique: deterministic checks first.** A vision critic raised faithfulness in PaperBanana (30.7 to 45.8, VLM judge) [2026-10-28 note, S24], but critics miss connection errors [S24; S61], and layout improves least [S59]. Compiler feedback mattered more than model verification in DiagramAgent [S60]. Mermaid source gives the graph exactly, so check the graph from the source.
- **Proposals.** Section 4 gives 9 prompt or check changes and 6 pipeline changes. The five with the most effect: an arrow grammar with an edge check (B1), app-owned emphasis classes with one highlight (X1 with B2), honest result charts (B3 with C1), math-aware checks (C2), and a row layout that passes the shape check without changing arrows (B4).

## 2. Findings

### 2.1 Visual hierarchy and emphasis

**Highlight one group so that the reader makes the right comparison first.** Designers add salient colour to a single group so that viewers process that comparison first. Low-knowledge readers gain most; experts rely on prior experience [S47; strong, review of controlled studies]. Rougier et al. give the same rule: use colour for the element to highlight, and keep other elements grey or black. "If you don't know the answer, just keep it black" [2026-10-28 note, S23; weak].

**Cues help learning.** A meta-analysis of 103 studies (N = 12,201) found that signaling improves retention (g = 0.53, 95% CI 0.42 to 0.64) and transfer (g = 0.33, 0.22 to 0.43), and lowers cognitive load. Prior knowledge did not moderate the effect [S48; strong].

**Pop-out needs low variety elsewhere.** Finding an odd item gets harder as the number of distinct colours in the view grows, and grouping makes it easier. The authors advise to "reduce variety in the entire view" for hard tasks [S49; moderate, 5 trained observers, thousands of trials each]. So a figure with six fill colours cannot make one part stand out (*unconfirmed* as a count limit; the study gives no cut-off for diagrams).

**Colour must mean something.** Researchers in an interview study were confused by colour with no stated purpose: "Why some operations are grey, why some operations are blue, some operations are green." Guideline H of the resulting framework is "Do not use colour for aesthetics." Among the 30 most-cited papers in the corpus, 9 used no colour, 13 used colour with meaning, and 8 used colour for aesthetics only [2026-10-28 note, S22; moderate, 12 interviews and 119 ACL 2017 diagrams].

**Journal rule: colour directs focus to the new findings.** Cell Press says colour can direct attention to focal points and establish emphasis. Its examples use colour to "direct focus toward the new findings". It warns against heavily saturated primary colours and against red–green and red–black pairs [2026-10-28 note, S5; weak, publisher guide, read again in full].

**Redundant colour and shape do not help most readers.** Colour is dominant; redundant shape coding gives no perceptual gain except for readers with colour-vision deficiency [S47]. *Unconfirmed*: a thicker border on the new part is a useful second cue for those readers, because it survives grey-scale and the Excalidraw strokes keep it [L8].

**What the new part is.** The 2026-10-28 note proposes a `novel` mark on Digest components (D2) and a plan rule that keeps the novel part (P1). The drawing rules in this note depend on that mark. Without it, the plan item's `why` text is the only signal ("This is the key idea") [L1].

### 2.2 Contrast with the prior approach

**Comparison of cases teaches more than single cases.** A meta-analysis of 57 experiments found d = 0.50 (95% CI 0.44 to 0.56) for case comparison over sequential, single-case, and other study. Comparison helped more when learners looked for similarities, when the principle came after the comparison, and when the content was perceptual [S53; strong].

**Alignment makes comparison fast.** Four experiments showed that comparison of two visuals is faster and more accurate when matching parts sit in direct alignment: visuals that change along a horizontal axis go one above the other; visuals that change along a vertical axis go side by side [S52; strong].

**Juxtaposition costs memory; explicit encoding removes it.** Side-by-side views are simple but "place too much of the comparative burden on a viewer's memory". Explicit encoding shows the difference itself, but needs the relationship to be known [S51; weak to moderate, a taxonomy paper]. Franconeri et al. describe dashboards that plot the delta directly [S47].

**Journal rule pulls the other way.** Cell Press asks for the new findings "without including excess details from previous literature" [2026-10-28 note, S5].

**Inference for LocalXiv.** *Unconfirmed*: when the Overview plan names the usual approach (proposal D3 of the 2026-10-28 note), one row of at most 3 grey nodes above the paper's row, aligned step for step, shows the change; the step that differs gets the highlight. Without D3, a contrast row would be the model's invention. The PRO Overview drew the comparator as a box inside the result group, with an arrow into "AUC evaluation" [L1]. Blog fig2 drew the two limit cases of α as branches from the formula, with dashed arrows [L6]. Both are contrasts drawn as process.

### 2.3 Grouping and chunking

**Three to five groups.** Working memory holds 3 to 5 chunks [2026-10-28 note, S17]. A subgraph that the reader takes as one unit counts as one chunk.

**Grouping cues by strength.** Connecting lines are the strongest grouping cue, then proximity, then colour, then shape [S47, citing Brooks 2015]. An arrow therefore groups two nodes more strongly than a shared colour does. *Unconfirmed*: an arrow between two groups that should stay separate (the problem and the method) joins them in the reader's eye.

**Enclosures mean containment.** Closed figures suggest "the possibility of containing certain elements, separating those elements from others" [S54; moderate]. A subgraph is the Mermaid enclosure. It suits a stage of a process, a family of a taxonomy, or the "usual" and "ours" rows of a contrast.

**Grouping helps detection.** Grouped displays make odd items and category counts easier to find [S49].

**Comparisons are slow.** Viewers extract overall statistics at once, but make only two or three comparisons per second [S47]. *Unconfirmed*: a 30-second figure supports about one deliberate comparison, so the figure must name which one.

### 2.4 What arrows mean, and when to draw none

**Arrows mean direction in space, time, motion, or cause.** Diagrams with arrows were read as function and sequence; without arrows, as structure [2026-10-28 note, S21; S54; strong for mechanical diagrams].

**One arrow type for one meaning.** Guideline B of the neural-network framework is "Only use one type of arrow for information flow". The evaluation rated it among the least useful, and 6 of the most compliant diagrams used several arrow types to separate kinds of flow or levels of abstraction [2026-10-28 note, S22; moderate]. So the evidence supports one meaning per arrow type, not one arrow type per figure.

**Data flow and control flow do not mix.** Zobel's advice, which the same study confirmed, is that "a schematic showing data flow in an architecture is likely to be unclear if control flow is also illustrated" [2026-10-28 note, S22].

**Include the input and the output; make the figure self-contained.** No top-quartile paper in the corpus broke the self-contained guideline, and all but three of the top 27 showed the input and the output [2026-10-28 note, S22].

**What the local figures do.** The PRO Overview uses arrows for four meanings: "motivates" (problem to method), "leads to" (method group to result group), "is compared in" (baseline to evaluation), and "produces" (evaluation to numbers). The "Lower-bound guarantee" node has no arrow at all [L1]. Blog fig2 uses three: data flow, "if α takes this value" (dashed, labelled), and "is bounded by" (three arrows into H(Y|x) ≥ PRO(x)) [L6].

### 2.5 Labels: words, boxes, edges, and math

**Name parts the way the field names them.** Readers want conventional names and specific parts; "the embedding layer could be anything" [2026-10-28 note, S22, guidelines I and K]. Unexplained symbols frustrated 9 of 12 researchers [2026-10-28 note, S22].

**Put the words on the thing.** Integrated text and pictures beat separated text and pictures (d = 0.85, 95% CI 0.68 to 1.02, 50 effects), more so for complex material [S55; strong]. Direct labels beat legends for speed and accuracy [S47, citing Lohse 1993]. Mermaid node labels are direct labels, so the Overview needs no legend. *Unconfirmed*: the colour of the new part needs no legend when the node label itself names the new part.

**Boxes are things; arrows are actions.** Enclosed figures read as objects and containers, arrows as actions and direction [S54]. *Unconfirmed*: a box label is a noun phrase (the part), and a verb goes on an arrow label only when the arrow carries a named operation.

**Math in labels.** Pele draws `$$TeX$$` through MathJax in plain and markdown labels [L5]. In a markdown string, Mermaid reads single asterisks as italics [S65]. A probe drew "p*_1 and p*_2" as "p1 and p*_2", with no error [L5]. Blog fig1 showed raw TeX braces, "e^{-NLL(y|x)}", because the model copied a backtick equation from the brief into a markdown string [L7].

**What the 8-word check counts.** Most over-long labels were a name plus a description line, such as "Sinusoidal positional encoding adds token order to every embedding". Others went over because math tokens count as words, such as "p*₁ ≥ p*₂ ≥ … ≥ p*_N" [L4].

### 2.6 Numbers on the figure

**Truncated axes exaggerate.** In a crowdsourced test, viewers rated the difference between two values about 1.5 on a 1-to-5 scale with a zero baseline, and 2.8 with a truncated one, after attention checks [S56, as reported by S47; strong]. The effect persists when viewers can read the axis labels [2026-10-28 note, S35; S47]. Rougier et al. show 0-to-100 against 80-to-100 bars and say the effect persists "even if we had used labels" [2026-10-28 note, S23].

**Zero is not always the right floor.** Franconeri et al. note that some measures have no natural zero, and a zero baseline can hide a real change [S47]. *Unconfirmed* for LocalXiv: AUROC has a reference level at 0.5 (random). An axis from the reference level, with that level named, is honest; an axis from an arbitrary value such as 0.65 is not.

**Give the number and the difference as text.** If numeric values matter, write them on the figure or elsewhere [2026-10-28 note, S23, rule 4]. Plot the delta directly when the delta is the message [S47]. On a zero-based bar chart, 0.739 against 0.715 is a 3% height difference [L2]. *Unconfirmed*: the chart title or a data label carries "+0.024 AUROC over NLL", so the reader sees both the true scale and the gain.

**Bars compare discrete items; lines show trends.** Readers produce and interpret bars for discrete comparisons and lines for trends [S54].

**Local failures.** The Overview chart axis runs from 0.65 to 0.75 [L2]. The spike chart for PRO ran from 0.68 to 0.75; the PRO bar drew 1.69 times the NLL bar for a true ratio of 1.034 [L2]. Blog fig3 drew a method comparison as boxes, with no difference and no magnitude [L6].

### 2.7 Choosing the diagram type

| Idea | Drawing | Basis |
| --- | --- | --- |
| Pipeline or method steps | flowchart, one direction, arrows for data flow | [2026-10-28 note, S21; S54] |
| Architecture | flowchart with subgraphs for containers, one level of nesting, plus a zoom on the new part | [2026-10-28 note, S16; S22] |
| Algorithm loop | flowchart with one back arrow, labelled with its condition | *Unconfirmed* |
| Contrast, usual vs. ours | two aligned rows; the step that differs highlighted | [S52; S53; S51] |
| Numbers compared across methods | xychart bar from 0 or from the named reference level, values as labels, difference in the title | [S47; S56; 2026-10-28 note, S35] |
| Trend along an ordered factor | xychart line | [S54] |
| Trade-off between two measures | quadrantChart | *Unconfirmed* |
| Taxonomy or structure | block or mindmap, no arrows | [2026-10-28 note, S21]; proposal G1 of the 2026-10-28 note |
| State change, before and after | stateDiagram, or two aligned rows | [S52] |
| Timeline or messages between parties | timeline or sequence diagram | `FIGURE_PROMPT` already |

The brief's content items have a `kind`: statement, value, equation, connection, qualification, or label [L12]. `FIGURE_PROMPT` does not say how to draw each kind. Blog fig2 drew a qualification ("alpha = 0 keeps all N answers") as a branch of the formula [L6].

### 2.8 The hand-drawn look

**Sketchy rendering lowers precision and raises engagement.** Relative area judgement got worse with sketchy rendering; viewers judged sketchiness only on an ordinal scale, with about 30% error. In an exploratory study, clearly sketchy figures raised engagement [S57; moderate]. A sketch style "conveys to the viewer that the data is approximate" [2026-10-28 note, S23, rule 9, citing Schumann et al. 1996].

**What the Excalidraw look changes.** `sketch.js` redraws outlines and lines with roughjs at roughness 1. Fills, text, arrowheads, and TeX labels stay as Pele drew them; the text is Excalifont. Chart bars have no stroke, so they stay crisp [L8]. The same `sketch.js` draws the on-screen Figure render and the exports, so both get the same strokes [L8]. Widths changed by at most 5% in four figures [L8]. *Unconfirmed*: the hand-drawn strokes say "illustrative" to the reader, which suits the mechanism but not the result numbers.

### 2.9 How models draw better diagrams

**Plan, then draw.** DiagrammerGPT has an LLM write a plan of entities, relationships, and bounding boxes, and a second LLM audit the plan for up to 4 rounds before drawing. The authors report that refinement "can effectively help correct some small errors". The planner's quality depends on the model: layout recall 78.4 for GPT-4 against 29.2 for LLaMA 3 8B [S58; moderate]. PaperBanana's planner works from retrieved example figures; random examples did about as well as matched ones, so general patterns matter more than content match [2026-10-28 note, S24; moderate, preprint, VLM judge].

**A critic on the rendered image raises faithfulness.** In PaperBanana, three critic rounds raised faithfulness from 30.7 to 45.8 and the overall score from 45.6 to 60.2; one round gave 51.8. A style agent raised conciseness by 17.5 points and lowered faithfulness by 8.5; the critic recovered it [2026-10-28 note, S24; moderate, preprint; the VLM judge was checked against two researchers on 50 cases]. SciDoc2Diagrammer-MAF used separate critics for completeness, faithfulness, and look; human ratings rose by about 1 point on a 5-point scale for completeness and faithfulness, and layout improved least, which the authors trace to the model's "inability to refine on specific criteria" [S59; moderate].

**Critics miss connections.** PaperBanana's main failure was connection errors, and its critic "often fails to identify these connectivity issues" [2026-10-28 note, S24]. Four VLMs averaged 58% on seven simple geometric tasks, such as whether two lines cross, and did well only when shapes were far apart [S61; strong benchmark]. A reference-free judge that grounds a multimodal auditor in structural facts parsed from the code matched human ratings (ρ = 0.715) better than an ungrounded judge; remaining failures were in topology, label grounding, and syntax [S62; moderate, abstract only]. DiagramEval scores diagrams as graphs of nodes and paths, because image metrics react to layout [S67; moderate, abstract].

**Compiler feedback beats model verification.** In DiagramAgent, removing the compiler step cost more than removing the GPT-4o verifier: Pass@1 fell by 15.56 against 6.30 on diagram coding, and by 0.74 against 0.37 on generation [S60; moderate]. LocalXiv's Diagram checks are this compiler-style feedback.

**Corrections can lose earlier work.** Multi-turn refinement shows quality drift and forgetting of features made in earlier turns [S64; moderate, preprint, abstract]. The PRO Overview correction fixed the shape and lost the node-to-node data path [L3].

**What no source measures.** I found no ablation of a vision critic on Mermaid figures, and no study of LLM-drawn figures that measures reader comprehension.

## 3. Local evidence

| Key | Fact |
| --- | --- |
| L1 | PRO Overview, accepted source: 10 nodes; 6 `classDef` fills plus 2 subgraph styles. Two highlights compete: "Adaptive top-K selection" and "PRO score" in dark blue with white text, and the two numbers at 20 px bold on yellow. "Why" is red (`#c0392b`), "Lower-bound guarantee" green (`#2e8b57`). Arrows: "Why" → HOW subgraph, HOW → RES subgraph, "NLL baseline (K=1)" → "AUC evaluation", "AUC evaluation" → each number. "Lower-bound guarantee" has no arrow. The comparator NLL sits inside "What PRO achieves". |
| L2 | PRO Overview chart: `y-axis "AUROC" 0.65 --> 0.75`, bars PRO 0.739, NLL 0.715, SD 0.709, Deg 0.695. Above the axis floor, PRO draws 0.089 / 0.065 = 1.37 times NLL; the true ratio is 1.034. Spike `out-v4` PRO chart: 0.68 to 0.75, 0.059 / 0.035 = 1.69 times. Neither chart writes the difference. |
| L3 | PRO Overview, first answer: node path `D --> E`, `D --> F`, `P --> A`; rejected at 584 × 1210 px (0.48) and for a 9-word label. Correction: two LR subgraphs linked group to group (`P --> HOW`, `HOW --> RES`), accepted at 942 × 909 with the chart. Probe: a row subgraph whose last node links to the next row's first node draws as one column, 166 × 664 (0.25); the same rows linked subgraph to subgraph draw as rows, 461 × 280 (1.65). Mermaid documents this: a subgraph's direction is ignored when its nodes link outside it [S65]. |
| L4 | Rejections in the Mermaid runs from spike `out-v3` onward: 11 rejected answers (spike `out-v3` 3, `out-v4` 5, library 3). Causes: label over 8 words in 8 answers, shape in 7, asterisks in 3, small text in 1. Over-long labels: "Encoder multi-head self-attention 8 heads, all positions in parallel"; "Masked decoder self-attention sublayer no peeking at later words"; "Sinusoidal positional encoding adds token order to every embedding"; "Unified open-ended QA benchmark AUROC · ECE · Brier"; "Why: sampling entropy is costly, inflated by rare outputs"; and with math tokens, "Rank the answers: p*₁ ≥ p*₂ ≥ ... ≥ p*_N", "Adaptive Top-K Selection keep p ≥ α = 0.1", "Model samples N = 10 answers for prompt x". |
| L5 | Math in labels. Blog fig1 and fig2 were rejected for literal asterisks in `p*_K`, `p*_1`, the paper's notation; the corrections wrote `p(K)` and `p₍₁₎`, which the prose does not use. Probe: `A["keep $$p^*_K \ge \alpha$$"]` draws correctly through MathJax and fails `check()` with "These labels show literal asterisks". Probe: in a markdown string, "p*_1 and p*_2" draws as "p1 and p*_2", with no error. |
| L6 | PRO Blog: fig1 is a 5-step vertical chain with a 3-way fan-out to "Rank 1/2/N". fig2 has three arrow meanings: data flow, dashed `-.->|"alpha = 0"|` branches, and three arrows into "H(Y#124;x) ≥ PRO(x)". fig3 compares methods as boxes linked with `~~~`, PRO 0.739 against NLL 0.715, SD 0.709, Deg 0.695, with no difference written and no magnitude drawn; `FIGURE_PROMPT` names xychart for "numbers a reader compares". |
| L7 | Blog fig1 shows raw TeX braces: the label `"\`p(y|x) = e^{-NLL(y|x)}\`"` draws "p(y\|x) = e^{-NLL(y\|x)}". The brief's content item was the backtick-wrapped equation `` `p(y|x) = e^{-NLL(y|x)}` ``. "p₍N₎" mixes subscript and normal glyphs because Unicode has no subscript N. |
| L8 | Excalidraw look (`excalidraw-look`, `158389c`): roughjs `roughness: 1` with a fixed seed per shape; fills, text, arrowheads, and nested TeX SVGs unchanged; Excalifont text measured with its own advance widths; a missing glyph falls back to the system font (code comment; I did not list which math glyphs). Chart bars have `stroke="none"` and are not sketched. Sizes, plain → sketch: Overview 942 × 605 → 963 × 605; Blog fig1 562 × 607 → 569 × 607; fig2 673 × 646 → 641 × 663; fig3 635 × 495 → 604 × 461. Stroke width survives the sketch. |
| L9 | Colours are hard-coded hex in every figure: PRO Overview 6 classes, Blog figs 4, 4, and 5; spike `out-v4` Attention 4, PRO 4, survey 5. Red–green pairs: PRO Overview (red "Why", green "proof"); spike Attention (orange-red "idea", green "result"). Hex colours bypass the Figure palette, so they do not follow the dark theme. |
| L10 | Pele chart probes at the application's chart size (942 × 280): `showDataLabel: true` in the application config draws value labels and keeps the size; the same key in the source's front matter replaced the application size (640 × 457). Two `bar` series draw in two colours (`--pele-series-1`, `--pele-series-2`), so one bar can stand out; with data labels on, the zero bars show "0". `xychart-beta horizontal` draws. |
| L11 | Pele layout probes: two LR subgraphs with no link stack vertically; `U ~~~ O` places them side by side. An outer LR subgraph around two subgraphs did not place them side by side (144 × 504). Two aligned rows of 3 nodes linked `U ~~~ O` draw at 581 × 280. |
| L12 | Pele writes `classDef` names into the SVG (`class="pele-node pele-shape-rect new"`). A `classDef` value with a CSS variable, `fill:var(--pele-accent)`, does not parse. The brief content kinds are `statement`, `value`, `equation`, `connection`, `qualification`, `label` (`PANEL_CONTENT_KINDS`). |
| L13 | `papers/ai.py` sends text content only. No request path sends an image, so a vision critique needs a provider change and a model that reads images. |
| L14 | Cost of corrections today: the PRO Overview diagram took 2 requests (about 5.5k and 7.0k tokens). The three PRO Blog figures took 5 requests. |

## 4. Proposed changes

Prefixes: G for `DIAGRAM_PROMPT` only, F for `FIGURE_PROMPT` only, B for both, C for a check in `papers/diagrams.py` only, X for a pipeline change. The proposed text is short and positive, to fit the terse prompts. Ranked by expected effect.

| Rank | Change | Prompt | Check |
| --- | --- | --- | --- |
| 1 | B1 Arrow grammar | both | yes, with an edge list from `mermaid.js` |
| 2 | X1 + B2 App-owned emphasis classes, one highlight | both | yes |
| 3 | B3 + C1 Honest result charts | both | yes |
| 4 | C2 Math-aware checks, and B5 paper notation in TeX | both | yes |
| 5 | B4 Row layout that passes the shape check | both, and the check message | message only |
| 6 | F1 Drawing for each brief kind and idea type | `FIGURE_PROMPT` | partly |
| 7 | G2 Aligned contrast row with the usual approach | `DIAGRAM_PROMPT` | partly |
| 8 | B6 Group budget | both | yes |
| 9 | B7 Label wording | both | partly |

### 4.1 Prompt and check changes

**B1. Arrow grammar.** Proposed text:
"Draw an arrow only where one node's output goes into the next node. The path runs from the input to the output, and one arrow may join the output to its result. Put the problem, the usual approach, and any guarantee in their own places, with no arrow into the path. Draw a condition or a limit case as its own small node, not as a branch."
- Reason: arrows read as steps and causes [2026-10-28 note, S21; S54]; connecting lines are the strongest grouping cue [S47]; mixing data flow and other flow confuses readers [2026-10-28 note, S22]. The PRO Overview and Blog fig2 use 3 to 4 arrow meanings [L1; L6].
- Check: yes, after `mermaid.js` reports edges (it reports nodes only today). Reject an edge whose source is a node of class `problem` or `prior`, or whose target is a node of class `problem` (needs X1). Reject a dashed or labelled edge whose label holds "=" between two nodes of the path (*unconfirmed* heuristic; test it on the spike set first).

**B2. One highlight, on the new part.** Proposed text, with X1:
"Give each node one class: new for the paper's new part, result for the headline numbers, prior for the usual approach. Leave every reused standard part without a class. Write no colours."
Proposed text without X1:
"Use one strong colour, for the paper's new part, and one soft colour for the result. Draw every other node in the default style. Use no red–green pair."
- Reason: one highlight guides the first comparison [S47; 2026-10-28 note, S23]; pop-out needs low variety elsewhere [S49]; colour without meaning confuses [2026-10-28 note, S22]; journals direct colour to the new findings and avoid red–green [2026-10-28 note, S5; S50]. The figures use 4 to 6 colours with competing highlights [L1; L9]. Depends on D2 and P1 of the 2026-10-28 note for which part is new.
- Check: yes. With X1: reject `fill`, `color`, or `stroke` colour values in `classDef` and `style`; for an Overview, require at least one node of class `new`. Without X1: count distinct fill colours in `classDef` and `style` and reject more than 3.

**B3. Honest result charts.** Proposed text:
"Start a bar chart's y-axis at 0, or at the measure's reference level when the plan names one, such as 0.5 for AUROC. Write the paper's gain over its strongest comparator in the chart title, such as "+0.024 AUROC over NLL"."
- Reason: truncation exaggerates, also with axis labels [S56; 2026-10-28 note, S35; S47]; a delta written out removes the comparison burden [S47; S51]; the reference level is a named score [2026-10-28 note, S30]. The PRO chart triples the visual gain [L2]. Depends on P3 of the 2026-10-28 note for the comparator.
- C1, check: yes. Parse the `y-axis` range of an `xychart` with `bar`. Reject a minimum other than 0 unless it equals a reference score in the plan. For an Overview with a chart, reject a chart title that has no "+" or "−" number when the plan has a comparator.

**C2. Math-aware checks.** No prompt change for the check itself.
- The asterisk check skips text inside `$$…$$` (`mermaid.js` already marks TeX labels) and an asterisk between a letter and `_`, `^`, a subscript digit, or a space, as in `p*_K` and `p* ≥`.
- The word count skips TeX, tokens with no letters (`=`, `≥`, `0.1`, `…`), and one-letter symbols.
- A new rejection: a plain label that holds `^{` or `_{` outside `$$…$$`, with the message "Write this equation as $$TeX$$".
- Reason: the asterisk check rejected the paper's own notation and valid TeX, and the correction changed the notation [L5]; math tokens made labels "too long" [L4]; raw braces reached the reader [L7]. The paper's symbols must stay as the paper writes them [2026-10-28 note, S22, unexplained symbols].

**B5. Paper notation in TeX.** Proposed text:
"Write an equation or a symbol with a star, a hat, or a subscript as $$TeX$$, with the paper's symbols: $$p^*_K$$. Write a brief's backtick equation as $$TeX$$."
- Reason: [L5; L7; S65].
- Check: C2.

**B4. A row layout that passes the shape check.** Proposed text:
"For a path of 4 or more steps, draw rows: one subgraph for each row, with direction LR, and link the rows to each other, not their nodes. Mermaid ignores a subgraph's direction when its nodes link outside it."
Add to each shape error message: "Keep the same arrows between the same nodes."
- Reason: shape caused 7 of 11 rejections [L4]; the correction changed the arrows' meaning [L3]; the Mermaid limitation explains why [S65; L3]; corrections lose earlier work [S64].
- Check: message only. *Unconfirmed* extra check: compare the node-level edges of a correction with the previous answer and name the dropped edges in the error.

**F1. A drawing for each brief kind and each idea type.** Proposed text for `FIGURE_PROMPT`:
"Draw each content item by its kind: a statement or a value as a node; an equation as a $$TeX$$ node; a connection as an arrow, with a short label when it names an operation; a qualification as a small node with no arrow; a label as text on a group. For numbers a reader compares, draw an xychart bar from 0 with the gain in the title. For a structure, draw groups with no arrows. For two cases, draw two aligned rows."
- Reason: the brief has six kinds and the prompt says how to draw none of them [L12]; a qualification drawn as a branch [L6]; numbers drawn as boxes [L6]; bars for discrete comparisons [S54]; aligned rows [S52].
- Check: partly. When every illustrative value is a number with a method name and there are 3 or more, require an `xychart` (*unconfirmed* rule; the brief has no field that marks a comparison).

**G2. Aligned contrast row with the usual approach.** Proposed text for `DIAGRAM_PROMPT`:
"When the plan names the usual approach, draw it as one row of at most 3 nodes of class prior, above the paper's row, step under step. Highlight the step where the paper differs."
- Reason: case comparison [S53]; aligned placement [S52; L11]; keep prior detail small [2026-10-28 note, S5]. Depends on D3 and P2 of the 2026-10-28 note, which name the usual approach. Counts against the 12-node limit.
- Check: partly: at most 3 nodes of class `prior` (needs X1).

**B6. Group budget.** Proposed text:
"Use 2 to 4 groups, one level deep. A group is one thing the reader remembers: the problem, the method, the result."
- Reason: 3 to 5 chunks [2026-10-28 note, S17]; grouping helps [S49; S47].
- Check: yes. Count `subgraph` statements and their nesting in the source; reject more than 4 or a depth over 1.

**B7. Label wording.** Proposed text:
"Write a node label as the part's name, as the paper names it, then at most one short line with its value or its equation. Put a verb on an arrow label only."
- Reason: conventional, specific names [2026-10-28 note, S22]; boxes as things, arrows as actions [S54]; most over-long labels were a name plus a description [L4]. The Component hover carries the role.
- Check: partly: the 8-word limit already covers length; C2 makes it fair to math.

### 4.2 Pipeline changes that a prompt cannot make

| Key | Change | Cost |
| --- | --- | --- |
| X1 | The application owns the emphasis colours. It styles the classes `new`, `result`, `prior`, and `problem` with Figure palette colours in the page CSS and in `write_assets`, light and dark, from one colour-blind-safe set [S50]. The model writes class names only (B2). Pele already writes class names into the SVG [L12]. | No request. CSS and one check. |
| X2 | The application sets `showDataLabel: true` in `chart_config` (not in the source, which replaces the size) and colours the bar whose label is the paper's method with the `new` colour, by editing the chart SVG [L10]. | No request. |
| X3 | Edges in the `mermaid.js` report: source, target, line style, and label. B1, B4, and the C checks need them. | No request. |
| X4 | A layout note before the source: the same diagram request asks first for `"layout"`: the rows, the groups, and the one highlighted node, then the Mermaid. This is plan-then-draw inside one request [S58; 2026-10-28 note, S24]. *Unconfirmed*: no source isolates an in-request plan. | No extra request; about 100 more output tokens. |
| X5 | A grounded vision critique after the Diagram checks pass: send the rendered PNG with the parsed node, edge, and class lists, and ask fixed questions: Which node draws most attention? Is any text cut or overlapped? Does the figure match the plan's through-line? Act only on a named fault. Do not ask it about connections, which the source already gives [S61; 2026-10-28 note, S24; S62]. Needs image input in `papers/ai.py` [L13]. | Overview: +1 vision request, +1 redraw when it finds a fault (about +6k to +13k tokens). Blog: +1 to +2 requests for each figure, 3 to 8 figures, so +3 to +16 requests. |
| X6 | The sketch skips the `result` nodes and the chart, so the numbers draw crisp and the mechanism draws hand-drawn. Sketchy rendering lowers precision and reads as approximate [S57; 2026-10-28 note, S23]. The chart is already crisp [L8]. | No request; a class filter in `sketch.js`. |

## 5. How to test the changes

1. Use the three spike Papers and PRO, with fresh Digests and Overview plans (the 2026-10-28 note, section 5, step 1).
2. Draw each Overview and each Blog figure with the current prompts, then with B1 to B7 and X1 to X3. Keep the model and the reasoning level fixed. Draw each figure 3 times, because the answers vary.
3. Measure from the source, with no reviewer:
   - corrections for each figure, and the cause of each rejection [L4];
   - arrows that break B1: edges into or out of `problem` and `prior` nodes, and edges with more than one line style;
   - distinct fill colours, and red–green pairs;
   - chart distortion: drawn height ratio ÷ true ratio of the top two bars (1.0 is honest) [L2];
   - edges dropped by a correction [L3].
4. Measure the reader's first look. A model answers from the image alone, as in the 2026-10-28 note, section 5: "Which part is new in this paper?", "What does the paper compare against?", "By how much does it win?" Score the answers against the Digest. Compare the current and the changed figures.
5. Simulate deuteranopia on the PNG of each figure, and check that the `new` node still differs from its neighbours in lightness.
6. Run X5 last, on the same set, only after X3. Count the faults it finds that the checks did not, and the faults it invents.

## 5a. First test of the prompt changes

On 2026-10-29, branch `figure-prompts` applied B1, B2 (without X1), B3, B4, B5, B6, B7, F1, and C2 (the asterisk part only). A script drew the Overview of 4 Papers from their saved Digests. Each Paper had one shared Overview plan, drawn once with the `DIAGRAM_PROMPT` of main and once with the new one, on `claude-opus-5-5` at medium reasoning. Each figure was drawn once, so the counts show a direction, not a rate.

| Paper | Prompt | Requests | Fill colours | Edges | `$$TeX$$` labels | Chart axis floor |
| --- | --- | --- | --- | --- | --- | --- |
| Attention (1706.03762) | main / new | 3 / 2 | 5 / 2 | 12 / 7 | 0 / 2 | none |
| PRO (2511.07694) | main / new | 2 / 2 | 4 / 2 | 6 / 5 | 0 / 3 | 0.69 / 0.5 |
| Black-box survey (2606.19868) | main / new | 1 / 2 | 6 / 2 | 13 / 0 | 0 / 0 | none |
| Deception probes (2502.03407) | main / new | 3 / 2 | 5 / 2 | 9 / 7 | 0 / 3 | 0.9 / 0.5 |

What changed in the figures:
- The problem box has no arrow into the method in all 4 new figures. The survey draws its families as a structure, with no arrows.
- The paper's symbols draw as TeX: $p^*_k \ge \alpha$, $\sigma(w \cdot x' + b)$. The figure from main drew `s_t = w·x't_` as broken text.
- Both charts start at the 0.5 chance level. The PRO chart title gives the gain: "+0.024 AUC over negative log-likelihood".
- Two gaps showed, and the same day's prompt change closed both in a second draw: the strong colour spread over a whole group (4 attention nodes, 5 survey families), and the Attention figure lost its comparator. The prompts now limit the strong colour to 1 or 2 nodes, and ask for each headline number with its comparator.

What the drawing step cannot fix: the survey plan chose "5 method families" and "500 test samples" as headline numbers. That is proposal P5 of the 2026-10-28 note.

## 6. What this research does not settle

- **A contrast row in 30 seconds.** Comparison helps learners [S53], and alignment helps comparison [S52]. No source tests a usual-versus-ours row in a first-pass research figure, where it costs nodes and attention against the rule to omit prior detail [2026-10-28 note, S5].
- **A vision critique on Mermaid.** The critique gains come from image-generated figures and from model judges [2026-10-28 note, S24; S59]. Mermaid source gives the structure exactly, so the remaining gain may be small. No source measures it.
- **The hand-drawn look and trust in numbers.** Sketchiness lowers precision and raises engagement [S57], and reads as approximate [2026-10-28 note, S23]. No source tests it on a research summary with real results.
- **One highlight or two.** The sources support one salient group [S47; S49]. The Overview also needs the headline numbers to stand out (`CONTEXT.md`, Overview). Whether a second, softer result colour costs the new part's pop-out is untested.
- **The reference level as the axis floor.** Zero can hide a real change [S47], and truncation exaggerates [S56]. Starting at a named reference level, such as random AUROC, is an inference.

## 7. Leads that did not hold

- **DeTikZify's MCTS refinement** scores candidates by similarity to a target image [S63]. LocalXiv has no target image, so the method does not transfer. I read the abstract only.
- **DiagramAgent's check agent** compiles and then asks GPT-4o for completeness [S60]. LocalXiv's Diagram checks already do both parts in deterministic form; the ablation supports them, but adds no new rule.
- **MermaidSeqBench [S68], Merbench, and the Braintrust Mermaid eval** test syntax success or sequence-diagram logic with LLM judges, or score aspect ratio by hand. None gives a drawing rule or a measured effect of one.
- **Redundant colour and shape coding** gives no gain for most readers [S47]. It is kept only as a second cue for colour-blind readers.
- **PaperBanana's style guide** (appendix F) was past the part of the page I could read. I have its method and its ablation, not its rules.
- **Not read at the source:** Okabe and Ito (2002), the palette that S50 cites; Lohse (1993), Moreno and Mayer (1999), Canham and Hegarty (2010), and Brooks (2015), all as reported by S47; Heiser and Tversky beyond the 2026-10-28 note's excerpt; AutomaTikZ.

## 8. Sources

Read on 2026-10-29. "Full" means the whole text was read. "Excerpt", "sections", or "abstract" means less; give those rows less weight. S58, S63, S64, and S67 are preprints or workshop papers; S59, S60, S61, and S62 are peer-reviewed venue papers. Sources from the 2026-10-28 note that I read again: S5 (full), S22 (sections 4.4, the framework creation in section 5, 6.3, 7.3, 8.1 to 8.3; not the evaluation study in section 5), S23 (rules 5 to 10), S24 (sections 3, 4.2, 5.4, appendix B, failure cases).

| Key | Source | Venue, year | Read | URL |
| --- | --- | --- | --- | --- |
| S47 | Franconeri, Padilla, Shah, Zacks, and Hullman, The Science of Visual Data Communication: What Works | Psychol Sci Public Interest, 2021 | excerpts by keyword search of the full text: truncation, comparison limits, grouping cues, highlighting, legends, colour vision | https://journals.sagepub.com/doi/full/10.1177/15291006211051956 |
| S48 | Schneider, Beege, Nebel, and Rey, A meta-analysis of how signaling affects learning with media | Educ Res Rev, 2018 | abstract, highlights | https://doi.org/10.1016/j.edurev.2017.11.001 |
| S49 | Haroz and Whitney, How Capacity Limits of Attention Influence Information Visualization Effectiveness | IEEE TVCG, 2012 | abstract, experiment 1, conclusion | https://whitneylab.berkeley.edu/PDFs/Haroz_Whitney_2012_InfoVis.pdf |
| S50 | Wong, Points of view: Color blindness | Nature Methods, 2011 (correction 2023) | preview, correction | https://www.nature.com/articles/nmeth.1618 |
| S51 | Gleicher, Albers, Walker, Jusufi, Hansen, and Roberts, Visual comparison for information visualization | Information Visualization, 2011 | sections 3.4, 4 | https://graphics.cs.wisc.edu/Papers/2011/GAWJHR11/paper.pdf |
| S52 | Matlen, Gentner, and Franconeri, Spatial alignment facilitates visual comparison | J Exp Psychol Hum Percept Perform, 2020 | abstract, introduction | https://groups.psych.northwestern.edu/gentner/papers/MatlenEtAl_2020-SpatialAlign.pdf |
| S53 | Alfieri, Nokes-Malach, and Schunn, Learning Through Case Comparisons: A Meta-Analytic Review | Educational Psychologist, 2013 | abstract, results excerpt | https://www.lrdc.pitt.edu/nokes/documents/alfieri_et_al.,_2013.pdf |
| S54 | Tversky, Zacks, Lee, and Heiser, Lines, Blobs, Crosses and Arrows | Diagrams 2000, LNAI 1889 | sections 5 to 7 | https://www.tc.columbia.edu/faculty/bt2158/faculty-profile/files/_Diagrammaticcommunicationwithschematicfigures.PDF |
| S55 | Ginns, Integrating information: A meta-analysis of the spatial contiguity and temporal contiguity effects | Learning and Instruction, 2006 | abstract, results excerpt | https://doi.org/10.1016/j.learninstruc.2006.10.001 |
| S56 | Pandey, Rall, Satterthwaite, Nov, and Bertini, How Deceptive are Deceptive Visualizations? | CHI, 2015 | abstract; result as reported by S47 | https://dl.acm.org/doi/10.1145/2702123.2702608 |
| S57 | Wood, Isenberg, Isenberg, Dykes, Boukhelifa, and Slingsby, Sketchy Rendering for Information Visualization | IEEE TVCG, 2012 | abstract, sections 5.2, 6 (start), conclusion | https://openaccess.city.ac.uk/id/eprint/1274/1/wood_sketchy_2012.pdf |
| S58 | Zala, Lin, Cho, and Bansal, DiagrammerGPT | COLM, 2024 (arXiv 2310.12128) | sections 1, 3, 5.5 | https://arxiv.org/pdf/2310.12128 |
| S59 | Mondal et al., SciDoc2Diagrammer-MAF | Findings of EMNLP, 2024 | sections 1 to 4, RQ1 to RQ4, limitations | https://arxiv.org/html/2409.19242v2 |
| S60 | Wei et al., From Words to Structured Visuals (DiagramAgent) | CVPR, 2025 | main text | https://openaccess.thecvf.com/content/CVPR2025/papers/Wei_From_Words_to_Structured_Visuals_A_Benchmark_and_Framework_for_CVPR_2025_paper.pdf |
| S61 | Rahmanzadehgervi, Bolton, Taesiri, and Nguyen, Vision language models are blind | ACCV, 2024 | abstract | https://arxiv.org/abs/2407.06581 |
| S62 | Zhang et al., QueryDiagramEval | W-NUT at ACL, 2026 | abstract | https://aclanthology.org/2026.wnut-1.18/ |
| S63 | Belouadi, Ponzetto, and Eger, DeTikZify | NeurIPS, 2024 | abstract | https://arxiv.org/abs/2405.15306 |
| S64 | Wu et al., PaperBanana-Interact | arXiv, 2026 | abstract | https://arxiv.org/abs/2608.30241 |
| S65 | Mermaid, Flowcharts Syntax (v12) | tool documentation | full | https://mermaid.js.org/syntax/flowchart.html |
| S66 | Pele 1.12.0 README | tool documentation | full | https://github.com/obsidianmd/pele |
| S67 | Liang and You, DiagramEval | arXiv, 2025 | abstract, introduction | https://arxiv.org/html/2510.25761 |
| S68 | Shbita, Ahmed, and DeLuca, MermaidSeqBench | arXiv, 2025 | abstract, section 3.3 | https://arxiv.org/html/2511.14967v3 |

## 9. The owner's reference figures, 2026-10-29

The owner gave 10 explainer figures as the target style: a sleep-phase memory diagram, an LLM roadmap, the DeepSeek-R1 training lineage, the DeepSeekMoE panels (twice), a sliding-window attention mask, two Raschka architecture comparisons (Llama 3.2 vs Qwen3, DeepSeek V3 vs Qwen3), an embedding explainer, the Qwen3 Next zoom figure, and a scaled dot-product attention walk-through. This section records what they do. It is design analysis, not a study; weight it as expert practice.

**What they share, under their layouts:**
- **The message is on the figure.** A large note in the figure's colour stands beside the part it is about: "Wider" and "Deeper", "Not attended to save computation", "only 37B parameters are active". Our figures put the message in a box at the end of the flow, or in the footer.
- **They show the thing.** A 0/1 mask on the tokens "The cat sat on the", attention weights on "Your journey starts with one step", embedding vectors with numbers, Q and K as n × d rectangles, ⊕ and ⊗ operators, a router histogram. One token is traced through (the highlighted row x⁽²⁾). Our figures name each step in a box.
- **Notes narrate.** Handwritten-style notes in the margins say why: "For simplicity, assume all token embeddings are the same". Each note sits next to its part.
- **Colour has one job and keeps it.** Llama is pink in the title, the block, and every number in the notes; Qwen is blue. Models, data, and given models have different colours and shapes in the lineage. Standard parts stay grey or white, the key operation is dark, and red marks only the cut.
- **The space is full.** Containers fit their content, notes and numbers fill the margins, and panels share the width. Our PRO figure had a Problem group around one node and a Result group around two boxes.
- **Rhythm.** The roadmap headers zig-zag, the lineage branches and changes shape, the MoE panels fan out, and box sizes vary. A straight column of equal boxes is rare.
- **Comparison and levels are built in.** The same skeleton repeats for each variant or each historical stage (MoE (a) → (b) → (c), each with a note on what changed), and zoom panels go from the whole model to a block to its operators (Qwen3 Next).

**Measured, and not usable as a check.** On a 40-cell grid, the references cover 43 to 78% of cells with ink and leave a largest empty rectangle of 3 to 20%. Our 10 Overview drawings cover 40 to 55% and leave 7 to 19%. The ranges overlap, so emptiness is a matter of how space is used, not how much.

**Mermaid can draw these.** Probes with Pele and the Excalidraw look drew: two models side by side with a repeat block and variant colours; the mask grid as block-beta; the MoE panels joined with ==>; the lineage with trapezoids for data and steps on the edges; a dashed zoom panel. Two Mermaid rules decide the layout: a subgraph keeps its direction only while its nodes link only inside it, and a node with no link starts a new, empty row (a note must join its node with ~~~).

**A hand-drawn target.** `DIAGRAM_EXAMPLE` in `papers/overview_workflow.py` is the PRO Overview drawn to these rules: three numbered rows titled with the plan's items, five answers with probabilities (three kept in blue, two dropped in red at α = 0.1), the PRO formula as the dark key operation, and three notes in the figure's voice. It passes the Diagram checks after two check changes: notes (a class name that starts with `note`) may have 16 words, and an equation in `$$TeX$$` counts as one word. Width ÷ height is 1.7, so the shape limit rose from 1.4 to 2.0.

**Changes.** `DRAWING_RULES` in `papers/diagrams.py` holds these rules once, for both prompts: message, worked example, notes, colour jobs, full space, rhythm, the layout patterns (steps, variants, progress in stages, zoom, lineage, structure), arrows, labels, and the two Mermaid layout rules. It replaces the single-highlight rule of B2.


**First run with the rules.** The 4 Papers of section 5a, drawn once each from their saved plans, all passed the Diagram checks in 1 to 3 requests. PRO used the paper's own worked example (Gemma-7B, "who was the 6th US president?", the retained p* values, PRO = 0.404). The Deception figure scored three tokens of a lie and an apology. The survey drew the paper's VPD example (Paris 0.62, London 0.18). Attention drew the "making" to "more difficult" attention weights in a zoom panel. Two faults showed: a node with no link floated in an empty row (Attention's numbers, two survey families), and rows of one node (PRO). The rules now say that every node joins another node and that each row holds at least 2 nodes. A redraw of Attention and the survey showed neither fault.

**The row budget.** Commit `3483d5a` added three rules to the end of `FIGURE_PROMPT`. A row holds 3 nodes, a note included. A label or a note of more than 4 words breaks into lines of 2 to 4 words with `<br/>`. A quote of more than 8 words goes in a note. The font-floor message in `check()` names the same fix. Before the commit, Blog figures put 3 or 4 nodes and an unbroken note in a row. At 640 px their text drew at 7 to 10 px, and 1 of 7 figures was omitted after 4 requests. With the rules, the same 7 briefs passed in 11 requests, where the first run took 17. Each brief was drawn once.

**Fixes that the measurements rejected, 2026-10-30.** A review of `3483d5a` found three wording faults. The prompt does not define "quote". The prompt and the font-floor message give the break rule in different words. "Row" can mean one subgraph or the full width of the figure. Each fix was drawn 3 or 6 times, as section 5 asks. The PRO Blog was no longer in the library, so the sample is the 8 stored briefs of 3 Papers (Attention 4, `2508.15794v1` 3, `2509.17192v3` 1), not the 7 briefs above. Every request went to `claude-opus-5-5` at reasoning high.

| Prompt | Change from `3483d5a` | Runs | Accepted | Requests | Too tall | Font floor | Word limit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v6 (`3483d5a`) | None | 6 | 48 of 48 | 66 | 0 | 6 | 11 |
| v7a | All of v7b, plus "row" defined as the full width in the prompt and the font-floor message, and "shorten a note" in the too-tall message | 3 | 23 of 24 | 40 | 4 | 3 | 11 |
| v7b | All of v7c, plus "a string of more than 16 words goes in a row title" | 6 | 46 of 48 | 73 | 7 | 9 | 14 |
| v7c | "A string in `<required>`" for "a quote", and the prompt's break rule in the font-floor message | 6 | 48 of 48 | 73 | 4 | 12 | 11 |

The columns after Requests count rejected requests by the check that failed. One request can fail more than one check.

Too-tall rejections were 0 of 66 requests for v6 and 15 of 186 for the v7 prompts. Every v7 prompt has the two changes of v7c, and the runs did not separate them. A probable cause, not measured: the v7 font-floor message asks the model to break every label of more than 4 words, where v6 asks it to break "each long label or note". A correction then draws more lines. Attention fig1 is 0.64 to 0.80 as wide as high under v6, so more lines take it below the 0.6 limit. v7b also drew 8 row titles of more than 8 words, against 1 for v6, out of 283 and 240 titles.

**Decision.** `FIGURE_PROMPT` and the font-floor message stay as in `3483d5a`. Two faults stay open: the undefined word "quote", and the two wordings of the break rule. Their fixes cost more requests and gave no gain. The "row" fault needs no fix, because the font-floor check measures the drawn width: 4 nodes on one line at 640 px fail after the draw. The review also expected broken notes to make figures too tall. Under v6 that did not occur in 66 requests.

**Long labels, 2026-10-30.** Under v6, 11 of 66 requests failed the 8-word label limit. The labels are of two kinds.

- **Math, 4 of 11.** An example is `"h = 8 heads d_k = d_v = 64"`. The check counted each `=` as a word, so the label counted 9 words, but it has 6. `check()` now counts only the tokens that contain a letter or a digit. A replay of the 252 saved candidates through the new count gave 30 word-limit failures, against 47 with the old count, and no new failure. Each label that now passes is math. All 4 v6 requests then pass every check, so v6 with the new count takes about 62 requests, with 7 word-limit rejections. The Overview uses the same check, and that is one reason for `overview-mermaid-v4`.
- **Real long labels, 7 of 11.** An example is `"Most attacks: average LM rating change less than 1 point"`. The model keeps 9 or 10 words in a label, not in a note. One more sentence after the break rule, "All the lines of a label hold at most 8 words together", was drawn 6 times. It gave 47 of 48 accepted in 62 requests, with 1 word-limit, 5 too-tall, and 8 font-floor rejections. So it saved no requests against v6 with the new count, and it lost a figure: Attention fig1 was omitted after 4 requests. The sentence is not in the prompt. Real long labels stay open, at about 7 rejections in 62 requests.

**Attention fig1 is near the shape limit.** Under v6 it is 0.64 to 0.80 as wide as it is high, and it passed on the first request in 6 of 6 runs. Under the four changed versions of the end of `FIGURE_PROMPT`, it went too tall in 10 of 21 runs: v7a 2 of 3, v7b 4 of 6, v7c 2 of 6, and the long-label sentence 2 of 6. The cause is not known. The long-label sentence changed no check message, and 3 of its 5 too-tall rejections came on the first request, so the probable cause given above for v7 does not explain all of them. The design spec expects a Shape range for Blog figures from live runs.

**The lower Shape limit for Blog figures, 2026-10-30.** Does a Blog figure at 640 px need a lower limit below 0.6? The data says no, so `SHAPE` stays `(0.6, 2.0)` for the Overview and the Blog. A script drew the 314 saved candidates of the runs above again at 640 px, so this result needed no new request.

- The reference figures give no reason for a lower limit. The 0.60 to 1.06 that the `SHAPE` comment gave is the shape of each whole page, with its title, subtitle, and footer. `check()` measures the diagram only, and the reference diagrams measure 0.77 (Attention), 1.54 (survey), and 2.04 (PRO).
- Under `3483d5a`, the 48 accepted Blog figures measure 0.63 to 1.52, and no request failed the Shape check. Attention fig1 measured 0.63 to 0.80. This is the Blog Shape range that the design spec asks for.
- A lower limit helps only the prompts that this section rejected. The table replays the saved candidates. The replay accepts the first candidate that passes every check under the new limit. It cannot know what the model draws without the too-tall message.
- A lower limit accepts taller figures. At 640 px wide, 0.6 is 1,067 px high, more than one laptop screen. The too-tall candidates measure 0.42 to 0.60, at 836 to 1,261 px high.
- The correction loop works. 11 of the 15 figures that went too tall passed in 1 or 2 more requests, at 0.61 to 1.33. Two of the 4 omitted figures are Attention fig1 in `fix-4` and `v7b-1`. Each drew at 0.41 to 0.50 on 3 of its 4 requests. Its other request swung to 1.26 or 1.69 with text below 11 px.
- A node cap does not help Attention fig1. Its too-tall candidates have 12 to 16 nodes, and its accepted figures have 13 to 15.

| Lower limit | Requests, `3483d5a` | Requests, the four changed prompts | Omitted, the four changed prompts | Tallest accepted figure |
| --- | --- | --- | --- | --- |
| 0.60 | 66 | 248 | 4 | 1,058 px |
| 0.55 | 66 | 235 | 2 | 1,134 px |
| 0.50 | 66 | 235 | 2 | 1,134 px |
| 0.45 | 66 | 232 | 0 | 1,181 px |
| 0.40 | 66 | 227 | 0 | 1,261 px |
