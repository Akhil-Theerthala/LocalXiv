# Blog readability: what readers need, what the Blog does, and new Tone profiles

Date: 2026-10-29. Main at `db04d39`. Prompt revision `blog-checks-v2`.

**Purpose.** This report supports two decisions by the owner: (a) which changes to make to the Blog prompts and checks, and (b) how to change the three Tone profiles. It changes no code.

**Inputs.**

- Three web-research lanes on Exa: what readers find hard in research papers; the craft of readable technical explanation; controlled language, register, and Tone. Their full notes have more sources than this report. This report keeps the findings that change a prompt line.
- The current prompts in `papers/blog_prompts.py` and the three 2026-10-08 Blog designs in `docs/superpowers/specs/`. The September Blog pilots in `docs/verification/` come before the 2026-10-08 redesign, so this report does not use them.
- Measurements of the nine Blogs generated with `blog-checks-v2` on 2026-10-14 and 2026-10-15 (claude-opus-5-5). The files are the `candidate.json` of each run in the library.

**Rules.** "Strong" marks a meta-analysis or replicated experiments. "Moderate" marks one or two controlled studies or a large corpus study. "Weak" marks a small or indirect study. "Opinion" marks advice with no study. "Inference" marks a recommendation that no source states.

## 1. Summary

- **The Blog is longer than the reader asked for.** All nine Blogs are Medium (750–1,250 words). Their prose has 1,369 to 1,627 words, without citations. 55 of 63 sections are at 1.3 to 1.53 times their outline target. The 1.5 ceiling in the Section check has become the target.
- **The running example has no owner.** In each of the four Blogs checked, the example first appears as "the running example", and no sentence introduces it. The pipeline's own word "running example" is in the reader's text in eight of nine Blogs.
- **The Blog explains too many terms, and some are basic.** Each outline lists 20 to 24 terms for about 1,600 words. Sections define logistic regression and l2 regularization for a reader who knows machine learning. Studies show that the plainest text helps only readers with low familiarity. Readers with more familiarity skip more of it, most often the limits.
- **The prose is short and uniform.** Mean sentence length is 12.8 to 14.7 words. Only 0 to 5 sentences of about 105 are longer than 25 words. LLM prose has this uniform rhythm already, and a rule set that cuts sentences makes it worse. The "one thought" rule splits a cause from its effect.
- **Each sentence is one cited claim.** The Blogs have 57 to 75 citations, about two in each paragraph, and "the authors" opens 7 to 16 sentences. The Section check needs only one citation for each outline point, so the density comes from the prompt.
- **Tone is not a working setting.** No model can hold "about 85 of 100 sentences". The nine Blogs have no "you" and no analogy. Their compliance with the 25-word cap is 95 to 100%. Section 4 proposes a constant core and one set of register features for each Tone.
- **Test understanding, not ratings.** In two studies of reading aids, readers rated the text as easier, but their comprehension did not improve (Section 6).

## 2. What the nine Blogs show

The provenance of all nine Blogs records Semi-formal and Medium (`overview_language` and `overview_length`). Word counts use the Section check's own count (`uncited` and `_FIGURE_MARKER`). Sentence counts exclude headings, tables, and display equations.

| Measure | Range over nine Blogs | What the prompt asks |
| --- | --- | --- |
| Words, without citations | 1,369–1,627 | Medium: 750–1,250 |
| Outline targets, sum | 1,040–1,150 | "the sections together make the requested length" |
| Section words ÷ section target | 1.13–1.53; 55 of 63 sections at 1.3 or more | "about as many words as the section's words field gives"; ceiling 1.5 |
| Sentences | 97–119 | No rule |
| Mean sentence length | 12.8–14.7 words (SD 4.7–6.6) | at most 25 words in a description |
| Sentences over 25 words | 0–5 | Semi-formal: about 15 of 100 may run longer |
| Citations | 57–75 (1.6–2.2 in each paragraph) | each paper claim cites passages |
| "The authors" | 0–16 | No rule |
| "you", "we" | 0 in all nine | Semi-formal: no rule |
| Analogy | 1 in one Blog | Semi-formal: no rule |
| Terms in the outline | 20–24 | "each technical term the article uses" |
| "running example" in the prose | 8 of 9 Blogs | No rule |

