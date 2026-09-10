"""Shared overview preferences, writing instructions, and citation helpers."""
import json
import re

PASSAGE_CITATIONS = r'\[\s*p\d+(?:\s*[,;]\s*p\d+)*\s*\]'
LANGUAGES = {
    'casual': 'Use approachable, conversational language, with natural contractions and concrete explanations. Keep the technical substance precise; avoid forced jokes or slang.',
    'semi-formal': 'Use polished, accessible explanatory prose. Keep a professional tone without academic stiffness.',
    'formal': 'Use precise, restrained professional language. Avoid conversational asides and contractions, but still explain unfamiliar concepts clearly.',
}
LENGTHS = {'short': 'about 750 words', 'medium': '750–1,250 words',
           'large': '1,500–2,000 words, longer only when needed to explain the paper'}
NARRATIVE_TIPS = """Build understanding for a technically curious reader who has not read the paper. Organize the explanation around the paper's central question. Begin with a single paragraph of one to three sentences stating the concrete pain point and why it matters. Then explain what was done previously, what those approaches enabled, and the specific gap that remained, using only the paper's account of prior work. Establish essential background before introducing this paper's method.

Explain what this paper does in detail: the mechanism, the role of each important component, how the parts fit together, and how they address the opening pain point. Anticipate questions a reader may not think to ask, especially why the authors chose X rather than a plausible Y. Distinguish reasons explicitly stated by the authors, comparisons or ablations actually tested, and interpretations grounded in the evidence. Never invent author intent, a missing experiment, or proof that an untested alternative is worse. When the paper does not explain a choice or evaluate an alternative, say so plainly. Explain relevant tradeoffs without turning the article into a list of speculative objections.

Use the shared original-figure readings to explain the paper's framework and architecture: component roles, inputs and outputs, parallel branches, repeated blocks and skip connections. State how each important original figure develops the central idea and which relationships a simplification must preserve. Then teach readers to interpret the results: axes, symbols, panels, baselines, measurements and qualifications supported by the evidence. Distinguish original figures, author explanations and generated schematics. Do not infer unseen details from captions. Choose what needs explaining before choosing a rendering template. Explain each generated figure and its simplifications alongside it.

Finish with the core insights, what the work achieved, the conditions under which the evidence supports that conclusion, and what remains unresolved. Preserve the details needed to understand the paper; avoid hype and repetitive summaries. Use a worked example only when supported by the paper, and identify any interpretation as interpretation. Do not invent background facts or anecdotes."""


def overview_preferences(settings):
    language = settings.get('overview_language', 'casual')
    length = settings.get('overview_length', 'medium')
    if not isinstance(language, str) or language not in LANGUAGES:
        raise ValueError('Choose casual, semi-formal, or formal blog language.')
    if not isinstance(length, str) or length not in LENGTHS:
        raise ValueError('Choose short, medium, or large blog length.')
    return language, length


WRITING_TIPS = '''Write for a technically curious reader who has not read the paper. Give each section a concrete, descriptive heading and one job. Start paragraphs with their point, then explain why. Define a term before using its abbreviation. Explain intuition before equations. Keep paragraphs short, usually 2–4 sentences. Report the baseline, dataset, and qualification beside each numerical result. Distinguish uncertainty, calibration, accuracy, and refusal when relevant. Use examples only when supported by the paper, and label interpretation. End with what the evidence establishes and leaves open. Avoid hype, stock transitions, repeated summaries, and a wall of bullets.

Use Markdown throughout. Typeset inline mathematics with $...$ and display equations with $$ on separate lines; never wrap equations in code fences. Explain symbols in nearby prose. Where the paper supports a comparison across methods, assumptions, or results, include a compact Markdown table without waiting for the reader to request one. Use a header row, a pipe-separated --- delimiter row, and each data row on its own line, with the same column count. Keep math delimiters inside cells and escape literal cell pipes. Never invent results to fill a table. Preserve equations and table structure during revision.'''


def clean_citations(text):
    return re.sub(r'[ \t]*' + PASSAGE_CITATIONS, '', text)


def parse_json(text):
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
    try:
        value = json.loads(text)
    except ValueError:
        raise ValueError('The model returned an invalid article or figure plan. Retry generation.') from None
    if not isinstance(value, dict):
        raise ValueError('The model plan must be a JSON object.')
    return value
