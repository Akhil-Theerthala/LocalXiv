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
The Paper is in a <paper> block, or some of its passages are in an <excerpt> block.
The <excerpt> block can be missing.
Each passage starts with its ID in square brackets and then its section.
Answer only from the Paper. Do not use other knowledge.
Cite each passage that you use. Write each ID in its own square brackets, as in [p00017] [p00018].
Never write a range, such as [p00017-p00019].
If the Paper does not say the answer, write "The Paper does not say".
A <selection> block is the text that the reader selected. Answer about that text.'''

TOO_LARGE = "This Paper is larger than the Chat model's context size. Select a passage and ask about it."
SELECTION_TOO_LARGE = "The selection does not fit the Chat model's context size. Select less text and ask about it."
TRUNCATED = ('The answer stopped at the output limit of the Chat model. Ask a narrower question, or set a lower '
             'Reasoning effort in Settings › Chat.')

# The most tokens that an answer takes. A Context size under 32,000 tokens reserves a quarter of it instead, so that
# follow-up turns and a short Paper can still fit.
OUTPUT_TOKENS = 8000
EXCERPT = '<excerpt>\n{}\n</excerpt>\n\n'
# The excerpt of a 4k model: P3 ran 2,000 tokens, and one answer went over 4,096 tokens in all.
# shortcut: the budget is fixed, so a model with a 16k to 32k context leaves room unused; scale it with the
# Context size when a reader with such a model asks.
EXCERPT_TOKENS = 2000
# Claude Haiku 5.5 charges 5 times the price of each token for a prompt over 100,000 tokens. _tokens counts 2.5
# characters a token on api.anthropic.com, and P3 measured 2.2, so such a prompt can count here as 88,000.
LARGE_PROMPT = 88_000
LARGE = ('This question can send more than 100,000 tokens. For a prompt of this size, some models charge more for '
         'each token: Claude Haiku 5.5 charges 5 times as much.')


class LargePrompt(Exception):
    """A prompt over ``LARGE_PROMPT`` tokens that the reader did not confirm."""


def _tokens(text, host):
    # shortcut: 2.5 characters a token on api.anthropic.com and 3.5 elsewhere (P3 measured 2.2 to 2.8 and 3.5
    # to 4.6), so a Paper near the Context size can still fail at the provider; ask the provider to count when one does.
    return math.ceil(len(text) / (2.5 if host == 'api.anthropic.com' else 3.5))


def counting_host(settings):
    """The host whose token count ``request`` uses: a Claude model through OpenRouter counts as on Anthropic."""
    host = urlsplit(settings['chat_endpoint']).hostname
    return 'api.anthropic.com' if host == 'openrouter.ai' and settings['chat_model'].startswith('anthropic/') else host


def _excerpt(passages, anchor, room, host):
    """An <excerpt> block with the passage ``anchor``, then the passages of its section, then the passages beside
    them, nearest first, while the block fits ``room`` tokens and ``EXCERPT_TOKENS``. Returns the block and the
    passages in it. Both are empty when ``anchor`` is not in ``passages`` or alone does not fit: the selection
    still holds the quoted text."""
    where = next((index for index, passage in enumerate(passages) if passage['id'] == anchor), None)
    if where is None:
        return '', []
    section = passages[where]['section']
    room = min(room, EXCERPT_TOKENS) - _tokens(EXCERPT.format(''), host)
    chosen = []
    for index in sorted(range(len(passages)),
                        key=lambda index: (passages[index]['section'] != section, abs(index - where), index)):
        # A passage costs its text and the blank line that evidence_text joins it with.
        room -= _tokens(evidence_text({'passages': [passages[index]]}) + '\n\n', host)
        if room < 0:
            break
        chosen.append(index)
    chosen = [passages[index] for index in sorted(chosen)]
    return (EXCERPT.format(evidence_text({'passages': chosen})), chosen) if chosen else ('', [])


def request(paper, thread, question, notes, context_tokens, host):
    """The system blocks, the messages, and the facts about them for one question on a Question card.

    ``thread['turns']`` holds the earlier turns. The Paper is the last system block, so Anthropic can cache it.
    The notes follow it in a user message, and the selection and the question come last. A Paper too large for
    ``context_tokens`` gives an excerpt around the selected passage instead, in the last message, so that no cache
    breakpoint lands on text that changes with each question. A question about the whole Paper then raises
    ``ValueError``.

    The prompt and the output reserve together fit ``context_tokens``, as servers such as vLLM and TGI check.
    ``info`` holds the ``passages`` that the request carries, the number of earlier turns that the turn budget
    left ``dropped``, the reserve, which is the ``max_tokens`` of the answer, and the estimated ``tokens`` of the
    prompt.
    """
    passages = evidence_document(paper)['passages']
    reserve = min(OUTPUT_TOKENS, context_tokens // 4)
    quote = thread.get('quote')
    final = (f'<selection passage="{thread.get("passage")}">\n{quote}\n</selection>\n\n' if quote else '') + question
    notes_block = '<notes>\n' + '\n'.join(notes) + '\n</notes>' if notes else ''
    paper_block = '<paper>\n' + evidence_text({'passages': passages}) + '\n</paper>'
    system = [INSTRUCTIONS, paper_block]
    if _tokens(''.join(system) + notes_block + final, host) + reserve > context_tokens:
        # shortcut: no Evidence selection when a whole-Paper question does not fit; upgrade when a reader with a
        # small model asks.
        if not quote:
            raise ValueError(TOO_LARGE)
        system = [INSTRUCTIONS]
        excerpt_room = context_tokens - reserve - _tokens(INSTRUCTIONS + notes_block + final, host)
        if excerpt_room <= 0:
            raise ValueError(SELECTION_TOO_LARGE)
        excerpt, passages = _excerpt(passages, thread.get('passage'), excerpt_room, host)
        if not excerpt:
            # The <selection> block still has the words and the ID of the selected passage: check a citation of it.
            passages = [passage for passage in paper.get('passages', []) if passage['id'] == thread.get('passage')]
        final = excerpt + final
    # Only finished answers go to the model. A turn with no answer text, such as one that went offline, also
    # keeps the roles alternate, and a stopped or failed answer would come before its own Retry.
    turns = [turn for turn in thread['turns']
             if turn['answer']['text'] and not turn['answer'].get('stopped') and not turn['answer'].get('error')]
    room = context_tokens - reserve - _tokens(''.join(system) + notes_block + final, host)
    history = []
    for turn in reversed(turns):
        room -= _tokens(turn['question'] + turn['answer']['text'], host)
        if room < 0:
            break
        history = [{'role': 'user', 'content': turn['question']},
                   {'role': 'assistant', 'content': turn['answer']['text']}, *history]
    messages = [*([{'role': 'user', 'content': notes_block}] if notes else []), *history,
                {'role': 'user', 'content': final}]
    return system, messages, {'passages': passages, 'dropped': len(turns) - len(history) // 2, 'max_tokens': reserve,
                              'tokens': _tokens(''.join(system) + ''.join(m['content'] for m in messages), host)}


def answer(provider, paper, thread, question, settings, on_text, stop, on_wait=lambda seconds: None):
    """Ask the Chat model one question and return its Turn.

    ``on_text`` gets each new part of the answer, and ``on_wait`` the seconds before a retry after a rate
    limit. A ``ValueError`` from ``request`` raises before the provider
    gets a request. A provider error does not raise: the Turn keeps the text that arrived and the error message.
    An answer cut at the output limit keeps its text too, with ``TRUNCATED`` as its error, unless the reader stopped it.
    The citations are checked against the passages that the request carried, and ``dropped`` is the number of
    earlier turns that it left out.
    """
    started = time.time()
    host = urlsplit(settings['chat_endpoint']).hostname
    # Release 2 sends the reader's Highlights and Notes in place of the empty list.
    system, messages, info = request(paper, thread, question, [], settings['chat_context'], counting_host(settings))
    parts, usage, stopped, error = [], dict(cached=0, new=0, output=0), False, None

    def send(text):
        parts.append(text)
        on_text(text)

    for reasoning in (settings['chat_reasoning'], None):
        try:
            result = provider.stream(system, messages, send, reasoning=reasoning, max_tokens=info['max_tokens'],
                                     stop=stop, on_wait=on_wait)
        except ProviderError as failure:
            # The same rule as Provider.complete(): a model that rejects the reasoning field answers without it.
            if reasoning is not None and not parts and _rejects_reasoning(failure):
                continue
            error = str(failure)
        else:
            usage, stopped = result['usage'], result['stopped']
            if result['truncated'] and not stopped:
                error = TRUNCATED
        break
    text = ''.join(parts)
    cites, unknown = chat_citations(info['passages'], text)
    return {'question': question,
            'answer': {'text': text, 'cites': cites, 'unknown': unknown, 'model': settings['chat_model'],
                       'host': host, 'created_at': started, 'tokens': usage, 'stopped': stopped, 'error': error,
                       'dropped': info['dropped']}}


def refused(question, settings, message):
    """The Turn of a question that the Chat model did not get: the card keeps the question and shows ``message``."""
    return {'question': question,
            'answer': {'text': '', 'cites': [], 'unknown': [], 'model': settings['chat_model'],
                       'host': urlsplit(settings['chat_endpoint']).hostname, 'created_at': time.time(),
                       'tokens': dict(cached=0, new=0, output=0), 'stopped': False, 'error': message, 'dropped': 0}}
