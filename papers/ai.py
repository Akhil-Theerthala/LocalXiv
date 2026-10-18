"""One model request through a compatible chat API or the Anthropic Messages API."""
import contextlib
import json
import os
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import anthropic

from papers.errors import ProviderError

# DeepSeek accepts max_tokens up to 393,216. At 64,000, reasoning at medium, high, and max effort
# ran out in 4 of 403 requests on 2026-09-25; the largest that finished used 59,283. 131,072 at the
# slowest tenth's 198 tokens a second takes 660 seconds, inside the request time.
_PROVIDER_LIMITS = {
    'api.openai.com': ('max_completion_tokens', 65_536, 600),
    'openrouter.ai': ('max_tokens', 96_000, 900),
    'api.deepseek.com': ('max_tokens', 131_072, 900),
    'generativelanguage.googleapis.com': ('max_tokens', 65_536, 600),
    # Every Claude model since Haiku 4.5 accepts 64,000 output tokens. Requests stream, so the time is
    # the longest wait between two parts of the response.
    'api.anthropic.com': ('max_tokens', 64_000, 900),
}
_CUSTOM_LIMITS = ('max_tokens', 64_000, 900)


def provider_limits():
    """The output-token cap and request time of each provider host for Settings, and of any other as 'custom'."""
    return {host: f'{tokens:,} output tokens and {seconds // 60} minutes per request'
            for host, (_, tokens, seconds) in {**_PROVIDER_LIMITS, 'custom': _CUSTOM_LIMITS}.items()}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


REASONING_EFFORTS = ('low', 'medium', 'high')


def _reasoning_fields(host, effort):
    """The vendor's own fields for one reasoning effort; ``None`` turns reasoning off where it can be."""
    if host == 'api.deepseek.com':
        if effort is None:
            return {'thinking': {'type': 'disabled'}}
        return {'thinking': {'type': 'enabled'}, 'reasoning_effort': effort}
    if effort is None:
        return {}
    if host == 'generativelanguage.googleapis.com':
        return {'extra_body': {'google': {'thinking_config': {'thinking_level': effort}}}}
    if host == 'openrouter.ai':
        return {'reasoning': {'effort': effort}}
    return {'reasoning_effort': effort}


def _rejects_reasoning(error):
    """An HTTP 400 that names the reasoning field is a model without reasoning, not a failure."""
    text = str(error).lower()
    return 'http status 400' in text and any(word in text for word in ('reasoning', 'thinking', 'effort'))


def _error_detail(message, key):
    """A bounded provider error message without the key, bearer tokens, or image data."""
    if not isinstance(message, str):
        return ''
    if key:
        message = message.replace(key, '[REDACTED]')
    message = re.sub(r'(?i)bearer\s+\S+', 'Bearer [REDACTED]', message)
    message = re.sub(r'data:[^\s\"\']+', '[image data]', message)
    return ' '.join(message.split())[:500]


_REJECTED = 'Provider rejected authentication. Check the saved key and model access.'
_INVALID = ('Provider request failed or returned an invalid response. Check connectivity and provider '
            'settings.')


def _status_error(code, body, key):
    """The error for an HTTP error answer, with a bounded detail from its body and never the key."""
    if code in (401, 403):
        return ProviderError(_REJECTED)
    error = body.get('error', {}) if isinstance(body, dict) else {}
    detail = _error_detail(error.get('message', '') if isinstance(error, dict) else '', key)
    return ProviderError('Provider request failed with HTTP status ' + str(code) + '.' +
                         (' ' + detail if detail else ''))


def _http_error(exc, key):
    # Read only a bounded part of the body, never the full echoed request or credentials.
    with exc:
        try:
            body = json.loads(exc.read(8192))
        except (ValueError, OSError):
            body = None
    return _status_error(exc.code, body, key)


def _declined(message):
    category = getattr(message.stop_details, 'category', None)
    return ProviderError('Claude declined the request' + (' (' + category + ')' if category else '') +
                         '. Try another model.')