Two examples from the 2026-10-15 Blog on deception probes (2502.03407):

- Section 2 says: "In the running example, the 'family emergency' tokens read deceptive". The late student who gives this excuse first appears in Section 4.
- Section 1 reports "a separation score of 0.96-0.999". Section 4 defines AUROC. Section 4 also defines four terms in one run: AUROC, false positive rate, recall at 1% FPR, and control set.

## 3. Changes to the Blog, ranked

Rank: gain to the Blog reader, weighted by the strength of the evidence and by how cheap the change is. Each item names the line it changes.

### 3.1 Make the length an upper limit, and make the ceiling tight

- **Evidence in the Blogs.** 55 of 63 sections land at 1.3 to 1.53 times their target, and three first sections are at 1.49 (Section 2). The 2026-10-08 checks design saw 1.3 to 3.2 before the ceiling. A section above 1.5 after the join is possible, because the join edits come after the Section check.
- **Sources.** Models follow "at most N" length rules much better than "equal to N". In LIFEBench, 19 of 26 models scored above 90 on "at most", and "equal to" targets failed often ([LIFEBench 2025](https://arxiv.org/abs/2505.16234), moderate). Faculty time for each reading fell from 48 to 31 minutes between 1977 and 2005 ([Tenopir et al. 2009](https://voljournals.utk.edu/cgi/viewcontent.cgi?article=1006&context=utk_infosciepubs), survey).
- **Change.** In SECTION_PROMPT step 7, write "Write at most N words", with N the section's `words`. Set `BLOG_SECTION_WORD_CEILING` to about 1.2. The 2026-10-08 design chose 1.5 because "a model counts words poorly". With "at most", the model aims under N, so 1.2 leaves room for counting errors. Inference: measure the correction count after the change. If it rises, try 1.3.

### 3.2 Give the running example an owner and a name

- **Evidence in the Blogs.** In 4 of 4 Blogs checked, the first mention is "In the running example" or "For the running example", with no introduction. In one, the example's content first appears two sections after that mention. The prose says "running example" in 8 of 9.
- **Sources.** Examples improve concept learning more than extra study of definitions, d = 0.74–1.67 ([Rawson et al. 2015](https://doi.org/10.1007/s10648-014-9273-3), moderate). Readers understand a sentence faster when its known part has a direct antecedent ([Haviland & Clark 1974](https://web.stanford.edu/~clark/1970s/Haviland,%20S.E.%20_%20Clark,%20H.H.%20_What's%20new_%20Acquiring%20new%20information%20as%20a%20process%20in%20comprehension_%201974.pdf), moderate). Alammar's Illustrated Transformer introduces one sentence and names each change of example (expert practice).
- **Change.** In OUTLINE_PROMPT step 2, the `example` gets two more fields: `name`, a short name the reader can hold ("the late student"), and `introduced_in`, the section ID that introduces it. This changes `BLOG_OUTLINE_SCHEMA` in `papers/explanation.py` and the outline validator. SECTION_PROMPT step 5 becomes: "If this section introduces the example, give its values. Otherwise call it by its name." Add "running example" to the words that the Section check rejects in a body.
- **Invented examples.** Two of nine outlines open their `example` with "Illustrative values, not from the paper" (2505.07309 and 2606.19868). OUTLINE_PROMPT step 2 asks for "the example in <overview_digest> when it has one, or an example the paper shows", so an invented example is outside the prompt's own rule. Its values then sit in the prose beside cited results. One of the two Blogs says "illustrative" in two sections. No check requires it. Add an `illustrative` flag to the example. When it is true, the introducing section must say once that the values are not from the paper, and the Section check can look for that sentence.

### 3.3 Explain fewer terms, and explain the paper's own terms first

- **Evidence in the Blogs.** The outlines list 20 to 24 terms. Sections define field basics (logistic regression, l2 regularization, chain-of-thought) for a reader who knows the field. One section defines four metrics in a row.
- **Sources.**
  - Plain summaries helped only readers with low familiarity with the topic. Readers with more familiarity skipped more of the plainest versions, most often the limitations ([August et al. 2024](https://doi.org/10.1145/3613904.3642289), three studies, N = 199, 191, 203, moderate to strong).
  - A support that helps novices can harm readers who know more ([Kalyuga et al. 2003](https://doi.org/10.1207/s15326985ep3801_4), strong).
  - A definition beside jargon does not bring back reading fluency ([Shulman et al. 2020](https://doi.org/10.1177/0261927x20902177), N = 650, moderate). More distinct concepts slow reading and lower recall ([Kintsch et al. 1975](https://cris.bgu.ac.il/en/publications/comprehension-and-recall-of-text-as-a-function-of-content-variabl-4/), moderate).
  - People learn more when they know the names of the key parts before the explanation, d = 0.78 ([Mayer 2021](https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf), strong; weaker for knowledgeable readers).
  - CS researchers' familiarity with terms varies widely, even in one subfield ([Guo et al. 2024](https://aclanthology.org/2024.naacl-long.255/), 10,571 ratings, moderate).
- **Change.**
  - In OUTLINE_PROMPT step 4, change "each technical term the article uses" to "each term that this paper names or that comes from outside the field, at most 12 for the article". No study gives a number, so 12 is an inference. It is about three for each section.
  - Change STE rule 12 to match (Section 4.2, core rule 10).
  - In SECTION_PROMPT, add: "Introduce at most two new terms in one paragraph."
  - In OUTLINE_PROMPT step 3, the second section names the method's key parts before the mechanism uses them.
  - The outline validator can check the term count.

### 3.4 Let sentences carry their links, and vary their length

- **Evidence in the Blogs.** Mean length 12.8 to 14.7 words, and 95 to 100% under 25 words, where Semi-formal permits 15% longer (Section 2).
- **Sources.**
  - LLM sentence lengths vary less than human ones ([Muñoz-Ortiz et al. 2024](https://doi.org/10.1007/s10462-024-10903-2), moderate). Expert annotators detect AI text by its formulaic structure, and they say human sentences "vary more in terms of length" ([Russell et al. 2025](https://arxiv.org/html/2501.15654), moderate).
  - Shorter sentences and easier words had no practical effect on comprehension for most readers ([Duffy & Kabance 1982](https://eric.ed.gov/?id=ED215330), moderate). Splitting sentences to fit a formula can make a text harder ([Davison & Kantor 1982](https://doi.org/10.2307/747483), moderate).
  - A revision that fills each inference gap conveys the author's meaning better ([Britton & Gülgöz 1991](https://doi.org/10.1037//0022-0663.83.3.329), moderate). Low-knowledge readers learn more from a coherent text ([McNamara et al. 1996](https://doi.org/10.1207/s1532690xci1401_1), moderate). The Blog reader knows little of the method.
  - Put known information first in a sentence and the new point last ([Gopen & Swan 1990](https://www.usenix.org/sites/default/files/gopen_and_swan_science_of_scientific_writing.pdf), expert practice).
- **Change.** STE rules 1, 2, and 11 change (Section 4.2, core rules 1, 2, and 4). Keep the 25-word cap, because a model can follow a cap.

### 3.5 Cite a run of sentences once, and let the method act

- **Evidence in the Blogs.** 57 to 75 citations, and up to 16 sentences that start with "the authors".
- **Sources.** Professors and graduate students skipped about 72% of citation words ([Eckstein et al.](https://scholarsarchive.byu.edu/cgi/viewcontent.cgi?article=7286&context=facpub), eye tracking, weak to moderate). In-text citations lowered quiz scores for less skilled readers ([Stiegler-Balfour et al. 2020](https://doi.org/10.1177/0098628320901384), moderate). `renderProse` in `app/static/render.js` already shows each citation as a small number, so the visual cost is low. The cost is in the prose: the prompt makes each sentence a separate cited claim.
- **Change.** In the SECTION_PROMPT "Evidence" paragraph, add: "When consecutive sentences use the same passages, cite them once, after the last of these sentences." The Section check needs one citation for each point, so it accepts this. In "Explaining", change "Write about the paper and its authors in the third person" to: "Make the method, the model, or the data the subject when it acts. Name the authors when they choose, claim, or test something."

### 3.6 Give each number its baseline and its meaning

- **Evidence in the Blogs.** Section 1 of the deception Blog gives "0.96-0.999" before the reader knows the measure.
- **Sources.** LLM summaries of science were 4.85 times as likely as human summaries to make results broader than the paper did, also when the prompt asked for accuracy ([Peters & Chin-Yee 2025](https://doi.org/10.1098/rsos.241776), 4,900 summaries, moderate to strong). People see relative changes as larger than absolute changes, with no gain in understanding ([Akl et al. 2011](https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.CD006776.pub2/full), Cochrane review of 35 studies, strong; health risk, so the transfer is partial).
- **Change.** In "Explaining", change "Report the baseline, the dataset, and the condition beside each number" to: "Report the measure, the baseline value and the new value, the dataset, and the condition beside each number. A number that comes before its measure is explained gets one plain sentence on what it means." Keep the closing section on limits, but keep each limit beside its claim too, because readers skip limits sections (August et al. 2024).

### 3.7 Smaller changes

| Change | Line | Source | Evidence |
| --- | --- | --- | --- |
| Mark an interpretation in natural words ("The paper does not test this, but…"). It replaces the fixed labels "One reading:" and "An analogy:". | SECTION "Explaining", last bullet | [Pinker 2014](https://stevenpinker.com/files/pinker/files/the_source_of_bad_writing_-_wsj_0.pdf) on metadiscourse | Opinion |
| The caption tells the takeaway of the figure in one sentence. | OUTLINE step 5, `caption` | Experts rated 53.88% of sampled arXiv captions as unhelpful ([Huang et al. 2023](http://arxiv.org/pdf/2302.12324v1)) | Moderate |
| Write an acronym in full at its first use. Give an acronym that the paper coins a plain name where one fits. | STE rules | 79% of acronyms occur fewer than 10 times in the literature ([Barnett & Doubleday 2020](https://elifesciences.org/articles/60080)) | Moderate |
| Put symbols in `terms`, with one symbol for each quantity in all sections. | OUTLINE step 4 | [ScholarPhi, Head et al. 2021](https://scholarphi.org/assets/pdf/scholarphi-chi-2021.pdf): one symbol had three meanings in one paper | Moderate |
| At each seam, the first sentence names what the previous section established. Today the join links only a seam that does not follow. | JOIN_TASK step 1 | Signals on only some topics lowered recall of the other topics ([Lorch & Lorch 1996](https://doi.org/10.1037/0022-0663.88.1.38)) | Moderate |
| Tell the reader in one sentence what the Blog leaves out, from NARRATIVE step 4. | Last section | 13 of 20 data scientists named missing details as a barrier ([interview study, 2023](https://arxiv.org/html/2301.03774v1)) | Weak |

### 3.8 What to keep

The evidence supports these parts of the Blog as they are:

- Question headings with the answer first ([Hartley & Trueman 1983](https://doi.org/10.1111/j.2044-8279.1983.tb02551.x); the Paper Plain key-question index was its users' favourite feature, [August et al. 2023](https://doi.org/10.1145/3589955)).
- The Overview before the Blog, as an advance organizer ([Luiten et al. 1980](https://doi.org/10.3102/00028312017002211), 135 studies).
- "Intuition, then operation, then equation" ([Fyfe et al. 2014](https://doi.org/10.1007/s10648-014-9249-3) on concreteness fading).
- The figure marker after the paragraph it supports ([Ginns 2006](https://doi.org/10.1016/j.learninstruc.2006.10.001), meta-analysis of 50 studies).
- Fidelity: each result keeps its condition (Peters & Chin-Yee 2025).
- The design-choice rule: "say whether the paper gives a reason, tests the alternative, or does neither". Qlarify readers asked "why" questions about abstracts ([Fok et al. 2024](https://doi.org/10.1145/3654777.3676397)).

## 4. Tone profiles

### 4.1 Why the share of sentences fails

1. **ASD-STE100 has no compliance share.** It is a set of writing rules plus a controlled dictionary, and a text follows it or does not ([ASD-STE100 Issue 9](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf)). The Blog's 12 rules are a house style based on STE. They drop the dictionary and add rule 12. STE permits technical nouns of the subject field with no definition.
2. **A model cannot hold a proportion.** Asked to output "1" 49% of the time, models output "0" nearly 100% of the time ([Yang & Zhang 2025](https://arxiv.org/abs/2511.14630), moderate). Models fail to hold a distribution over items in one response ([Zhao et al. 2026](https://aclanthology.org/2026.acl-long.1051/), 11 models, moderate). The Blogs agree: 95 to 100% of sentences are under 25 words, where Semi-formal permits 15% longer.
3. **Nothing measures the difference.** The design says, "The application does not score sentences".
4. **The axis is wrong.** Registers differ in a set of features that occur together: person, contractions, questions, hedges, and noun density. This is Biber's Dimension 1, "involved against informational" ([Biber & Conrad](https://www.blackwellpublishing.com/content/BPL_Images/content_store/WWW_Content/9780631205951/009.pdf), strong). Sentence length is only one feature, and the core rules already set it.
5. **The evidence on each feature:**
   - Conversational style improves retention (d = 0.30) and transfer (d = 0.54) in lessons shorter than 35 minutes ([Ginns, Martin & Marsh 2013](https://doi.org/10.1007/s10648-013-9228-0), meta-analysis, strong). A Blog takes about 7 to 10 minutes. So Casual is the right default, and Formal has a cost.
   - For readers with background knowledge, an analogy helped when the text did not connect to what they knew. It lowered performance when the text did ([Donnelly & McDaniel 2000](https://doi.org/10.3758/bf03214368), moderate). So an analogy is for the method's central idea only, and Semi-formal and Formal can do without one.
   - No study shows that rhetorical questions help comprehension. Questions that the reader answers do help ([Hamaker 1986](https://doi.org/10.2307/1170376)).
   - Contractions have no reader evidence. They only signal the register.

Tone sets the register only. The depth, the terms explained, and the evidence are the same at every Tone. The August et al. 2024 result shows why: a plainer text helps only readers with low familiarity, and the Blog reader knows the field.

### 4.2 Proposed core, replacing `STE_RULES`

Every Tone keeps these rules. Twelve rules stay, because compliance falls as rules stack up ([IFScale 2025](https://arxiv.org/html/2507.11538), moderate). `[check]` marks a rule that the application can check with a counter or a word list. The others stay with the model.

```text
Write the prose in a plain style based on ASD-STE100 Simplified Technical English (STE).
The prose keeps these rules:
1. One main statement in the sentence. Keep "because", "so", "but", and "if" inside the sentence
   when they join a cause, a result, a contrast, or a condition to it. A condition comes before
   the statement it controls: "If a sentence is long, attention costs more."
2. At most 25 words. Mix short and long sentences in each paragraph. [check: the cap]
3. At most six sentences in a paragraph, and the first sentence tells its topic. [check: the count]
4. What the reader already knows comes first in the sentence, and the new point comes last.
5. Active voice that names who acts: "the encoder maps each token to a vector".
6. The present, the simple past, or the future tense.
7. One word for one meaning: after you name a thing, call it by that name every time.
8. Noun clusters of three words or fewer, and a verb in place of an "-ing" form or a noun made
   from a verb: "the model computes the score" in place of "the computation of the score".
9. The plain word: "use", "help", "start", "show", "about". Keep to the words of the field and
   of the paper in place of "delve", "pivotal", "intricate", "showcase", "underscore",
   "leverage", "landscape", and "seamless". [check: the list]
10. A plain explanation at the first use of each term that this paper names or that comes from
    outside the field. Use the field's basic terms as the reader knows them. Write an acronym in
    full at its first use.
11. Each result with its measure, the baseline value and the new value, and its dataset or
    setting. Each claim as wide as the paper's claim, and a hedge where the paper hedges.
12. A period or a comma between clauses, and a hyphen between joined words: "encoder-decoder".
    A number range takes a hyphen: "3-5". [check: the existing dash check]
Equations, citations, table cells, headings, and quoted labels are outside the word count.
```

Notes on the core:

- Rule 2 drops the 20-word limit. STE gives 20 words to procedures (Rule 5.1) and 25 to descriptive text (Rule 6.3). A Blog is descriptive text.
- Rule 2 asks for a mix of short and long sentences but sets no number. The research lane proposed "one sentence at least 10 words longer than the shortest". That is opinion, so calibrate it on human explainers before the application checks it.
- Rules 1 and 4 come from Section 3.4, rule 10 from Section 3.3, and rule 11 from Section 3.6.
- Rule 8 keeps the "-ing" rule and adds nouns made from verbs. Instruction-tuned models use present participial clauses at 2 to 5 times the human rate, and nominalizations at 1.5 to 2 times ([Reinhart et al. 2025](https://www.pnas.org/doi/10.1073/pnas.2422455122), moderate to strong).
- Rule 9's word list is a hard guardrail, so it is written as a negative. The list comes from [Kobak et al. 2025](https://www.science.org/doi/10.1126/sciadv.adt3813) (15 million abstracts, strong) and Russell et al. 2025. "Underscore", "leverage", "landscape", and "seamless" are opinion.
- The STE rule on articles ("the" and "a") goes. The nine Blogs give no sign that the model drops articles, so the rule is probably a no-op. Check this on one run before you delete it. The old rule 11, a condition before the statement it controls, moves into rule 1.

### 4.3 Proposed Tones, replacing `LANGUAGES`

Each Tone sets the same five features. Section requests run in parallel, so the outline gives the one Casual analogy to one section. The outline names the analogy, the idea it explains, and where it stops being true.

```text
Tone: Casual.
- Speak to the reader as "you". Use "we" for you and the reader as you follow the example.
  Contractions are fine.
- One question in a section at most, and the next sentence answers it.
- If the outline gives this section the analogy, use it for the method's central idea. Say that it
  is an analogy, and say in the next sentence where it stops being true.
- After a key number, say in plain words what it means for the reader.

Tone: Semi-formal.
- Use "we" for you and the reader as you follow the example, and the third person elsewhere.
  Write full forms in place of contractions.
- State each point as a statement. The heading carries the question.
- Give a concrete example with the paper's values in place of an analogy.
- A sentence may add one condition or one consequence after its main statement.

Tone: Formal.
- Write in the third person, and write full forms in place of contractions.
- State each point as a statement, and use the paper's own examples.
- Give the limit of each result in its own sentence after the result, in the paper's words where
  you can.
- Report the variance or the number of runs where the paper gives them.
```

Application checks for each Tone, with an exact message as today. The Section check looks only at the prose: it skips quotes, math, code, and citations, which hold the paper's words. The outline validator checks the analogy.

| Check | Casual | Semi-formal | Formal |
| --- | --- | --- | --- |
| "you" or "your" in the prose | permitted | none | none |
| Contractions | permitted | none | none |
| "?" in the prose | at most 1 for each section | none | none |
| "we", "our" | permitted | permitted | none |
| Analogy in the outline | one section, or none | none | none |

Two checks from the first draft of this report are not in the code. A minimum count of "you" for Casual is a check on the whole article, so it would need a correction after the join. A check that the analogy stays in its section needs a marker that the prose does not have.

### 4.4 Costs and order

- Each check that fails costs one correction from the section's existing budget. Five cheap counts add no provider call.
- Change `PROMPT_REVISION` from `blog-checks-v2`, because the prompts change.
- Update the CONTEXT.md entry for **Tone** and the Tone section of the 2026-10-08 readability design. Both describe the share of sentences.
- Order: first Sections 3.1 and 3.2, because they are cheap and the Blogs show the failure. Then 3.3 to 3.6 and the Tone profiles, as one prompt revision. Then the smaller changes.

## 5. Not verified

- I found no study of STE in descriptive or explanatory text read by expert or native readers. The STE studies used maintenance procedures ([Shubert et al. 1995](https://doi.org/10.2190/wg69-d74b-4dll-2wbk)).
- The STE rule against contractions (Rule 4.2) comes from a secondary source. Check it against the Issue 9 PDF.
- No study gives a number of new terms for each paragraph. The limits of 12 for the article and 2 for each paragraph are inferences from Kintsch 1975 and Cowan 2001.
- The new ceiling of 1.2 is an inference. Measure the correction count.
- No study shows that LLMs over-hedge. The evidence shows the reverse risk: claims that are too broad.

## 6. How to test the change

Most reading-aid studies measure only how easy readers say the text felt. Two studies measured comprehension too, and the two measures did not agree:

- With Paper Plain, readers rated reading as less difficult. Their comprehension did not change ([August et al. 2023](https://doi.org/10.1145/3589955), N = 24).
- Readers rated LLM plain-language summaries the same as human ones. The human summaries gave better comprehension and recall ([Guo et al. 2025](https://arxiv.org/abs/2505.10409), N = 150).

Inference: test a new prompt revision in two steps.

1. Generate three papers at each Tone and Medium length. For each Blog, measure the words against the target, the mean and SD of sentence length, the terms, the citations, and the counts in Section 4.3. If two Tones give the same numbers, the profiles have no effect.
2. Write five questions from each paper's Digest: the contribution, the mechanism, the main number with its baseline, the condition, and one limit. Ask a reader who knows the field to answer them after the old Blog and after the new one.

## 7. Status on 2026-10-29

The changes are in `papers/blog_prompts.py`, `papers/explanation.py`, and `papers/blog_workflow.py`, at prompt revision `blog-tone-v2`. One live Blog ran on `blog-tone-v1` (results below), and `blog-tone-v2` changes the length rule after it.

In the code:

- Section 3.1: the section prompt states "at most N words" with the number, the outline aims at the middle of the length range, and `BLOG_SECTION_WORD_CEILING` is 1.3. The 1.2 of `blog-tone-v1` cost too many corrections (below).
- Section 3.2: the outline `example` has `name`, `text`, `introduced_in`, and `illustrative`. The Section check rejects "running example", and it rejects an introducing section that does not say that illustrative values are not from the paper.
- Section 3.3: at most 12 terms (`BLOG_MAX_TERMS`), with symbols, and at most two new terms in a paragraph. The second section names the key parts.
- Sections 3.4 to 3.6, and every row of Section 3.7: the prompt lines.
- Section 4: the new `STE_RULES` and `LANGUAGES`, the outline `analogy`, and the checks in Section 4.3. The Section check also rejects the marker words of core rule 9.

Not in the code:

- Checks on the 25-word cap, on six sentences in a paragraph, and on the mix of sentence lengths. A sentence splitter has to handle abbreviations, decimals, and math. The nine Blogs already keep the cap in 95 to 100% of sentences. The mix has no calibrated number.
- The two checks named at the end of Section 4.3.
- The comprehension test in Section 6.

### Live run on `blog-tone-v1`, 2026-10-29

One Casual, Medium Blog of 2502.03407 (deception probes), claude-opus-5-5, medium reasoning, run with `tools/overview_run.py --kind blog`. The baseline is the Semi-formal Blog of the same paper on 2026-10-15. The Tones differ, so the register rows compare Tones, not prompt revisions.

| Measure | Baseline (`blog-checks-v2`) | `blog-tone-v1` |
| --- | --- | --- |
| Words, without citations | 1,421 (targets 1,050) | 1,329 (targets 1,150) |
| Section words ÷ target | 1.25–1.49 | 1.06–1.22 |
| Section requests, rejected | 13, 6 rejected | 18, 12 rejected |
| Rejections on the word count | 4 | 8 |
| Terms in the outline | 20 | 12 |
| "running example" in the prose | 2 | 0 (the check rejected it twice) |
| Example introduced before use | no | yes, in section 3, by its name |
| "you", "we", contractions | 0, 0, 0 | 3, 2, 6 |
| Analogy | none | one, in section 2, with where it stops being true |
| Mean sentence length (SD) | 14.1 (5.0) | 13.7 (5.3) |
| Citations | 68 | 64 |
| "the authors" | 16 | 16 |
| Requests, seconds | not measured | 28, 224 |

What worked: the term limit, the example owner and name, the seam links ("With the probe built, we need realistic test data"), the Casual register, and a plain meaning after a key number ("you'd flag about 1 in 100 normal chats and catch nearly every lie").

What did not work:

- The length rule cost too much. First drafts ran 1.0 to 1.7 times their target under "at most", as they did under "about". One section needed five of its six requests, one short of a failed run. `blog-tone-v2` responds with the three changes in the Section 3.1 line above.
- The subject rule and the cite-once rule had no measurable effect: "the authors" and the citation count stayed the same.
- The rule on mixed sentence length had no effect: the SD stayed near 5.
- Four section requests returned empty JSON, as one did in the baseline. That is the provider, not the prompt.

### Live run on `blog-tone-v2`, 2026-10-29

The same paper, model, reasoning, and Tone as the `blog-tone-v1` run.

| Measure | `blog-tone-v1` | `blog-tone-v2` |
| --- | --- | --- |
| Words, without citations | 1,329 (targets 1,150) | 1,300 (targets 1,150) |
| Section words ÷ target | 1.06–1.22 | 0.92–1.22 |
| Section requests, rejected | 18, 12 rejected | 7, 1 rejected (empty JSON) |
| Rejections on the word count | 8 | 0 |
| Requests, tokens, seconds | 28, 481,891, 224 | 22, 232,927, 248 |
| Citations | 64 | 49 |
| "the authors" | 16 | 17 |
| "you", "we", contractions | 3, 2, 6 | 2, 1, 5 |
| Example | introduced in section 3 | introduced in section 1, by its name |
| Figures accepted | 3 of 3 | 1 of 3; 2 omitted after 3 corrections each |

What changed:

- The length rule now costs no corrections, and the sections stay within 1.22 times their target.
- The run used half the tokens of `blog-tone-v1`.
- The outline did not aim at the middle of the range: its targets still sum to 1,150, and the article is 1,300 words against a Medium range of 750 to 1,250.

What stays open:

- Two figures were omitted. Their rejections are Diagram checks on width, height, small text, and literal asterisks. The prose changes did not cause them: the Mermaid Blog figures were merged on 2026-10-28, and the 2026-10-15 baseline drew its figures as Scenes. The figure fix is in the next section.
- "The authors" is still in 17 sentences.
- One run on one paper is not a measurement. The test in Section 6 needs three papers at each Tone.
