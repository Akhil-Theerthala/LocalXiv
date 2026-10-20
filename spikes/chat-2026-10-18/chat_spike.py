"""P3 Chat spike: ask questions about 5 Papers with the whole Paper in a cached prefix, and measure each answer.

  python chat_spike.py anthropic --model claude-haiku-5-5 --key keychain --out runs/anthropic.jsonl
  python chat_spike.py compatible --endpoint URL --model M --key keychain|env:NAME|none --out runs/x.jsonl
  python chat_spike.py compatible ... --selection-only --context 4096   (a local model: the selection path only)
  python chat_spike.py anthropic --offline --out runs/offline.jsonl     (one request to a host that does not resolve)

The prompt follows plan section 5.2: the Chat instructions, then the AI view of the Paper (papers/reading.py
evidence_document, formatted as papers/coordinator.py evidence_text), then the selection and the question.
Anthropic gets an explicit cache breakpoint on the Paper block. The Paper text comes from the library row, which
the script opens read only. Each request writes one JSON line; a key is never written or printed.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import anthropic  # noqa: E402

from papers.ai import _PROVIDER_LIMITS, _CUSTOM_LIMITS, _reasoning_fields  # noqa: E402
from papers.coordinator import evidence_text  # noqa: E402
from papers.passages import CITATION  # noqa: E402
from papers.reading import evidence_document  # noqa: E402

LIBRARY = Path.home() / 'Library/Application Support/LocalXiv/library/library.sqlite3'
QUESTIONS = json.loads((HERE / 'questions.json').read_text())
# Plan 5.1: Chat gets its own output cap. 8,000 tokens holds a short answer and low-effort reasoning.
CHAT_OUTPUT_CAP = 8000
# Haiku 5.5 per million tokens, prompt of 100K tokens or fewer: input, output, cache read, 5 m write, 1 h write.
HAIKU_PRICE = {'input': 0.10, 'output': 0.50, 'read': 0.01, 'write_5m': 0.125, 'write_1h': 0.20}
# shortcut: deepseek-chat list prices from late 2025 (miss, hit, output), for an estimate and the budget only.
DEEPSEEK_PRICE = {'input': 0.28, 'read': 0.028, 'output': 0.42}

INSTRUCTIONS = '''You answer a reader's questions about one research Paper while they read it.

- Use only the Paper in <paper>. If the Paper does not answer the question, say so in one sentence, then say what
  the Paper does say about the topic, if anything.
- After each claim that comes from the Paper, cite its passage ID in square brackets, such as [p00017] or
  [p00017, p00018]. Cite only IDs that occur in <paper>.
- If the reader selected a passage, the question is about that passage first.
- Be short: two to six sentences, or a short list. Write inline math in $...$.'''

SELECTION_INSTRUCTIONS = INSTRUCTIONS.replace(
    'Use only the Paper in <paper>.', 'Use only the excerpt of the Paper in <paper>.').replace(
    'If the Paper does not answer', 'If the excerpt does not answer')

# Pauses longer than the 5-minute cache. Each phase asks every Paper in turn, so each Paper waits at least PAUSE.
SCHEDULE = [
    ('ask', '5m', [0, 1, 2]),     # a cold write, then two warm reads
    ('pause',),
    ('ask', '5m', [3]),           # after the pause: the 5-minute entry is gone
    ('pause',),
    ('prewarm', '5m', [4, 5]),    # "Chat opens": a max_tokens=0 pre-warm, then two questions
    ('pause',),
    ('ask', '1h', [6, 7]),        # a 1-hour write, then a warm read
    ('pause',),
    ('ask', '1h', [8, 9]),        # after the pause: the 1-hour entry should still be there
]


def load_paper(paper_id):
    db = sqlite3.connect(f'file:{LIBRARY}?mode=ro', uri=True)
    document = json.loads(db.execute('SELECT value FROM papers WHERE id=?', (paper_id,)).fetchone()[0])
    db.close()
    view = evidence_document(document)
    return document, view


def selection_text(view, passage_id):
    passage = next(p for p in view['passages'] if p['id'] == passage_id)
    text = ' '.join(passage['text'].split())
    return text if len(text) <= 1200 else text[:1200] + ' …'


def user_message(view, question):
    if question.get('selection'):
        return (f'<selection passage="{question["selection"]}">{selection_text(view, question["selection"])}'
                f'</selection>\n\n{question["q"]}')
    return question['q']


def excerpt(view, passage_id, budget_chars):
    """Plan 5.2 selection path: the selected passage, its section, and the passages beside it, within a budget."""
    passages = view['passages']
    index = next(i for i, p in enumerate(passages) if p['id'] == passage_id)
    chosen, low, high = [index], index, index
    size = len(passages[index]['text'])
    while True:
        grown = False
        for candidate in (low - 1, high + 1):
            if 0 <= candidate < len(passages) and size + len(passages[candidate]['text']) <= budget_chars:
                size += len(passages[candidate]['text'])
                chosen.append(candidate)
                low, high = min(low, candidate), max(high, candidate)
                grown = True
        if not grown:
            break
    return {'passages': [passages[i] for i in sorted(chosen)]}


def citations(text, known):
    ids = [ref for group in re.findall(CITATION, text) for ref in re.findall(r'p\d+', group)]
    loose = [ref for ref in re.findall(r'\bp\d{3,}\b', text)]
    return {'cited': ids, 'unknown': [ref for ref in ids if ref not in known],
            'outside_brackets': len(loose) - len(ids)}


def resolve_key(spec, endpoint):
    if spec == 'none':
        return ''
    if spec == 'keychain':
        from papers.settings import get_key
        return get_key(endpoint)
    if spec.startswith('env:'):
        return os.environ.get(spec[4:], '')
    raise SystemExit('--key is keychain, env:NAME, or none')


class AnthropicChat:
    def __init__(self, model, key, base_url='https://api.anthropic.com', max_retries=2):
        self.model = model
        self.client = anthropic.Anthropic(api_key=key or 'x', base_url=base_url, max_retries=max_retries,
                                          timeout=900)

    def _system(self, instructions, paper, ttl):
        cache = {'type': 'ephemeral', **({'ttl': '1h'} if ttl == '1h' else {})}
        return [{'type': 'text', 'text': instructions},
                {'type': 'text', 'text': '<paper>\n' + paper + '\n</paper>', 'cache_control': cache}]

    def prewarm(self, instructions, paper, ttl):
        start = time.monotonic()
        message = self.client.messages.create(
            model=self.model, max_tokens=0, system=self._system(instructions, paper, ttl),
            messages=[{'role': 'user', 'content': 'warmup'}],
            thinking={'type': 'adaptive'}, output_config={'effort': 'low'})
        return {'seconds': round(time.monotonic() - start, 3), 'usage': self._usage(message.usage)}

    def ask(self, instructions, paper, user, ttl, output_cap=CHAT_OUTPUT_CAP):
        start = time.monotonic()
        first_text = first_thinking = None
        with self.client.messages.stream(
                model=self.model, max_tokens=output_cap, system=self._system(instructions, paper, ttl),
                messages=[{'role': 'user', 'content': user}],
                thinking={'type': 'adaptive'}, output_config={'effort': 'low'}) as stream:
            for event in stream:
                if event.type == 'content_block_start' and event.content_block.type == 'thinking':
                    first_thinking = first_thinking or time.monotonic() - start
                elif event.type == 'content_block_delta' and event.delta.type == 'text_delta' and event.delta.text:
                    first_text = first_text or time.monotonic() - start
            message = stream.get_final_message()
        text = ''.join(block.text for block in message.content if block.type == 'text')
        return {'first_text': first_text, 'first_thinking': first_thinking, 'seconds': time.monotonic() - start,
                'stop': message.stop_reason, 'usage': self._usage(message.usage), 'text': text}

    @staticmethod
    def _usage(usage):
        detail = getattr(usage, 'cache_creation', None)
        return {'input': usage.input_tokens, 'output': usage.output_tokens,
                'cache_read': usage.cache_read_input_tokens or 0,
                'cache_write': usage.cache_creation_input_tokens or 0,
                'cache_write_5m': getattr(detail, 'ephemeral_5m_input_tokens', 0) or 0,
                'cache_write_1h': getattr(detail, 'ephemeral_1h_input_tokens', 0) or 0}


class CompatibleChat:
    def __init__(self, endpoint, model, key):
        self.url = endpoint.rstrip('/')
        self.url = self.url if self.url.endswith('/chat/completions') else self.url + '/chat/completions'
        self.host = urllib.parse.urlsplit(self.url).hostname
        self.token_field, self.app_cap, _ = _PROVIDER_LIMITS.get(self.host, _CUSTOM_LIMITS)
        self.model, self.key, self.reasoning = model, key, 'low'

    def _post(self, payload, stream):
        # The app sends 'Bearer ' + key even when the key is empty (papers/ai.py:117); a local server must accept it.
        request = urllib.request.Request(self.url, data=json.dumps(payload).encode(), headers={
            'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.key, 'User-Agent': 'LocalXiv/0.1'})
        return urllib.request.urlopen(request, timeout=900)

    def _payload(self, instructions, paper, user, cap, stream):
        payload = {'model': self.model, 'stream': stream, self.token_field: cap,
                   'messages': [{'role': 'system', 'content': instructions + '\n\n<paper>\n' + paper + '\n</paper>'},
                                {'role': 'user', 'content': user}]}
        if stream:
            payload['stream_options'] = {'include_usage': True}
        payload.update(_reasoning_fields(self.host, self.reasoning))
        return payload

    def prewarm(self, instructions, paper, ttl):
        start = time.monotonic()
        with self._post(self._payload(instructions, paper, 'warmup', 1, False), False) as response:
            result = json.loads(response.read())
        return {'seconds': round(time.monotonic() - start, 3), 'usage': self._usage(result.get('usage') or {})}

    def ask(self, instructions, paper, user, ttl, output_cap=CHAT_OUTPUT_CAP):
        try:
            return self._ask(instructions, paper, user, output_cap)
        except urllib.error.HTTPError as error:
            body = error.read(4000).decode(errors='replace')
            if error.code == 400 and self.reasoning and re.search(r'reasoning|thinking|effort', body, re.I):
                self.reasoning = None  # the model has no reasoning field, as papers/ai.py handles it
                return self._ask(instructions, paper, user, output_cap)
            raise RuntimeError(f'HTTP {error.code}: {" ".join(body.split())[:300]}') from None

    def _ask(self, instructions, paper, user, output_cap):
        start = time.monotonic()
        first_text = first_thinking = None
        text, usage, finish = [], {}, None
        with self._post(self._payload(instructions, paper, user, output_cap, True), True) as response:
            for raw in response:
                line = raw.decode().strip()
                if not line.startswith('data:') or line == 'data: [DONE]':
                    continue
                chunk = json.loads(line[5:])
                usage = chunk.get('usage') or usage
                for choice in chunk.get('choices') or []:
                    delta = choice.get('delta') or {}
                    if delta.get('reasoning_content') or delta.get('reasoning'):
                        first_thinking = first_thinking or time.monotonic() - start
                    if delta.get('content'):
                        first_text = first_text or time.monotonic() - start
                        text.append(delta['content'])
                    finish = choice.get('finish_reason') or finish
        return {'first_text': first_text, 'first_thinking': first_thinking, 'seconds': time.monotonic() - start,
                'stop': finish, 'usage': self._usage(usage), 'text': ''.join(text)}

    @staticmethod
    def _usage(usage):
        details = usage.get('prompt_tokens_details') or {}
        completion = usage.get('completion_tokens_details') or {}
        cached = usage.get('prompt_cache_hit_tokens', details.get('cached_tokens', 0)) or 0
        return {'input': (usage.get('prompt_tokens') or 0) - cached, 'output': usage.get('completion_tokens'),
                'cache_read': cached, 'cache_write': 0, 'reasoning': completion.get('reasoning_tokens')}


def anthropic_cost(usage):
    p = HAIKU_PRICE
    return round((usage['input'] * p['input'] + usage['output'] * p['output'] + usage['cache_read'] * p['read'] +
                  usage['cache_write_5m'] * p['write_5m'] + usage['cache_write_1h'] * p['write_1h']) / 1e6, 6)


def cost_of(provider, usage):
    if provider == 'anthropic':
        return anthropic_cost(usage)
    p = DEEPSEEK_PRICE
    return round((usage['input'] * p['input'] + (usage['output'] or 0) * p['output'] +
                  usage['cache_read'] * p['read']) / 1e6, 6)


def run(args):
    if args.provider == 'anthropic':
        chat = AnthropicChat(args.model, resolve_key(args.key, 'https://api.anthropic.com/v1'))
    else:
        chat = CompatibleChat(args.endpoint, args.model, resolve_key(args.key, args.endpoint.rstrip('/')))
    papers = {pid: load_paper(pid) for pid in QUESTIONS}
    out = open(args.out, 'a')
    spent = [0.0]

    def record(**fields):
        out.write(json.dumps({'at': round(time.time(), 3), 'provider': args.provider, 'model': args.model,
                              **fields}) + '\n')
        out.flush()
        spent[0] += fields.get('cost') or 0
        if spent[0] >= args.budget:
            raise SystemExit(f'Stopped: the measured cost ${spent[0]:.4f} reached the budget ${args.budget}.')

    def ask(paper_id, index, phase, ttl, gap):
        document, view = papers[paper_id]
        question = QUESTIONS[paper_id][index]
        known = {p['id'] for p in view['passages']}
        if args.selection_only:
            # 3 characters a token; 1,024 tokens for the answer, 800 for the instructions and the question.
            budget = (args.context - 1024 - 800) * 3
            context = excerpt(view, question['selection'], budget)
            paper, instructions = evidence_text(context), SELECTION_INSTRUCTIONS
        else:
            paper, instructions = evidence_text(view), INSTRUCTIONS
        try:
            result = chat.ask(instructions, paper, user_message(view, question), ttl,
                              output_cap=args.output_cap or CHAT_OUTPUT_CAP)
        except Exception as error:  # a spike records the failure and goes on
            record(paper=paper_id, q=index, phase=phase, ttl=ttl, error=f'{type(error).__name__}: {error}'[:400])
            return
        cost = cost_of(args.provider, result['usage'])
        record(paper=paper_id, q=index, phase=phase, ttl=ttl, gap=gap, question=question['q'],
               selection=question.get('selection'), paper_chars=len(paper), cost=cost,
               citations=citations(result['text'], known), **result)
        print(f"{paper_id} q{index} {phase:>12} first={result['first_text'] and round(result['first_text'], 2)} "
              f"read={result['usage']['cache_read']} write={result['usage']['cache_write']} "
              f"in={result['usage']['input']} out={result['usage']['output']}", flush=True)

    last = {}
    if args.smoke:
        paper_id = next(iter(QUESTIONS))
        return ask(paper_id, 0, 'smoke', '5m', None)
    if args.selection_only:
        for paper_id, questions in QUESTIONS.items():
            for index, question in enumerate(questions):
                if question.get('selection'):
                    ask(paper_id, index, 'selection', None, None)
        return
    for step in SCHEDULE:
        if step[0] == 'pause':
            print(f'pause {args.pause} s', flush=True)
            time.sleep(args.pause)
            continue
        kind, ttl, indices = step
        for paper_id in QUESTIONS:
            gap = round(time.time() - last[paper_id], 1) if paper_id in last else None
            if kind == 'prewarm':
                document, view = papers[paper_id]
                try:
                    warm = chat.prewarm(INSTRUCTIONS, evidence_text(view), ttl)
                    record(paper=paper_id, phase='prewarm', ttl=ttl, gap=gap, **warm,
                           cost=cost_of(args.provider, warm['usage']))
                except Exception as error:
                    record(paper=paper_id, phase='prewarm', ttl=ttl, error=f'{type(error).__name__}: {error}'[:400])
            for n, index in enumerate(indices):
                phase = ('after-prewarm' if kind == 'prewarm' and n == 0 else
                         'after-pause' if n == 0 and paper_id in last else 'first' if paper_id not in last else 'warm')
                ask(paper_id, index, phase, ttl, gap if n == 0 else None)
                last[paper_id] = time.time()


def offline(args):
    """Criterion 4: how a question fails with no route to the provider, and how long the failure takes."""
    out = open(args.out, 'a')
    for retries in (2, 0):
        chat = AnthropicChat('claude-haiku-5-5', 'x', base_url='https://localxiv-offline.invalid', max_retries=retries)
        start = time.monotonic()
        try:
            chat.ask(INSTRUCTIONS, 'x', 'question', '5m')
            outcome = 'answered'
        except Exception as error:
            outcome = type(error).__name__
        out.write(json.dumps({'offline': 'anthropic-sdk', 'max_retries': retries, 'error': outcome,
                              'seconds': round(time.monotonic() - start, 3)}) + '\n')
    chat = CompatibleChat('https://localxiv-offline.invalid/v1', 'm', 'x')
    start = time.monotonic()
    try:
        chat.ask(INSTRUCTIONS, 'x', 'question', None)
        outcome = 'answered'
    except Exception as error:
        outcome = f'{type(error).__name__}: {error}'[:200]
    out.write(json.dumps({'offline': 'urllib', 'error': outcome, 'seconds': round(time.monotonic() - start, 3)}) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('provider', choices=('anthropic', 'compatible'))
    parser.add_argument('--model', default='claude-haiku-5-5')
    parser.add_argument('--endpoint', default='https://api.anthropic.com/v1')
    parser.add_argument('--key', default='keychain')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--pause', type=int, default=360)
    parser.add_argument('--selection-only', action='store_true')
    parser.add_argument('--context', type=int, default=4096)
    parser.add_argument('--output-cap', type=int, default=0)
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--smoke', action='store_true', help='one question on the first Paper, no pauses')
    parser.add_argument('--budget', type=float, default=1.5, help='stop when the measured cost reaches it, in $')
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    offline(args) if args.offline else run(args)


if __name__ == '__main__':
    main()
