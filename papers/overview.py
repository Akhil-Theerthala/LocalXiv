"""Shared overview preferences, writing instructions, and the JSON reader for model answers."""
import json
import re

# The Tone setting is a level of ASD-STE100 Simplified Technical English (STE): the same rules,
# kept in a different share of sentences. Before 2026-10-08 each level was one sentence such as
# "Use polished, accessible explanatory prose", which no model can follow or check.
STE_RULES = """Write the prose in ASD-STE100 Simplified Technical English (STE).
A sentence follows STE when it keeps every rule:
1. One thought in the sentence.
2. At most 20 words in an instruction and 25 words in a description.
3. At most six sentences in its paragraph.
4. Active voice that names who acts: "the encoder maps each token to a vector".
5. The present, the simple past, or the future tense.
6. "The" and "a" kept where the noun needs them.
7. One word for one meaning: after you name a thing, call it by that name every time.
8. Noun clusters of three words or fewer: "the cost of training the model".
9. The plain word: "use", "help", "start", "show", "about".
10. A verb in place of an "-ing" form where one fits.
11. A condition before the statement it controls: "If a sentence is long, attention costs more."
12. Each technical term explained in plain words at its first use.
Equations, citations, table cells, headings, and quoted labels are outside the count."""

LANGUAGES = {
    'casual': STE_RULES + '\nTone: Casual. About 7 of every 10 sentences follow every STE rule. The other '
              'sentences may run longer to carry an intuition or an example, speak to the reader as "you", use '
              'contractions, and use one analogy that you name as an analogy.',
    'semi-formal': STE_RULES + '\nTone: Semi-formal. About 85 of every 100 sentences follow every STE rule. The '
                   'other sentences may run longer to carry one condition or one consequence. Write full forms '
                   'in place of contractions.',
    'formal': STE_RULES + '\nTone: Formal. Every sentence follows every STE rule. Write full forms in place of '
              'contractions, and state facts in place of analogies and rhetorical questions.',
}
LENGTHS = {'short': 'about 750 words', 'medium': '750–1,250 words',
           'large': '1,500–2,000 words, longer only when needed to explain the paper'}


def overview_preferences(settings):
    language = settings.get('overview_language', 'casual')
    length = settings.get('overview_length', 'medium')
    if not isinstance(language, str) or language not in LANGUAGES:
        raise ValueError('Choose casual, semi-formal, or formal blog language.')
    if not isinstance(length, str) or length not in LENGTHS:
        raise ValueError('Choose short, medium, or large blog length.')
    return language, length


def parse_json(text):
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        # The correction names the place: told only "invalid", deepseek-flash sent the same digest
        # three times, each closing the object early after an "example" written like its neighbours.
        raise ValueError('The model returned invalid JSON (' + error.msg + ' at character ' + str(error.pos)
                         + ', after ' + json.dumps(text[max(0, error.pos - 80):error.pos], ensure_ascii=False)
                         + '). Retry generation.') from None
    if not isinstance(value, dict):
        raise ValueError('The model plan must be a JSON object.')
    return value
