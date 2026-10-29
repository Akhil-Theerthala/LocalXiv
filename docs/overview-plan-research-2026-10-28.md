# What the Overview plan chooses: research for the Digest and plan prompts

Date: 2026-10-28. Branch `akhil/hopeful-curie-113b6a`, from main at `db04d39`.

**Purpose.** The [2026-10-28 Mermaid figures design](superpowers/specs/2026-10-28-mermaid-figures-design.md) moves the quality of the Overview into the Overview plan. This note gives the evidence for what the plan must choose, and what the Digest must hold so that the plan can choose it. It ends with prompt changes for the owner to accept or reject. This note changes no prompt and no code.

**Inputs.**
- `DIGEST_INSTRUCTION`, `PLAN_PROMPT`, `DIAGRAM_PROMPT`, and `validate_overview_plan` in [`papers/overview_workflow.py`](../papers/overview_workflow.py), and `SELECTION_INSTRUCTION` in [`papers/coordinator.py`](../papers/coordinator.py).
- The run 4 spike plans in `spikes/mermaid-overview/out-v4/` (not in git), with the saved Digests and retrieved evidence of the same three Papers in the library database (L1 to L8).
- 46 published sources, read on 2026-10-28 through Exa (S1 to S46). The Sources section gives the read depth of each. I checked two key claims again at their sources: S5 (Cell Press bans data items) and S16 (Table 3 row E).

**Rules.**
- Each claim has a citation key. S keys are published sources. L keys are facts from this repository and the local library.
- *Unconfirmed* marks an inference that no source states directly, or a claim with thin evidence.
- Evidence strength: **strong** is a controlled experiment, a large annotated dataset, or the Paper itself. **Moderate** is a peer-reviewed study with a small sample, or a benchmark with a model judge. **Weak** is expert opinion or a style guide with no data.

**Caveat on the spike data.** The three spike Digests were made on 2026-09-25 and 2026-09-27, before `why` went into `DIGEST_INSTRUCTION` on 2026-10-08. `why` is null in all three [L1]. So the spike plans had no problem or obstacle to read. A fresh Digest can give a better plan before any change in this note.

## 1. Summary

- **A first pass gives the gist, not the parts.** Expert readers want the paper type, the prior approach, the new idea, and the result against a comparator [S1; S2; S4]. The method is one item, the new one. Hyperparameters, training details, and secondary experiments are for the Blog.
- **Choose the items by what carries the result.** A part is load-bearing when it takes part in the main result [S18]. The paper's ablation table shows which parts carry it [S20]. The plan has no signal for this, so it chose by data flow. For Attention it kept two standard parts and left out scaled dot-product attention, the paper's own operation [L2; S16].
- **Three to five groups, not seven parts.** Working memory holds 3 to 5 chunks [S17]. Seven items work only when they form 3 to 5 visible groups.
- **A result number is a tuple with a comparator.** A result is (task, dataset, metric, score, method) [S18; S20; S28]. It has meaning only against the same tuple for another method, with a direction [S7; S20; S29]. The Attention evidence held Table 2 with 8 prior systems. The Digest's one-sentence `result` dropped them, so the plan had no chart data [L3]. The gap is in the Digest schema, not in the Paper or in the evidence selection.
- **A survey has no mechanism path.** Its core is its taxonomy or its comparison table [S37; S38]. A taxonomy is a structure. Arrows make readers see a process [S21]. An evaluation paper's core is what it measures, the conditions it compares, and the reference levels [S30]. The evidence on figures for evaluation papers is thin (*unconfirmed*).
- **Preference is not comprehension.** In several randomized trials, readers preferred visual summaries, but did not understand more from them [S10; S11; S12]. The owner's review of a figure measures preference. Section 5 gives a test that measures comprehension.
- **Proposals.** Section 4 gives 14 changes. The five with the most effect: structured result measures with comparators in the Digest (D1), a `novel` mark and an ablation note on Digest components (D2), item rules on one containment level with a zoom on the novel part (P1), headline numbers with comparators (P3), and a plan shape for each paper type (P5).

## 2. Findings

### 2.1 What a first pass shows, and what it leaves out

**The first pass ends in a decision to read more.** Keshav's first pass takes 5 to 10 minutes: title, abstract, introduction, headings, and conclusions. Figures come in the second pass. After it, the reader knows the five Cs: Category (paper type), Context (the prior work), Correctness, Contributions, and Clarity [S1; weak, one expert's essay]. Scholars read about 20 articles a month past the abstract, for about 30 minutes each [S14; S15; moderate, large self-report surveys]. So a 30-second Overview is a triage step before a reading.

**The first pass carries one central contribution.** A paper succeeds when a reader can tell its main contribution to a colleague a year later [S2; weak]. The abstract goes from the gap, to the method, to the result, to the answer to the gap [S2]. The `through_line` and the order "why, how, what" follow this. The method is one item here: the new approach, not a set of parts.