def _count(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


@contextlib.contextmanager
def _shut_down_on_stop(response, stop):
    """Shut the connection down when ``stop()`` turns true, also while the provider sends nothing."""
    # A shutdown wakes the blocked read; closing the response from another thread does not.
    sock = socket.socket(fileno=os.dup(response.fileno()))
    done = threading.Event()

    def watch():
        while not done.wait(0.25):
            if stop():
                with contextlib.suppress(OSError):
                    sock.shutdown(socket.SHUT_RDWR)
                return

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    try:
        yield
    finally:
        done.set()
        watcher.join()
        sock.close()


def is_loopback(endpoint):
    """Whether the endpoint is a provider on this Mac."""
    return urllib.parse.urlsplit(endpoint).hostname in ('localhost', '127.0.0.1', '::1')


class Provider:
    def __init__(self, settings, key, *, on_usage=None):
        self.on_usage = on_usage
        self.settings = dict(settings)
        self.key = key
        endpoint = settings.get('endpoint', '').rstrip('/')
        parsed = urllib.parse.urlsplit(endpoint)
        if parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.hostname:
            raise ProviderError('Enter a provider API base URL without credentials, query, or fragment.')
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and is_loopback(endpoint)):
            raise ProviderError('Provider endpoints require HTTPS, except a local provider on loopback.')
        if not settings.get('model'):
            raise ProviderError('Choose a provider model first.')
        self.url = endpoint if endpoint.endswith('/chat/completions') else endpoint + '/chat/completions'
        self.token_field, self.output_cap, self.request_time = _PROVIDER_LIMITS.get(parsed.hostname, _CUSTOM_LIMITS)
        # The base URL is explicit so that ANTHROPIC_BASE_URL in the environment cannot redirect the key.
        self.anthropic = anthropic.Anthropic(
            api_key=key, base_url='https://api.anthropic.com',
            timeout=self.request_time) if parsed.hostname == 'api.anthropic.com' else None

    def complete(self, messages, *, reasoning='low', json_object=False):
        """One chat completion. ``reasoning`` is the effort every provider is asked for.

        The effort is sent in each vendor's own field. A model that rejects the field with HTTP 400
        gets the same request once more without it, so a model without reasoning still answers.
        """
        try:
            return self._complete(messages, reasoning=reasoning, json_object=json_object)
        except ProviderError as error:
            if reasoning is None or not _rejects_reasoning(error):
                raise
            return self._complete(messages, reasoning=None, json_object=json_object)

    def stream(self, system, messages, on_text, *, reasoning='low', max_tokens=8000, stop=lambda: False):
        """One streamed answer. ``on_text`` gets each new part of the text in order.

        ``system`` holds the system blocks, and ``system[-1]`` is the Paper, which Anthropic caches for an
        hour. ``stop()`` turning true ends the request, also while the provider is silent; a watcher thread
        calls it too. A model that rejects the reasoning field before any text gets the request once more
        without it, as in ``complete()``.
        Returns ``{'text', 'usage': {'cached', 'new', 'output'}, 'stopped'}``.
        """
        parts, held = [], ''
        hold = max(len(self.key) - 1, 0)

        def add(text):
            # Hold back the last characters, so that a key split across two parts never leaves.
            nonlocal held
            held += text
            if self.key:
                held = held.replace(self.key, '[REDACTED]')
            if len(held) > hold:
                parts.append(held[:len(held) - hold])
                held = held[len(held) - hold:]
                on_text(parts[-1])

        transport = self._stream_anthropic if self.anthropic else self._stream_compatible
        try:
            usage, stopped = transport(system, messages, add, reasoning=reasoning, max_tokens=max_tokens, stop=stop)
        except ProviderError as error:
            if reasoning is None or parts or held or not _rejects_reasoning(error):
                raise
            usage, stopped = transport(system, messages, add, reasoning=None, max_tokens=max_tokens, stop=stop)
        # A stopped answer drops the held part: it can be most of a key.
        if held and not stopped:
            parts.append(held)
            on_text(held)
        return {'text': ''.join(parts), 'usage': usage, 'stopped': stopped}

    def _stream_compatible(self, system, messages, add, *, reasoning, max_tokens, stop):
        payload = {'model': self.settings['model'],
                   'messages': [{'role': 'system', 'content': '\n\n'.join(system)}, *messages],
                   'stream': True, 'stream_options': {'include_usage': True}, self.token_field: max_tokens}
        payload.update(_reasoning_fields(urllib.parse.urlsplit(self.url).hostname, reasoning))
        headers = {'Content-Type': 'application/json', 'User-Agent': 'LocalXiv/0.1'}
        if self.key:
            headers['Authorization'] = 'Bearer ' + self.key
        request = urllib.request.Request(self.url, data=json.dumps(payload).encode(), headers=headers)
        usage = {'cached': 0, 'new': 0, 'output': 0}
        for attempt in (1, 2):
            try:
                response = urllib.request.build_opener(_NoRedirect).open(request, timeout=self.request_time)
                break
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt == 2:
                    raise _http_error(exc, self.key) from None
                wait = exc.headers.get('Retry-After', '')
                exc.close()
                # One more request after a rate limit, at most 10 s later.
                time.sleep(min(int(wait), 10) if re.fullmatch(r'\d+', wait) else 1)
                if stop():
                    return usage, True
            except Exception:
                raise ProviderError(_INVALID) from None
        finished = False
        try:
            with response, _shut_down_on_stop(response, stop):
                for line in response:
                    # Only data lines carry chunks. Comments, event names, and blank lines do not.
                    if not line.startswith(b'data:'):
                        continue
                    if line[5:].strip() == b'[DONE]':
                        finished = True
                        break
                    chunk = json.loads(line[5:])
                    if chunk.get('usage'):
                        counts = chunk['usage']
                        details = counts.get('prompt_tokens_details')
                        cached = _count((details if isinstance(details, dict) else {}).get('cached_tokens') or
                                        counts.get('prompt_cache_hit_tokens'))
                        usage = {'cached': cached, 'new': max(_count(counts.get('prompt_tokens')) - cached, 0),
                                 'output': _count(counts.get('completion_tokens'))}
                    for choice in chunk.get('choices') or ():
                        if choice.get('finish_reason') == 'error':
                            error = chunk.get('error')
                            detail = _error_detail(error.get('message', '') if isinstance(error, dict) else '',
                                                   self.key)
                            raise ProviderError('Provider did not finish its response (error).' +
                                                (' ' + detail if detail else ''))
                        if text := (choice.get('delta') or {}).get('content'):
                            add(text)
        except ProviderError:
            raise
        except Exception:
            if not stop():
                raise ProviderError(_INVALID) from None
        if not finished and not stop():
            raise ProviderError(_INVALID)
        return usage, not finished

    def _stream_anthropic(self, system, messages, add, *, reasoning, max_tokens, stop):
        blocks = [{'type': 'text', 'text': text} for text in system]
        blocks[-1]['cache_control'] = {'type': 'ephemeral', 'ttl': '1h'}
        params = {'model': self.settings['model'], 'max_tokens': max_tokens, 'system': blocks, 'messages': messages}
        if reasoning is not None:
            params.update(thinking={'type': 'adaptive'}, output_config={'effort': reasoning})
        stopped = False
        try:
            with self.anthropic.messages.stream(**params) as stream:
                # shortcut: stop() is read only at each event, so a stop waits for the next event; shut the
                # socket down as _shut_down_on_stop does if a silent Claude answer stops late.
                for event in stream:
                    if stop():
                        stopped = True
                        break
                    if event.type == 'text':
                        add(event.text)
                message = stream.current_message_snapshot
        except anthropic.APIStatusError as exc:
            raise _status_error(exc.status_code, exc.body, self.key) from None
        except anthropic.AnthropicError:
            raise ProviderError(_INVALID) from None
        if message.stop_reason == 'refusal':
            raise _declined(message)
        counts = message.usage
        return {'cached': counts.cache_read_input_tokens or 0,
                'new': counts.input_tokens + (counts.cache_creation_input_tokens or 0),
                'output': counts.output_tokens}, stopped

    def _complete(self, messages, *, reasoning, json_object):
        if self.anthropic:
            return self._complete_anthropic(messages, reasoning=reasoning)
        payload = {'model': self.settings['model'], 'messages': messages, 'stream': False,
                   self.token_field: self.output_cap}
        if json_object:
            payload['response_format'] = {'type': 'json_object'}
        payload.update(_reasoning_fields(urllib.parse.urlsplit(self.url).hostname, reasoning))
        body = json.dumps(payload).encode()
        request = urllib.request.Request(self.url, data=body, headers={
            'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.key,
            'User-Agent': 'LocalXiv/0.1'})
        try:
            with urllib.request.build_opener(_NoRedirect).open(request, timeout=self.request_time) as response:
                raw = response.read()
            result = json.loads(raw)
            usage = {k: v for k, v in (result.get('usage') or {}).items()
                     if k in ('prompt_tokens', 'completion_tokens', 'total_tokens', 'prompt_cache_hit_tokens',
                              'prompt_cache_miss_tokens')
                     and isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0}
            for field, detail, name in (('prompt_tokens_details','cached_tokens','cached_tokens'),
                                        ('completion_tokens_details','reasoning_tokens','reasoning_tokens')):
                details=(result.get('usage') or {}).get(field)
                value=details.get(detail) if isinstance(details,dict) else None
                if isinstance(value,(int,float)) and not isinstance(value,bool) and value>=0:
                    usage[name]=value
            if self.on_usage:
                self.on_usage(usage)
            choice = result['choices'][0]
            if choice.get('finish_reason') != 'stop':
                reason = str(choice.get('finish_reason', 'unknown'))
                if reason == 'function_call_filter: MALFORMED_FUNCTION_CALL':
                    raise ProviderError('Gemini returned a malformed native function call.')
                reason = reason if re.fullmatch(r'[A-Za-z_]{1,50}', reason) else 'unknown'
                raise ProviderError(
                    'Provider did not finish its response (' + reason +
                    '). The provider stopped generation; try a narrower request or another model.')
            content = choice['message']['content']
            if not isinstance(content, str) or not content.strip():
                raise ValueError()
            # Do not persist a secret even if an upstream error or echo includes it.
            if self.key:
                content = content.replace(self.key, '[REDACTED]')
            return {'text': content, 'usage': usage}
        except urllib.error.HTTPError as exc:
            raise _http_error(exc, self.key) from None
        except ProviderError:
            raise
        except Exception:
            raise ProviderError(_INVALID) from None

    def _complete_anthropic(self, messages, *, reasoning):
        """One request through the Anthropic SDK, streamed so a long answer keeps the connection busy.

        The Messages API has no schema-free JSON mode, so a JSON answer depends on the prompt alone.
        """
        params = {'model': self.settings['model'], 'max_tokens': self.output_cap,
                  'cache_control': {'type': 'ephemeral'},
                  'messages': [{'role': m['role'], 'content': m['content']}
                               for m in messages if m['role'] != 'system']}
        system = '\n'.join(m['content'] for m in messages if m['role'] == 'system')
        if system:
            params['system'] = system
        if reasoning is not None:
            params.update(thinking={'type': 'adaptive'}, output_config={'effort': reasoning})
        try:
            with self.anthropic.messages.stream(**params) as stream:
                message = stream.get_final_message()
        except anthropic.APIStatusError as exc:
            raise _status_error(exc.status_code, exc.body, self.key) from None
        except anthropic.AnthropicError:
            raise ProviderError(_INVALID) from None
        counts = message.usage
        cached = counts.cache_read_input_tokens or 0
        prompt = counts.input_tokens + cached + (counts.cache_creation_input_tokens or 0)
        usage = {'prompt_tokens': prompt, 'completion_tokens': counts.output_tokens,
                 'total_tokens': prompt + counts.output_tokens, 'cached_tokens': cached}
        if self.on_usage:
            self.on_usage(usage)
        if message.stop_reason == 'refusal':
            raise _declined(message)
        if message.stop_reason not in ('end_turn', 'stop_sequence'):
            raise ProviderError(
                'Provider did not finish its response (' + str(message.stop_reason) +
                '). The provider stopped generation; try a narrower request or another model.')
        content = ''.join(block.text for block in message.content if block.type == 'text')
        if not content.strip():
            raise ProviderError(_INVALID)
        if self.key:
            content = content.replace(self.key, '[REDACTED]')
        return {'text': content, 'usage': usage}
