# Blog readability design (2026-10-08)

This design changes three things in the Blog: how many figures it draws, how the review ends, and how the reader's Tone setting shapes the prose. It also rewrites every Blog and Overview prompt with the rules of the `writing-for-agents` skill.

## What failed

The user generated Blogs with sonnet-5.5 and gpt-6-luna on 2026-10-07 and 2026-10-08.

- **One or two figures.** The author may plan zero to three figure briefs. In the last 13 completed or failed runs the author planned one, two, or three, and the saved Blogs carry one or two.
- **A review that never ends.** On AI Control (2312.06942) the reviewer reported 10, 12, 14, 15, 14, 17, 14, 4, and 2 findings across nine verdicts. Most were scope nuances and unexplained terms. Two prose corrections are allowed, then the run fails with "Draft retained", and the reader gets no Blog.
- **A Tone setting with no rules.** Casual, Semi-formal, and Formal were one sentence each, such as "Use polished, accessible explanatory prose." A model cannot follow or check a sentence like that.

## Figures follow the Blog length

| Length | Figures |
| --- | --- |
| Short | 1 to 2 |
| Medium | 2 to 4 |
| Large | 3 to 6 |

The author plans one figure for each section where a picture explains an operation, a relationship, a comparison, or a change. The draft validator rejects a count outside the range for the length. Each figure stays one Scene panel.

## The review fixes errors and records advice

Each review category has a severity:

- **Error:** `unsupported_claim`, `incorrect_mechanism`, `misleading_connection`. The reader would believe something false.
- **Advice:** `scope`, `missing_explanation`, `missing_transition`, `unexplained_term`, `readability`. The article is true but could be clearer.

The first correction answers every finding. Later corrections answer errors only. The Blog ships when no error is open, and the provenance records the open advice. If errors are still open after two prose corrections, one last request deletes the sentences those errors name, and the Blog ships. A run fails in review only when the provider fails.

## Tone is a level of Simplified Technical English

The Tone setting names how strictly the prose follows ASD-STE100 Simplified Technical English (STE). Every level uses the same rule list. The level sets how many sentences must follow every rule:

| Tone | Sentences that follow every rule | Allowed in the other sentences |
| --- | --- | --- |
| Casual | about 7 in 10 | a longer sentence that carries an intuition or an example, "you" and "we", contractions, a labelled analogy |
| Semi-formal | about 85 in 100 | a longer sentence that carries one condition or consequence |
| Formal | all | nothing: no contractions, analogies, or rhetorical questions |

The rule list: one thought per sentence; at most 20 words in an instruction and 25 in a description; at most six sentences in a paragraph; active voice that names who acts; present, simple past, and future tenses only; "the" and "a" kept; one word for one meaning, used the same way every time; no noun cluster of more than three words; the plain word ("use", not "utilize"); few "-ing" forms; a condition before the statement it controls; each technical term defined at its first use.

The model reads the level and the rules. The application does not score sentences.

## Easy to follow

The Blog keeps the Overview's spine: why the work was needed, how it works, and what it achieved, so a reader who saw the Overview recognises the order. Each section heading is the question the section answers. Each section starts with its answer, then explains it. The article carries one running example from the Overview's digest through the mechanism. A figure comes right after the paragraph it supports.

## Prompts

Every Blog and Overview prompt is rewritten with the `writing-for-agents` rules: the target behaviour stated positively, a numbered step list where the model works in order, a completion criterion on each step, one source of truth for each rule, and no sentence the model already obeys by default.