**Experts name the field and the type of contribution. Results are less frequent.** In SciTLDR, author one-sentence summaries name the field in 85.6% of cases and the contribution type in 68.4%. Only 29.0% give results [S3; moderate, 76 computer-science papers]. A one-sentence summary has less room than a figure, so this is not evidence against headline numbers. It shows that the contribution type comes before the number.

**Skimmers separate novelty from method.** Scim's interviews found four facets that skimmers look for: objective, novelty, method, and result [S4; moderate, IUI 2023, small studies]. Today the plan items have no mark for "new in this paper" against "standard part".

**Journal rules: one point, new findings, little text.** Cell Press asks for one process or one point, the new findings without detail from previous literature, a clear start and end, and no data items [S5; weak, checked again on 2026-10-28]. Wiley gives the same rules [S6]. For protocols, Cell Press recommends at most 6 boxes [S5].

**Numbers: the field decides.** Cell Press bans data in a graphical abstract [S5]. Medical visual abstracts require 1 to 3 outcomes, each with its units, its direction, and the groups compared [S7; weak, practitioner guide]. ML papers report against leaderboards [S20; S28], so ML readers expect the number. *Unconfirmed*: keep the headline numbers for ML Papers, with their comparators.

**The Paper's own first pass.** The Attention abstract names the usual approach (recurrent or convolutional encoder-decoders), the idea (attention only), and the result against the best prior result, ensembles included, and its training cost. It names no sub-layer [S16; strong].

**What the first pass leaves out:** hyperparameters, training details, secondary experiments, related work in detail, and standard parts that every model of the kind has [S1; S2; S5; S19]. The Digest keeps these for the Component hover and the Blog.

**What the plan lacks today:** Category and Context. The Digest has `paper_type`, but the plan does not use it. `why.obstacle` names "what blocks the usual approach", but no field names the usual approach.

### 2.2 How to choose at most 7 items on the mechanism's path

**Three to five chunks.** When grouping is not possible, adults hold 3 to 5 meaningful items. Miller's "seven plus or minus two" comes from tasks that allow grouping [S17; strong, review]. A subgraph that the reader sees as one unit, such as "Encoder ×6", counts as one chunk. So 7 items work only in 3 to 5 groups. The Cell Press limit of 6 boxes is close to this [S5].

**A salient part takes part in the main result.** SciREX defines a salient entity as one that takes part in the paper's results, not one that the paper only mentions [S18; moderate]. The Digest does not record this link for a component.

**Contribution models keep the proposed parts and drop the setup.** NLPContributionGraph sorts a contribution into units: problem, approach ("only proposed system highlights"), setup and hyperparameters, baselines, results, and ablation [S19; moderate]. The annotators found the contribution in the title, the abstract, a few lines of the introduction, and the first lines of the results. Agreement fell as the units got smaller: 67.9% F1 for sentences, 22.3% for triples [S19]. Choosing 7 of 24 components is a fine-grained choice of this unstable kind.

