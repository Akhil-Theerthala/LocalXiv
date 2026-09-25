"""The state one Blog run shares across its stages: the paper, the provider, the evidence, and the plan."""
import json
import os
import tempfile
from pathlib import Path

from papers.blog_prompts import CONTEXT_REVISION, PROMPT_REVISION, BlogRules
from papers.coordinator import Coordinator, create_run_directory, supplement_evidence
from papers.errors import ProviderError
from papers.library import document_digest
from papers.passages import Passages
from papers.reading import build_orientation


class EvidenceSupplemented(Exception):
    """A planner or reviewer asked for more evidence; its request is rebuilt with the new evidence."""


class GenerationContext:
    """The state the next stage needs, kept on disk after every stage without secrets or image bytes."""

    SECRET_KEYS = ('url', 'key', 'reasoning_content', 'reasoning_details', 'reasoning')

    def __init__(self, path, values):
        self.path = Path(path)
        self.values = values

    def update(self, stage, **updates):
        self.values.update(stage=stage, **updates)
        self.write()

    def write(self):
        """Replace the file atomically."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=self.path.parent, suffix='.json')
        try:
            with os.fdopen(descriptor, 'w') as stream:
                json.dump(self.on_disk(self.values), stream, ensure_ascii=False, indent=2)
            os.replace(temporary, self.path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    @classmethod
    def on_disk(cls, value):
        if isinstance(value, dict):
            return {key: cls.on_disk(item) for key, item in value.items() if key not in cls.SECRET_KEYS}
        if isinstance(value, list):
            return [cls.on_disk(item) for item in value]
        return value


class BlogSession:
    """One Blog run's shared state. The stages read ``evidence`` and ``plan`` when they need them,
    so an evidence supplement in one stage reaches the next."""

    def __init__(self, provider, document, progress):
        if not document.get('passages'):
            raise ProviderError(document.get('report', {}).get('text_warning')
                                or 'This paper has no retained passages for an overview.')
        if not document.get('directory'):
            raise ProviderError('Save the paper before generating an overview.')
        self.provider = provider
        self.document = document
        self.progress = progress
        self.vision = bool(provider.settings.get('overview_vision', False))
        self.rules = BlogRules(provider.settings)
        self.directory = create_run_directory(document)
        self.coordinator = Coordinator(provider, progress, run_directory=self.directory, workflow='blog')
        self.orientation = build_orientation(document)
        self.source_digest = document_digest(document)
        self.selection = None
        self.evidence = {'passages': [], 'images': [], 'coverage': {}}
        self.plan = None
        self.context = GenerationContext(self.directory / 'generation_context.json', {
            'run_id': self.directory.name, 'context_revision': CONTEXT_REVISION,
            'document_digest': self.source_digest, 'source_digest': document.get('source_digest'),
            'provider': {'endpoint': provider.settings.get('endpoint'),
                         'model': provider.settings.get('model'), 'vision': self.vision},
            'prompt_revision': PROMPT_REVISION, 'schema_revision': PROMPT_REVISION,
            'stage': 'selection', 'selection': None, 'evidence': self.evidence,
            'accepted_plan': None, 'plan_digest': None, 'article_digest': None, 'briefs': [],
            'figure_states': [], 'omitted_figures': [], 'cleanup_edits': [],
            'draft_issues': [], 'reviews': [], 'open_findings': []})

    def navigation(self):
        """Keep post-selection navigation complete without repeating abstract or caption prose."""
        orientation = self.orientation
        figures = {section['id']: [] for section in orientation['sections']}
        for figure in orientation['figures']:
            figures.setdefault(figure.get('section'), []).append(figure['id'])
        return {'revision': orientation['revision'], 'document_digest': orientation['document_digest'],
                'index_kind': orientation['index_kind'],
                'sections': [{'id': item['id'], 'title': item['title'], 'parent': item['parent'],
                              'figure_ids': figures.get(item['id'], [])} for item in orientation['sections']],
                'figures': [{'id': item['id'], 'kind': item['kind'], 'section': item['section'],
                             'passage': item['passage']} for item in orientation['figures']],
                'warnings': orientation['warnings']}

    def checkpoint(self, stage, **updates):
        self.context.update(stage, **updates)

    def stage_prompt(self, stage, body):
        return (self.rules.text + '\n\nSTAGE: ' + stage + '\n' + body + '\nOUTPUT MODE: Blog\nPAPER: '
                + self.document.get('title', ''))

    def evidence_text(self):
        """The retrieved passages as the prompts carry them."""
        return Passages(self.evidence['passages']).prompt_text()

    def supplement(self, request):
        """Load the evidence a planner or reviewer asked for into ``evidence``."""
        self.evidence = supplement_evidence(self.coordinator, self.document, self.orientation,
                                            self.selection, self.evidence, request, vision=self.vision)
        return self.evidence
