"""A Chat question: the request that carries the Paper, and the Turn that holds the answer and its citations."""
import math
import time
from urllib.parse import urlsplit

from papers.ai import _rejects_reasoning
from papers.coordinator import evidence_text
from papers.errors import ProviderError
from papers.passages import chat_citations
from papers.reading import evidence_document

INSTRUCTIONS = '''You answer questions about one Paper.
The Paper is in a <paper> block. If the Paper is too long, you get an <excerpt> block with some of its passages.
The <excerpt> block can be missing.
Each passage starts with its ID in square brackets and then its section.
Answer only from the Paper. Do not use other knowledge.
Cite each passage that you use. Write each ID in its own square brackets, as in [p00017] [p00018].
Never write a range, such as [p00017-p00019].
If the Paper does not say the answer, write "The Paper does not say".
A <selection> block is the text that the reader selected. Answer about that text.'''

TOO_LARGE = "This Paper is larger than the Chat model's context size. Select a passage and ask about it."
SELECTION_TOO_LARGE = "The selection does not fit the Chat model's context size. Select less text and ask about it."

OUTPUT_TOKENS = 8000
# The least room that an answer gets when the selection path shrinks the prompt to fit a small Context size.
MIN_OUTPUT_TOKENS = 1024
EXCERPT = '<excerpt>\n{}\n</excerpt>\n\n'
# The excerpt of a 4k model: P3 ran 2,000 tokens, and one answer went over 4,096 tokens in all.
# shortcut: the budget is fixed, so a model with a 16k to 32k context leaves room unused; scale it with the
# Context size when a reader with such a model asks.
EXCERPT_TOKENS = 2000


def _tokens(text, host):
    # shortcut: 2.5 characters a token on api.anthropic.com and 3.5 elsewhere (P3 measured 2.2 to 2.8 and 3.5
    # to 4.6), so a Paper near the Context size can still fail at the provider; ask the provider to count when one does.
    return math.ceil(len(text) / (2.5 if host == 'api.anthropic.com' else 3.5))


def _excerpt(passages, anchor, room, host):
    """An <excerpt> block with the passage ``anchor``, then the passages of its section, then the passages beside
    them, nearest first, while the block fits ``room`` tokens and ``EXCERPT_TOKENS``. The block is empty when
    ``anchor`` is not in ``passages`` or alone does not fit: the selection still holds the quoted text."""
    where = next((index for index, passage in enumerate(passages) if passage['id'] == anchor), None)
    if where is None:
        return ''
    section = passages[where]['section']
    room = min(room, EXCERPT_TOKENS) - _tokens(EXCERPT.format(''), host)
    chosen = []
    for index in sorted(range(len(passages)),
                        key=lambda index: (passages[index]['section'] != section, abs(index - where), index)):
        room -= _tokens(evidence_text({'passages': [passages[index]]}), host)
        if room < 0:
            break
        chosen.append(index)
    if not chosen:
        return ''
    return EXCERPT.format(evidence_text({'passages': [passages[index] for index in sorted(chosen)]}))


def request(paper, thread, question, notes, context_tokens, host):
    """The system blocks and the messages of one question on a Question card.

    ``thread['turns']`` holds the earlier turns. The Paper is the last system block, so Anthropic can cache it.
    The notes follow it in a user message, and the selection and the question come last. A Paper too large for
    ``context_tokens`` gives an excerpt around the selected passage instead, in the last message, so that no cache
    breakpoint lands on text that changes with each question. A question about the whole Paper then raises
    ``ValueError``.
    """
    passages = evidence_document(paper)['passages']
    quote = thread.get('quote')
    final = (f'<selection passage="{thread.get("passage")}">\n{quote}\n</selection>\n\n' if quote else '') + question
    notes_block = '<notes>\n' + '\n'.join(notes) + '\n</notes>' if notes else ''
    paper_block = '<paper>\n' + evidence_text({'passages': passages}) + '\n</paper>'
    system = [INSTRUCTIONS, paper_block]
    if _tokens(''.join(system) + notes_block + final, host) + OUTPUT_TOKENS > context_tokens:
        # shortcut: no Evidence selection when a whole-Paper question does not fit; upgrade when a reader with a
        # small model asks.
        if not quote:
            raise ValueError(TOO_LARGE)
        system = [INSTRUCTIONS]
        excerpt_room = context_tokens - MIN_OUTPUT_TOKENS - _tokens(INSTRUCTIONS + notes_block + final, host)
        if excerpt_room <= 0:
            raise ValueError(SELECTION_TOO_LARGE)
        final = _excerpt(passages, thread.get('passage'), excerpt_room, host) + final
    # A turn with no answer text, such as one that went offline, is not sent: the roles must alternate.
    room = context_tokens - OUTPUT_TOKENS - _tokens(''.join(system) + notes_block + final, host)
    history = []
    for turn in reversed([turn for turn in thread['turns'] if turn['answer']['text']]):
        room -= _tokens(turn['question'] + turn['answer']['text'], host)
        if room < 0:
            break
        history = [{'role': 'user', 'content': turn['question']},
                   {'role': 'assistant', 'content': turn['answer']['text']}, *history]
    return system, [*([{'role': 'user', 'content': notes_block}] if notes else []), *history,
                    {'role': 'user', 'content': final}]


def answer(provider, paper, thread, question, settings, on_text, stop):
    """Ask the Chat model one question and return its Turn.

    ``on_text`` gets each new part of the answer. A ``ValueError`` from ``request`` raises before the provider
    gets a request. A provider error does not raise: the Turn keeps the text that arrived and the error message.
    """
    started = time.time()
    host = urlsplit(settings['chat_endpoint']).hostname
    passages = evidence_document(paper)['passages']
    # Release 2 sends the reader's Highlights and Notes in place of the empty list.
    system, messages = request(paper, thread, question, [], settings['chat_context'], host)
    # The prompt and the answer limit together fit the Context size, as servers such as vLLM and TGI check.
    # No clamp here: request leaves at least MIN_OUTPUT_TOKENS, and a clamp would let the sum go over.
    prompt = _tokens(''.join(system) + ''.join(message['content'] for message in messages), host)
    max_tokens = min(OUTPUT_TOKENS, settings['chat_context'] - prompt)
    parts, usage, stopped, error = [], dict(cached=0, new=0, output=0), False, None

    def send(text):
        parts.append(text)
        on_text(text)

    for reasoning in (settings['chat_reasoning'], None):
        try:
            result = provider.stream(system, messages, send, reasoning=reasoning, max_tokens=max_tokens, stop=stop)
        except ProviderError as failure:
            # The same rule as Provider.complete(): a model that rejects the reasoning field answers without it.
            if reasoning is not None and not parts and _rejects_reasoning(failure):
                continue
            error = str(failure)
        else:
            usage, stopped = result['usage'], result['stopped']
        break
    text = ''.join(parts)
    cites, unknown = chat_citations(passages, text)
    return {'question': question,
            'answer': {'text': text, 'cites': cites, 'unknown': unknown, 'model': settings['chat_model'],
                       'host': host, 'created_at': started, 'tokens': usage, 'stopped': stopped, 'error': error}}