**The ablation table shows which parts carry the result.** AxCell separates leaderboard tables (the paper against other papers) from ablation tables (variants of the paper's own method) [S20; moderate]. *Unconfirmed*: a part that the ablation shows is replaceable is not load-bearing.

**The Attention spike plan failed this test** [L2; S16; strong]:
- The plan kept "Sinusoidal positional encoding". Table 3 row (E) shows learned positional embeddings at 25.7 BLEU against 25.8 for the base model. The sinusoidal choice does not carry the result, although position information is necessary.
- The plan kept "Shifted target input" and "Autoregressive predictions". These are standard parts of an autoregressive encoder-decoder.
- The plan left out "Scaled dot-product attention head" (`softmax(QKᵀ/√d_k)V`). The paper gives it its own section, its own equation, and its own panel (Figure 2). Single-head attention is 0.9 BLEU worse than the best setting.
- The plan mixed levels: "Encoder stack" (depth 1) beside "Encoder multi-head self-attention" (depth 4, inside the stack).

**Arrows mean steps.** In two experiments, people described diagrams with arrows as actions and causes, and diagrams without arrows as structure [S21; strong, mechanical diagrams]. A path that mixes containers ("Encoder stack"), operations ("Masked multi-head self-attention"), and data states ("Shifted target input") mixes the two readings. *Unconfirmed*: the items on one arrow path must be of one kind.

**Mixed levels confuse readers of ML diagrams.** Researchers were confused by diagrams that mix levels of abstraction, by a missing part that they expect, and by a primary part that looks like a minor one [S22; moderate, PLOS ONE 2025]. For the Transformer, an expert expects the attention operation.

**The Paper's own figures give the pattern.** Figure 1 of Attention is the whole architecture. Figure 2 zooms into the attention operation [S16]. So one level for the path, plus a zoom into the novel part, matches how the authors show it.

**Fix the message first.** Rougier et al. ask for the message before the design, and for a figure seen for a short time to show only the most salient part [S23; weak]. The plan stage does this when `through_line` comes before the items.

**Figure generators give no selection rule.** PaperBanana and FigTree score conciseness as abstraction, not box-by-box transcription [S24; S25]. Paper2Poster tests a poster with questions from the paper, answered from the poster alone [S27]. None reports an ablation of content choice [S24 to S27; moderate to weak, preprints with model judges].

### 2.3 Which result numbers a reader needs

**A result is a tuple.** TDMS extracts (task, dataset, metric, score) to build leaderboards, so that readers can choose fair comparisons and strong baselines [S28; strong]. AxCell uses the same tuple [S20]. SciREX adds the method [S18]. The plan's `{value, measures}` puts task, dataset, and metric in one free text, with no method and no comparator.

**A score needs a comparator and a direction.** AxCell defines the leaderboard table as the principal results with comparisons to other papers [S20]. Ibrahim states each outcome against the compared groups, with a direction [S7]. In SciFact, a change from "higher" to "lower" changes whether evidence supports a claim [S29]. Benchmarks also need reference levels: floor, ceiling, human, and random [S30; moderate].

**The baselines were in the evidence.** The Attention evidence held Table 2 (passage p00061), with 8 prior systems: ByteNet 23.75; Deep-Att + PosUnk 39.2 (EN-FR only); Deep-Att + PosUnk Ensemble 40.4 (EN-FR only); GNMT+RL 24.6 and 39.92; ConvS2S 25.16 and 40.46; MoE 26.03 and 40.56; GNMT+RL Ensemble 26.30 and 41.16; ConvS2S Ensemble 26.36 and 41.29; Transformer base 27.3 and 38.1; Transformer big 28.4 and 41.8 (EN-DE and EN-FR BLEU) [L3]. The Digest `result` is one string of at most 400 characters. It kept only "over 2 BLEU above prior reported models". `DIGEST_INSTRUCTION` asks for "the headline finding with its numbers", and asks for compared values only in the evaluation branch. So no chart was possible [L3].

**The table is the record.** The Attention abstract and Table 2 say 41.8 BLEU for English-French. Section 6.1 says 41.0. The Digest and the plan used 41.0 [L4; S16]. Take a headline number from the table that holds its comparators.

**One score can name the wrong winner.** The winner can change with the tuning budget [S31], with point estimates against intervals [S32], and with the choice of tasks [S33] (strong; S33 is a preprint). The Digest's `qualification` is the place for that condition. A headline number and its qualification form one unit [S36; weak to moderate].

**What a comparison chart needs.** *Unconfirmed*, an inference from S34 and S35: every value shares one task, one dataset, one metric, and one unit, or the common scale is false. Axis truncation makes differences look larger, also with explicit marks [S35; strong, CHI 2020]. On a zero-based bar chart, 28.4 against 26.36 BLEU differs by about 7% of the bar height. *Unconfirmed*: the figure must give the difference as text, for example "+2.0 BLEU over the best ensemble". The axis rule stays with the builder, as the design says.

**What the chart takes:** the paper's best variant, the strongest comparator, and the other compared rows of the same measure. For Attention EN-DE that is 8 rows (6 prior systems and 2 Transformer variants); a cap of about 6 bars keeps the strongest. For PRO, Table 1's average row has 8 methods [L5]; the spike chart used 3.

### 2.4 Survey papers and evaluation papers

**A survey's core is its organization.** Review articles usually rest on tables that compare approaches on a set of properties. These tables are the most informative part of the review [S37; moderate]. In TaxoBench, the expert taxonomy is the backbone of each survey [S38; moderate, preprint].

**Expert taxonomies are deep; a first pass shows the top.** In 72 expert taxonomies, the mean depth is 4.9, with about 14 leaf categories [S38]. A 30-second figure can show only the top one or two levels. Category names were the largest gap between model and expert trees [S38]. Model trees are much larger than human trees [S39]. Models organize categories well, but place studies in them less well [S40]. The facet that splits a node changes from branch to branch [S41]. *Unconfirmed*: the Digest must copy the survey's own top-level names and the principle that separates them.

**No arrows between families.** A taxonomy is a structure, so arrows make it look like a sequence [S21]. The spike drew the survey as a flowchart with subgraphs [L6]. The `CONTEXT.md` Overview says "the reader follows it along its arrows". That sentence assumes a process.

**Survey numbers.** The spike survey plan wrote two "headline numbers" that are not numbers: "SteerConf: highest AUROC" and "Sampling-aggregated VPD: best ECE and Brier" [L6]. The plan check needs 1 or 2 numbers, so the model filled the slot with text. The survey's comparison table reached the Digest as its caption only, 82 characters, with no body [L6]. No source gives a rule for headline numbers in a survey [S42; S43; weak]. *Unconfirmed*: a survey needs a headline finding, and a number only when its comparison table gives scores.

**Journal guidance for review graphics is thin.** I found no Cell Press, Wiley, or Elsevier graphical-abstract rule for reviews [S5; S6; S46]. One Elsevier journal asks a review to state its scope and purpose [S42]. Thieme's Graphical Reviews show the origins of the field, the current mechanism, and representative examples [S43]. Both are single journals with no data.

**An evaluation paper's core is the protocol.** BetterBench asks a benchmark to define the tested capability, how the task measures it, how to read a score, and the reference levels [S30]. The finding depends on budget, runs, and task choice [S31; S32; S33]. *Unconfirmed* as a figure rule: the path is what is measured, then the conditions compared, then the finding with its reference level and its condition.

**Ranks are not scores.** A ranking without scores is ordinal. A bar chart of ranks shows a false scale [S35]. *Unconfirmed*: a chart takes scores only.

## 3. Local evidence

| Key | Fact |
| --- | --- |
| L1 | The three spike Digests date from 2026-09-25 and 2026-09-27. `why` went into `DIGEST_INSTRUCTION` in commit `d99fdb8` (2026-10-08). `why` is null in all three. |
| L2 | Attention: 19 components. The plan chose 7: positional encoding, encoder stack, encoder multi-head self-attention, shifted target input, masked multi-head self-attention, encoder–decoder attention sublayer, autoregressive predictions. It left out `attn_head`. The plan was not accepted (one label had 9 words after 3 requests). |
| L3 | Attention: passage p00061 (Table 2) was in the retrieved evidence, with 8 prior systems (6 with EN-DE scores) and 2 Transformer rows. The Digest `result` kept no comparator value. |
| L4 | Attention: abstract (p00002) and Table 2 say 41.8 EN-FR BLEU; Section 6.1 (p00063) says 41.0. The Digest and the plan used 41.0. |
| L5 | PRO: 5 components on one `feeds` chain; the plan took all 5. Table 1 (p00033) has 7 baselines on 15 settings; its average row is SD 0.709, SE 0.618, Deg 0.695, NE 0.595, PE 0.600, ALL 0.646, NLL 0.715, PRO 0.739. |
| L6 | Survey: 23 components (5 families, 18 methods). The plan chose the 5 families and "Unified open-ended QA benchmark", with text in place of headline numbers. The comparison table (p00103) arrived as its 82-character caption. |
| L7 | `SELECTION_INSTRUCTION` asks for a table only "when the headline result is measured across a factor", not for the main results table or the ablation table. |
| L8 | `validate_overview_plan` checks counts and types only. It does not check that an item is a Digest component, that the items share a level, or that the novel part is present. |

## 4. Proposed changes

Each change names the prompt, the change, the reason, and the check that enforces it. The Digest changes (D) make the choice possible. The plan changes (P) make it. Change both together: P1, P3, and P4 read fields that D1 and D2 add. The caps, the chart axis, and the other Diagram checks stay outside this note.

### 4.1 Digest (`DIGEST_INSTRUCTION`, `validate_digest`)

**D1. Give the result as measures with comparators.** Keep `result.text`. Add `result.measures`:

```json
"measures": [{"task": "English→German translation", "dataset": "WMT 2014 newstest2014",
  "metric": "BLEU", "better": "higher",
  "scores": [{"method": "Transformer (big)", "value": 28.4, "ours": true},
             {"method": "ConvS2S Ensemble", "value": 26.36},
             {"method": "GNMT + RL Ensemble", "value": 26.30}],
  "passages": ["p00061"]}]
```

Proposed instruction text: "For each main result, at most 3, copy from the table that compares the paper with other methods: the task, the dataset, the metric, whether higher or lower is better, the paper's best score, and every compared method's score, up to 8. Take the values from the table, not from the prose. A reference level (random, human, prior best) is a score with its name."
- Reason: a result is a (task, dataset, metric, score, method) tuple [S18; S20; S28], read against a comparator with a direction [S7; S29; S30]. The Attention evidence had Table 2, and the Digest dropped it [L3]. The table and the prose can disagree [L4].
- Check: each measure has `metric`, `better`, and at least 2 `scores` with numeric `value`. For architecture and method Papers, at least one measure, with exactly one `ours` score in each. The `passages` exist in the evidence.
- Exception: a survey or an evaluation Paper can have measures with no `ours` score. A survey, evaluation, theory, or other Paper with rankings only, or with no scores, gives no measures and says so in `result.text` [L6]. An architecture or method Paper with no comparator table gets the correction message; the owner decides from the Section 5 test whether that is too strict.

**D2. Mark the novel parts, and record the ablation.** Add two fields to each component:
- `novel`: true when the paper introduces or changes this part; false for a standard part that it reuses.
- `ablation`: optional, at most 80 characters, the paper's ablation result for this part, for example "learned embeddings instead: 25.7 vs 25.8 BLEU (dev)".
- Reason: skimmers look for novelty apart from method [S4]. Journal rules ask for the new findings, not prior detail [S5; S6]. The ablation table shows which parts carry the result [S19; S20]. The Attention plan chose standard and replaceable parts over the novel operation [L2; S16].
- Check: at least one component has `novel: true`, for every paper type except survey.

**D3. Name the usual approach in `why.obstacle`.** Proposed text: "obstacle: the usual approach, by name, and what blocks it."
- Reason: Context (the prior work) is one of the five Cs of a first pass [S1]. The abstract opens with the gap [S2; S16]. No field names the usual approach today.
- Check: none. Review the text in the Section 5 test.

**D4. Survey branch: the survey's own taxonomy and scope.** Proposed text: "survey: each top-level category of the survey's own taxonomy as a component, with the survey's own name; the principle that separates the categories as its role; at most 3 representative methods in its contains; the scope (how many methods, models, and settings) in contribution. When the survey benchmarks the methods, its comparison table goes into result.measures."
- Reason: the taxonomy or the comparison table is a survey's core [S37; S38]. Category names were the largest gap between model and expert trees [S38]. Model trees are too large [S39].
- Check: none new. D1's checks cover the measures.

**D5. Evaluation branch: the protocol and the reference levels.** Proposed text: "evaluation: the tested capability and how the task measures it in contribution; each compared condition or method as a component; the reference levels (random, human, prior best) as scores in result.measures; the condition that the ranking depends on (tuning budget, runs, task subset) in qualification."
- Reason: [S30; S31; S32; S33].
- Check: none new.

### 4.2 Evidence selection (`SELECTION_INSTRUCTION`), related

**E1. Ask for the main results table and the ablation table.** Proposed text: "Include the table that compares the paper's method with other methods, and the ablation table when the paper has one." D1 and D2 read these tables. For Attention, Table 2 was in the evidence anyway [L3], but `SELECTION_INSTRUCTION` does not ask for it [L7].
- Check: none. The run notes record the retrieved passage IDs.

### 4.3 Plan (`PLAN_PROMPT`, `validate_overview_plan`)

**P1. Choose items on one level, with a zoom on the novel part.** Proposed text: "Choose items on one level of the digest's containment tree, along its feeds, from input to result. Include every novel component that the ablation does not show is replaceable, or its nearest container below the root. One novel component can sit inside an item as a zoom, as Figure 2 of a paper zooms into Figure 1. Leave out standard parts that every model of this kind has, and parts that the ablation shows are replaceable; this rule wins over the novel rule. Aim for 3 to 5 items; 7 is the limit."
- Reason: one level of abstraction [S21; S22]; the authors' own Figure 1 and Figure 2 [S16]; novelty [S4; S5]; ablation [S20]; 3 to 5 chunks [S17].
- Check in `validate_overview_plan`, which then needs the Digest:
  - An item that names a component uses its exact `name`.
  - No item is an ancestor (through `contains`) of another item, except that a `novel` component can sit inside one item.
  - When the Digest has novel components with no `ablation` note, at least one of them, or its nearest container below the root, is an item. The root component (the one that no other component contains) is never an item; for Attention, "Transformer" alone does not pass.
- Expected effect for Attention: "Scaled dot-product attention head" comes in as the zoom; "Shifted target input", "Autoregressive predictions", and "Sinusoidal positional encoding" go out (*unconfirmed* until a rerun).

**P2. Give the through-line the shape of the first pass.** Proposed text: "through_line: one sentence with the usual approach and what blocks it, the paper's idea, and the result against its strongest comparator."
- Reason: [S1; S2; S16]. D3 supplies the usual approach.
- Check: none. Review it in the Section 5 test.

**P3. Give each headline number its comparator.** Change the shape to:

```json
{"value": 28.4, "metric": "BLEU", "dataset": "WMT 2014 English→German",
 "better": "higher", "comparator": {"method": "ConvS2S Ensemble", "value": 26.36}}
```

Proposed text: "Copy each headline number from result.measures with its strongest comparator."
- Reason: [S7; S20; S28; S29]. The diagram can then write "+2.0 BLEU over the best ensemble", which a zero-based bar shows only weakly [S35].
- Check: `value` and `comparator.value` match scores of one Digest measure. `comparator` is required when that measure has another score.

**P4. Build the chart from one Digest measure.** Proposed text: "chart: when one measure in result.measures has at least 3 scores, chart the paper's score and the strongest comparators, at most 6. Name the metric, the dataset, and the direction in shows."
- Reason: one task, one dataset, one metric, one scale (an inference from S34 and S35). With D1, the 3-number rule becomes true for Attention (8 EN-DE rows) and stays true for PRO (8 methods) [L3; L5].
- Check: every chart value matches a score in one Digest measure. Values are scores, not ranks [S35].
- Effect on the chart types: bar, line, and pie take one measure. Radar and quadrant need 2 or more measures over the same methods: radar takes 3 or more measures whose `scores` share their method names, and quadrant takes 2. Write that rule into P4, or drop radar and quadrant from `PLAN_CHARTS`. The owner decides; no spike chart used them.

**P5. Choose the plan's shape by `paper_type`.** Proposed text:
- architecture, method, theory: P1 to P4 as written.
- survey: "items are the survey's top-level categories, with the survey's own names, and the through-line names the principle that separates them. Give a headline finding in words when the digest has no measures."
- evaluation: "items are what the paper measures, the conditions it compares, and the finding. The chart is the core: the conditions on the paper's main measure, with a reference level when the digest has one."
- Reason: a survey has no mechanism path [S37; S38]; an evaluation's core is its protocol and its reference levels [S30]. The spike survey plan put text in the number slot [L6].
- Check: for survey and evaluation, allow 0 to 2 headline numbers plus a `headline_finding` string; for the other types keep 1 or 2 numbers.

**P6. Name what the first pass leaves out, in positive form.** Proposed text: "The Overview shows the paper type, the usual approach, the idea and its novel parts, and the result against a comparator. Hyperparameters, training details, secondary experiments, and related work go to the Blog and the Component hover."
- Reason: [S1; S2; S5; S19].
- Check: none.

**P7. Give the plan the qualification.** Add `qualification`: the Digest's qualification, shortened to at most 120 characters. The diagram writes it in the subtitle or the footer.
- Reason: a headline number without its scope can overstate the claim [S36]; the winner depends on the condition [S31; S32; S33].
- Check: a string of 1 to 120 characters. Lower priority than P1 to P5.

### 4.4 Diagram (`DIAGRAM_PROMPT`), one change

**G1. No arrows between survey categories.** Proposed text: "For a survey, show the categories as a structure: a mindmap, a block diagram, or subgraphs with no arrows between them. An arrow means one step feeds the next." Then change the `CONTEXT.md` Overview sentence "The reader follows it along its arrows" so that it covers a structure.
- Reason: [S21]; the spike drew the survey as a flowchart [L6].
- Check: none. The current design says the model chooses the diagram type.

## 5. How to test the changes

1. Make fresh Digests for the three spike Papers with D1 to D5, so that `why` is present [L1].
2. Run the plan and the diagram for each Paper, as the spike did, and record the items, the numbers, and the chart.
3. Check the items against the Paper by hand: for Attention, the attention operation is present, and the shifted input and the prediction output are absent [S16].
4. Measure comprehension as well as preference [S10; S11; S12]. Write 5 questions for each Paper from its abstract and its main results table: the paper type, the usual approach, the idea, the main result with its comparator, and the condition. A model answers them from the figure image alone, as PaperQuiz does [S27]. Compare the score of the current plan with the score of the changed plan.
5. Add Papers outside the three: at least one evaluation Paper with scores, and one theory Paper. The three spike Papers have no evaluation Paper with scores and no theory Paper.

## 6. What this research does not settle

- **The cap of 7.** The evidence supports 3 to 5 groups [S17]. Whether 7 items in 3 to 5 groups beats 5 items is a question for the Section 5 test.
- **Numbers in a first-pass figure.** Cell Press bans data [S5]; medicine requires numbers [S7]. For ML Papers, keeping them is an inference from leaderboard practice [S20; S28] (*unconfirmed*).
- **Eye-tracking.** I found no eye-tracking study of how researchers take a first pass over an ML paper. Scim cites Loizides and Buchanan (2009) on triage readers, who looked at visual content and headers; I did not read that source (*unconfirmed*).
- **Survey and evaluation figures.** No source tests a first-pass figure for these types. P5 and G1 are inferences from S21, S30, S37, and S38.
- **Missing table bodies.** The survey's comparison table reached the Digest without its body [L6]. That is a parser or retrieval issue, outside this note.

## 7. Leads that did not hold

- **CiteWorth** detects whether a sentence needs a citation. It does not extract contributions [S44].
- **AutoSurvey** gives no rule for choosing a survey's content for one figure [S45]. TaxoAlign reports that its trees are much larger than human trees [S39].
- **Visual abstracts improve comprehension.** The trials show more engagement [S8; S9], not more comprehension [S10; S11; S12].
- **Graphical-abstract rules for review articles** at Elsevier, Cell Press, or Wiley: not found [S5; S6; S46].
- **Paper2Poster, PosterAgent, and Paper2Figure** as evidence on content selection: they report compression and quiz scores, not which content to choose [S27]. Paper2Figure (CVPR 2026) was seen only in a search result.
- **Not read at the source:** Cleveland and McGill (1984), so the ranking of encodings rests on the Heer and Bostock replication [S34]; Few on zero baselines, so S35 is used in its place; the NeurIPS checklist after item 4 [S36]; Ruder (2018), cited by AxCell.

## 8. Sources

Read on 2026-10-28. "Full" means the whole text was read. "Excerpt" or "abstract" means less; give those rows less weight. S24 to S27, S33, S38, and S45 are preprints.

| Key | Source | Venue, year | Read | URL |
| --- | --- | --- | --- | --- |
| S1 | Keshav, How to Read a Paper | ACM SIGCOMM CCR, 2007 | full | http://ccr.sigcomm.org/online/files/p83-keshavA.pdf |
| S2 | Mensh and Kording, Ten simple rules for structuring papers | PLOS Comput Biol, 2017 | rules 1–5 | https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1005619 |
| S3 | Cachola et al., TLDR: Extreme Summarization of Scientific Documents | Findings of EMNLP, 2020 | sections 1–5.2 | https://ar5iv.labs.arxiv.org/html/2004.15011 |
| S4 | Fok et al., Scim: Intelligent Skimming Support for Scientific Papers | IUI, 2023 | excerpts | https://arxiv.org/html/2205.04561v3 |
| S5 | Cell Press Graphical Abstract Guidelines | publisher guide | full | https://www.cell.com/pb/assets/raw/shared/figureguidelines/GA_guide.pdf |
| S6 | Wiley, Guidelines for graphical abstracts | publisher guide | excerpt | https://onlinelibrary.wiley.com/pb-assets/Graphical%20Abstract%20PDF-1683501909.pdf |
| S7 | Ibrahim, A Primer on How to Create a Visual Abstract, v2 | practitioner guide, 2017 | full | https://med.stanford.edu/content/dam/sm/s-spire/documents/VisualAbstract_Primerv2.pdf |
| S8 | Chapman et al., RCT of plain English and visual abstracts on social media | Br J Surg, 2019 | abstract | https://pubmed.ncbi.nlm.nih.gov/31577372/ |
| S9 | Trueger et al., Visual Abstract Display and Social Media–Driven Website Traffic | JAMA, 2023 | excerpt | https://jamanetwork.com/journals/jama/fullarticle/2810361 |
| S10 | Bredbenner and Simon, Video abstracts and plain language summaries are more effective than graphical abstracts | PLOS ONE, 2019 | abstract | https://pmc.ncbi.nlm.nih.gov/articles/PMC6863540/ |
| S11 | Buljan et al., No difference in knowledge from infographic or plain language summary | J Clin Epidemiol, 2018 | abstract | https://pubmed.ncbi.nlm.nih.gov/29269021/ |
| S12 | Martin et al., Exploring the role of infographics for summarizing medical literature | Health Prof Educ, 2019 | excerpt | https://med.virginia.edu/faculty-affairs/wp-content/uploads/sites/458/2020/09/Martin2019_Article_ExploringtheroleofInfographics-1.pdf |
| S13 | Pferschy-Wenzig et al., Does a Graphical Abstract Bring More Visibility to Your Paper? | Molecules, 2016 | sections 1–3 | https://pmc.ncbi.nlm.nih.gov/articles/PMC5283664/ |
| S14 | Tenopir et al., Scholarly article seeking, reading, and use | Learned Publishing, 2015 | excerpt | https://voljournals.utk.edu/cgi/viewcontent.cgi?article=1050&context=utk_infosciepubs |
| S15 | Tenopir, Christian, and Kaufman, Seeking, Reading, and Use of Scholarly Articles | Publications, 2019 | excerpt | https://www.mdpi.com/2304-6775/7/1/18 |
| S16 | Vaswani et al., Attention Is All You Need | NeurIPS, 2017 | full; Table 3 checked again in the local copy | https://ar5iv.labs.arxiv.org/html/1706.03762 |
| S17 | Cowan, The Magical Mystery Four | Curr Dir Psychol Sci, 2010 | first half | https://pmc.ncbi.nlm.nih.gov/articles/PMC2864034/ |
| S18 | Jain et al., SciREX | ACL, 2020 | sections 1–2 | https://aclanthology.org/2020.acl-main.670.pdf |
| S19 | D'Souza, Auer, and Pedersen, SemEval-2021 Task 11: NLPContributionGraph | SemEval, 2021 | sections 1–2.2 | https://aclanthology.org/2021.semeval-1.44.pdf |
| S20 | Kardas et al., AxCell | EMNLP, 2020 | sections 1–3.1 | https://aclanthology.org/2020.emnlp-main.692.pdf |
| S21 | Heiser and Tversky, Arrows in Comprehending and Producing Mechanical Diagrams | Cognitive Science, 2006 | excerpt | https://www.tc.columbia.edu/faculty/bt2158/faculty-profile/files/sincomprehendingandproducingmechanicaldiagrams.PDF |
| S22 | Marshall, Freitas, and Jay, An evidence-based guidance framework for neural network system diagrams | PLOS ONE, 2025 | sections 1–2.3 | https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0318800 |
| S23 | Rougier, Droettboom, and Bourne, Ten Simple Rules for Better Figures | PLOS Comput Biol, 2014 | rules 1–4 | https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003833 |
| S24 | Zhu et al., PaperBanana | arXiv, 2026 | excerpt | https://arxiv.org/html/2601.23265v1 |
| S25 | Chen et al., Figures as Programs (FigTree) | arXiv, 2026 | excerpt | https://arxiv.org/html/2609.01006 |
| S26 | Pramanick et al., SciFig | arXiv, 2026 | excerpt | https://arxiv.org/html/2601.04390 |
| S27 | Pang et al., Paper2Poster | arXiv, 2025 | sections 1–3.3 | https://arxiv.org/html/2505.21497 |
| S28 | Hou et al., Identification of Tasks, Datasets, Evaluation Metrics, and Numeric Scores for Scientific Leaderboards Construction (TDMS) | ACL, 2019 | sections 1–2 | https://aclanthology.org/P19-1513.pdf |
| S29 | Wadden et al., Fact or Fiction: Verifying Scientific Claims (SciFact) | EMNLP, 2020 | section 1 | https://aclanthology.org/2020.emnlp-main.609.pdf |
| S30 | Reuel et al., BetterBench | NeurIPS D&B, 2024 | section 4, excerpt | https://arxiv.org/html/2411.12990 |
| S31 | Dodge et al., Show Your Work | EMNLP-IJCNLP, 2019 | sections 1–2 | https://aclanthology.org/D19-1224.pdf |
| S32 | Agarwal et al., Deep RL at the Edge of the Statistical Precipice | NeurIPS, 2021 | abstract, section 1 | https://ar5iv.labs.arxiv.org/html/2108.13264 |
| S33 | Dehghani et al., The Benchmark Lottery | arXiv, 2021 | abstract, section 1 | https://ar5iv.labs.arxiv.org/html/2107.07002 |
| S34 | Heer and Bostock, Crowdsourcing Graphical Perception | CHI, 2010 | to experiment 1A | https://hci.stanford.edu/publications/2010/crowd-perception/heer-chi2010.pdf |
| S35 | Correll, Bertini, and Franconeri, Truncating the Y-Axis: Threat or Menace? | CHI, 2020 | sections 1–2 | https://ar5iv.labs.arxiv.org/html/1907.02035 |
| S36 | NeurIPS Paper Checklist Guidelines | venue guide, current | items 1–4 | https://neurips.cc/public/guides/PaperChecklist |
| S37 | Oelen et al., Generate FAIR Literature Surveys with Scholarly Knowledge Graphs | JCDL, 2020 | excerpt | https://arxiv.org/pdf/2006.01747 |
| S38 | Zhang et al., Can Deep Research Agents Retrieve and Organize? (TaxoBench) | arXiv, 2026 | sections 1–2 | https://arxiv.org/html/2601.12369 |
| S39 | Lahiri, Hou, and Sanyal, TaxoAlign | EMNLP, 2025 | excerpt | https://aclanthology.org/2025.emnlp-main.1536.pdf |
| S40 | Hsu et al., CHIME | Findings of ACL, 2024 | abstract | https://aclanthology.org/2024.findings-acl.8.pdf |
| S41 | Zhu et al., Context-Aware Hierarchical Taxonomy Generation for Scientific Papers | EMNLP, 2025 | sections 1–2.1 | https://aclanthology.org/2025.emnlp-main.788.pdf |
| S42 | Int J Biochem Cell Biol (Elsevier), Structure requirements: Full-length Reviews | journal guide | excerpt | https://legacyfileshare.elsevier.com/promis_misc/BC_FormatRequirements.pdf |
| S43 | Thieme SynOpen, Author Guidelines (Graphical Reviews) | journal guide | excerpt | https://connect.thieme.com/en/journals/synopen/author-guidelines |
| S44 | Wright and Augenstein, CiteWorth | Findings of ACL, 2021 | abstract, section 1 | https://aclanthology.org/2021.findings-acl.157.pdf |
| S45 | Wang et al., AutoSurvey | arXiv, 2024 | abstract, section 1 | https://arxiv.org/html/2406.10252 |
| S46 | Elsevier, Graphical abstract | publisher page | full (short) | https://www.elsevier.com/researcher/author/tools-and-resources/graphical-abstract |

The research agent's full evidence file, with a strength note for each finding, is in the shared notes folder of this session group: `overview-plan-evidence.md`.
