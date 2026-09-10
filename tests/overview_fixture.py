"""Deterministic cited evidence response; no credentials or network calls."""
import re


def response(messages, **kwargs):
    prompt = messages[-1]['content']
    ref = re.findall(r'\[(p\d+)\]', prompt)[0]
    text = 'Supported result [' + ref + '].'
    return {'text': text, 'usage': {'total_tokens': 42}}
