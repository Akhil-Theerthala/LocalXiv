"""The Scene's content limits and the validation helpers that the schema and every node kind share.

A separate module so ``schema`` can derive its tables from the node classes while the classes
validate with the same helpers, without either module importing the other at load time.
"""
import re

PANEL_ID_RE = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,31}')
TONES = ('blue', 'green', 'peach', 'muted')
MAX_DEPTH = 4
LIMITS = {'title': 100, 'subtitle': 240, 'footer': 320, 'heading': 80, 'note_line': 90,
          'panel_note': 160, 'label': 48, 'detail': 100, 'group_heading': 48, 'repeat': 16,
          'item': 16, 'sub': 20, 'cell': 12, 'grid_label': 16, 'caption': 90, 'step': 72, 'bar_label': 28,
          'divider': 48, 'edge_label': 28, 'series_label': 28, 'axis_label': 24}


def _panel_error(errors, path, message, **details):
    errors.append({'code': 'panel_plan_validation', 'path': path, 'message': path + ' ' + message, **details})


def _text(item, key, path, errors, *, maximum=1200):
    value = item.get(key) if isinstance(item, dict) else None
    if not isinstance(value, str) or not value.strip():
        _panel_error(errors, path + '.' + key, f'needs 1-{maximum} characters of text')
    elif len(value) > maximum:
        _panel_error(errors, path + '.' + key,
                     f'has {len(value)} characters; the limit is {maximum}, so shorten it by at least '
                     f'{len(value) - maximum} characters',
                     constraint='maximum_characters', actual=len(value), limit=maximum)


def _identifier(value, path, errors, *, pattern, label):
    if not isinstance(value, str) or not pattern.fullmatch(value):
        _panel_error(errors, path, f'must be a safe {label}: a letter, then letters, digits, dashes or underscores')
        return None
    return value


def _scene_id(node, path, ids, errors):
    if 'id' not in node:
        return
    identifier = _identifier(node['id'], path + '.id', errors, pattern=PANEL_ID_RE, label='card id')
    if identifier in ids:
        _panel_error(errors, path + '.id', 'duplicates an earlier id in this panel')
    ids[identifier] = path


def _scene_lines(lines, path, errors, *, maximum, length):
    if not isinstance(lines, list) or not 1 <= len(lines) <= maximum or any(
            not isinstance(line, str) or not line.strip() for line in lines):
        _panel_error(errors, path, f'needs 1 through {maximum} strings of 1-{length} characters')
        return
    for index, line in enumerate(lines):
        if len(line) > length:
            _panel_error(errors, f'{path}[{index}]',
                         f'has {len(line)} characters; the limit is {length}, so shorten it by at least '
                         f'{len(line) - length} characters',
                         constraint='maximum_characters', actual=len(line), limit=length)
