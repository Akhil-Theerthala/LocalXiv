"""The state one Blog run shares across its stages: the paper, the provider, the evidence, and the plan."""
from papers.blog_prompts import BlogRules
from papers.coordinator import Coordinator, create_run_directory, supplement_evidence
from papers.library import document_digest
from papers.reading import build_orientation


class EvidenceSupplemented(Exception):
    """The planner asked for more evidence; its request is rebuilt with the new evidence."""


class BlogSession:
    """One Blog run's shared state. The stages read ``evidence`` and ``plan`` when they need them,
    so an evidence supplement in one stage reaches the next."""

    def __init__(self, provider, document, progress):
        self.provider = provider
        self.document = document
        self.progress = progress
        self.rules = BlogRules(provider.settings)
        self.directory = create_run_directory(document)
        self.coordinator = Coordinator(provider, progress, run_directory=self.directory, workflow='blog')
        self.orientation = build_orientation(document)
        self.source_digest = document_digest(document)
        self.selection = None
        self.evidence = {'passages': [], 'coverage': {}}
        self.plan = None
        self.outline = None

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

    def stage_prompt(self, stage, body):
        return (self.rules.text + '\n\nSTAGE: ' + stage + '\n' + body + '\nOUTPUT MODE: Blog\nPAPER: '
                + self.document.get('title', ''))

    def supplement(self, request):
        """Load the evidence the planner asked for into ``evidence``."""
        self.evidence = supplement_evidence(self.coordinator, self.document, self.orientation,
                                            self.selection, self.evidence, request)
        return self.evidence
