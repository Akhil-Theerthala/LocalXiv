"""Blog figure lifecycle: one drawing request per attempt, four attempts, then omission.

The coordinator owns the article and the review loop. This module owns one figure's state: how
many drawing requests it has spent, whether it is still pending, accepted, or omitted, and the
exact text edits that remove the prose that depended on an omitted figure.

Every attempt makes at most one provider request. ``attempt_figure`` never mutates the state it
is given, so a checkpoint written before dispatch is exactly the budget a crash would retain.
"""
from __future__ import annotations

import copy
import re

from papers import html_figures
from papers.ai import ProviderError
from papers.explanation import blog_figure_assignment, candidate_digest

from papers.panel_authoring import check_panel, missing_value_details, request_panel

# The hard ceiling over the whole run for one stable figure ID: creation plus three repairs.
MAX_FIGURE_ATTEMPTS = 4
_MARKER = '{{figure:%s}}'
_NEWLINE_RUN = re.compile(r'\n{3,}')


def check_blog_figure(source, directory, figure_id):
    """Render one Blog figure at the article width: ``check_panel`` at 640 display units."""
    return check_panel(source, directory, figure_id, display_width=html_figures.BLOG_DISPLAY_WIDTH)


def new_figure_state(brief):
    """A fresh pending record for one validated drawing brief."""
    return {'id': brief['id'], 'brief': copy.deepcopy(brief), 'attempts': 0, 'status': 'pending',
            'checked': None, 'issues': [], 'history': [], 'source': None}


def _defect_line(issue):
    """One repair-prompt line: the message plus its location and measured size when known."""
    if isinstance(issue, str):
        return issue
    if not isinstance(issue, dict):
        return str(issue)
    message = str(issue.get('message') or issue.get('value') or issue)
    path = issue.get('path')
    actual = issue.get('actual')
    limit = issue.get('limit')
    if path:
        message = str(path) + ': ' + message
    if isinstance(actual, (int, float)) and isinstance(limit, (int, float)):
        message += ' (measured ' + str(actual) + '; limit ' + str(limit) + ')'
    return message


def _finish(updated, attempt, usage, error, error_kind, defects, checkpoint):
    """Append one history entry, checkpoint the settled state, and return it."""
    updated['history'] = list(updated.get('history') or []) + [{
        'attempt': attempt,
        'status': updated['status'],
        'usage': copy.deepcopy(usage) if isinstance(usage, dict) else {},
        'error': error,
        'error_kind': error_kind,
        'issues': [_defect_line(item) for item in defects],
        'issue_details': copy.deepcopy(defects),
    }]
    if checkpoint is not None:
        checkpoint(copy.deepcopy(updated))
    return updated


def attempt_figure(provider, state, directory, *, issues=(), image=None, options=None,
                   checkpoint=None):
    """Make at most one Blog drawing request for one figure and return the updated state.

    ``state`` is never mutated. An omitted figure is terminal and an accepted figure with no
    new issues is returned unchanged. The attempt counter is incremented and ``checkpoint`` is
    called before dispatch so a later review cannot restore the budget, then ``checkpoint`` is
    called again after the native check. Authentication failures raise ``ProviderError``;
    transport and invalid-output failures consume the attempt and stay pending; a local
    renderer ``ValueError`` propagates. The fourth unsuccessful attempt marks the figure
    omitted. Each history entry records the attempt, usage, error, error kind, defect strings,
    and the raw defect list.
    """
    updated = copy.deepcopy(state)
    if updated.get('status') == 'omitted':
        return updated
    new_issues = [item for item in (issues or [])]
    if updated.get('status') == 'accepted' and not new_issues:
        return updated
    if updated.get('status') == 'accepted':
        updated['status'] = 'pending'
    stored_issues = list(updated.get('issues') or [])
    prompt_issues = stored_issues + new_issues
    assignment = blog_figure_assignment(updated['brief'])
    updated['attempts'] = int(updated.get('attempts') or 0) + 1
    attempt = updated['attempts']
    if checkpoint is not None:
        checkpoint(copy.deepcopy(updated))
    result = request_panel(provider, assignment, previous=updated.get('source'),
                           issues=[_defect_line(item) for item in prompt_issues],
                           image=image, options=options, purpose='blog')
    usage = result.get('usage') if isinstance(result.get('usage'), dict) else {}
    if result.get('error_kind') == 'authentication':
        raise ProviderError(result.get('error') or 'Provider rejected authentication.')
    if result.get('source') is None:
        kind = result.get('error_kind') or 'transport'
        updated['status'] = 'omitted' if attempt >= MAX_FIGURE_ATTEMPTS else 'pending'
        return _finish(updated, attempt, usage, result.get('error'), kind, stored_issues, checkpoint)
    checked = check_blog_figure(result['source'], directory, updated['id'])
    updated['source'] = checked['source']
    updated['checked'] = checked
    defects = list(checked['checks'].get('issue_details') or [])
    defects += missing_value_details(assignment, checked['labels'])
    updated['issues'] = copy.deepcopy(defects)
    if defects:
        updated['status'] = 'omitted' if attempt >= MAX_FIGURE_ATTEMPTS else 'pending'
    else:
        updated['status'] = 'accepted'
    return _finish(updated, attempt, usage, result.get('error'), result.get('error_kind'),
                   updated['issues'], checkpoint)


def remove_omitted_markers(text, omitted_ids):
    """Remove each exact ``{{figure:ID}}`` marker from the article text.

    A marker alone on its line removes the whole line; inline markers leave the surrounding
    text untouched. Runs of three or more newlines left behind then collapse to two.
    """
    result = str(text)
    for figure_id in omitted_ids:
        marker = _MARKER % figure_id
        result = re.sub(r'(?m)^[ \t]*' + re.escape(marker) + r'[ \t]*\n?', '', result)
        result = result.replace(marker, '')
    return _NEWLINE_RUN.sub('\n\n', result)


def apply_text_edits(text, edits, *, base_digest):
    """Apply exact source-span edits bound to the current text digest.

    ``base_digest`` must equal ``candidate_digest(text)``. Each edit has a nonempty ``old``
    string that occurs exactly once and a ``new`` string that may be empty. Source spans may
    not overlap, so the replacements are applied in reverse position order and can never match
    another replacement's output.
    """
    if not isinstance(base_digest, str) or base_digest != candidate_digest(text):
        raise ValueError('The text edits were written against a different article digest.')
    if not isinstance(edits, list) or not edits:
        raise ValueError('The correction contains no edits.')
    spans = []
    seen = set()
    for index, edit in enumerate(edits):
        if (not isinstance(edit, dict) or set(edit) != {'old', 'new'}
                or not isinstance(edit.get('old'), str) or not edit['old']
                or not isinstance(edit.get('new'), str)):
            raise ValueError('edit ' + str(index) + ' needs a nonempty old string and a new string')
        old = edit['old']
        if old in seen:
            raise ValueError('edit ' + str(index) + ' repeats an old string')
        seen.add(old)
        first = text.find(old)
        if first < 0:
            raise ValueError('edit ' + str(index) + ' old text does not occur in the article')
        if text.find(old, first + 1) != -1:
            raise ValueError('edit ' + str(index) + ' old text occurs more than once in the article')
        spans.append((first, first + len(old), edit['new']))
    spans.sort()
    for (_, end, _), (start, _, _) in zip(spans, spans[1:]):
        if start < end:
            raise ValueError('text edits have overlapping source spans')
    result = text
    for start, end, new in reversed(spans):
        result = result[:start] + new + result[end:]
    return result
