"""The Blog's drawings: one state per brief, each a Mermaid diagram the model writes and Pele renders."""
import copy
import json
import re

from papers.blog_prompts import BLOG_DISPLAY_WIDTH, FIGURE_PROMPT, MAX_FIGURE_CORRECTIONS
from papers.coordinator import request_validated
from papers.diagrams import MAIN_CONFIG, check, write_assets
from papers.errors import ProviderError
from papers.explanation import ValidationError, blog_figure_required


class BlogFigures:
    """The figure states of one Blog, in planned order, and the requests that draw them.

    A state is ``pending`` while it has requests left, then ``accepted`` or ``omitted``.
    """

    # A passage citation in a drawing, bracketed as in the article or in parentheses.
    CITATION = re.compile(r'\s*[\[(]\s*p\d+(?:\s*[,;]\s*p\d+)*\s*[\])]')

    def __init__(self, session):
        self.session = session
        self.states = []

    @staticmethod
    def new_state(brief):
        """A fresh pending record for one validated brief."""
        return {'id': brief['id'], 'brief': copy.deepcopy(brief), 'status': 'pending', 'requests': 0,
                'corrections': 0, 'answer': None, 'result': None, 'issues': [], 'history': []}

    @classmethod
    def uncited(cls, value):
        """An answer without passage citations. The article cites the evidence; in a drawing, "[p00026]"
        is noise: reviewers found passage IDs in the figures of Blogs at every reasoning level."""
        if isinstance(value, str):
            return cls.CITATION.sub('', value)
        if isinstance(value, dict):
            return {key: cls.uncited(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls.uncited(item) for item in value]
        return value

    # --- the states ------------------------------------------------------------------------------

    def planned_ids(self):
        return [state['id'] for state in self.states]

    def surviving_ids(self):
        return [state['id'] for state in self.states if state['status'] == 'accepted']

    def briefs(self):
        return [state['brief'] for state in self.states]

    def set(self, state):
        for index, item in enumerate(self.states):
            if item['id'] == state['id']:
                self.states[index] = state

    def records(self):
        """The states as JSON: the render result becomes its asset paths."""
        records = []
        for state in self.states:
            record = {key: value for key, value in state.items() if key != 'result'}
            record['result_assets'] = state['result']['assets'] if state['result'] is not None else None
            records.append(copy.deepcopy(record))
        return records

    def outcomes(self):
        return [{'id': state['id'], 'status': state['status'], 'requests': state['requests'],
                 'corrections': state['corrections'], 'issues': list(state['issues'])} for state in self.states]

    def publish(self):
        """The rendered figures of the accepted states, in planned order."""
        published = []
        for state in self.states:
            if state['status'] != 'accepted' or state['result'] is None:
                continue
            brief, result = state['brief'], state['result']
            figure = {key: brief[key]
                      for key in ('id', 'title', 'paper_connection', 'caption', 'illustrative', 'passages')}
            figure.update(result['assets'], mermaid=state['answer']['mermaid'], layout_width=BLOG_DISPLAY_WIDTH,
                          layout_config=MAIN_CONFIG, dimensions=result['figure'], components=[],
                          alt=brief['title'] + '. ' + brief['caption'],
                          brief=copy.deepcopy(brief))
            published.append(figure)
        return published

    # --- drawing ---------------------------------------------------------------------------------

    def settle(self, state):
        """Draw one state until it is accepted or omitted. Reads no other state, so it runs on a worker."""
        while state['status'] == 'pending':
            state = self.draw(state)
        return state

    def messages(self, brief):
        return [{'role': 'user', 'content': self.session.rules.text + '\n\nSTAGE: FIGURE\n' + FIGURE_PROMPT
                 + '\n\n<brief>\n'
                 + json.dumps({key: brief[key] for key in ('id', 'title', 'purpose', 'entry_context', 'exit_state',
                                                           'content')}, ensure_ascii=False)
                 + '\n</brief>\n<required>\n' + json.dumps(blog_figure_required(brief), ensure_ascii=False)
                 + '\n</required>'}]

    def requests_made(self, figure_id):
        """How many requests this figure's labels have made so far.

        The coordinator's request counter is shared by every section and figure in the pool, so
        on 2026-10-08 one figure counted six requests against a budget of four.
        """
        prefix = 'figure_' + figure_id
        with self.session.coordinator.lock:
            return sum(1 for event in self.session.coordinator.events if event.get('kind') == 'model_request'
                       and (event.get('label') == prefix or str(event.get('label', '')).startswith(prefix + '_')))

    def draw(self, state):
        """One figure request plus corrections, bounded by MAX_FIGURE_CORRECTIONS over the run.

        The Diagram checks are corrected inside ``request_validated``. The returned state is
        ``accepted``, ``omitted``, or ``pending`` with requests left.
        """
        coordinator = self.session.coordinator
        state = copy.deepcopy(state)
        brief = state['brief']
        budget = 1 + MAX_FIGURE_CORRECTIONS
        remaining = budget - state['requests']
        if remaining <= 0:
            state['status'] = 'omitted'
            return state
        checked = {}

        def validate(value):
            if not isinstance(value, dict) or value.get('id') != brief['id']:
                raise ValidationError([{'code': 'diagram', 'path': 'id', 'message': 'id must be ' + brief['id']}])
            value = self.uncited(value)
            checked.update(check(value, width=BLOG_DISPLAY_WIDTH, required=blog_figure_required(brief)))
            return value

        before = self.requests_made(brief['id'])
        answer = problem = None
        try:
            _, answer = request_validated(coordinator, 'figure_' + brief['id'], self.messages(brief), validate,
                                          stage='figures', attempts=min(remaining, 3), describe='figure object')
        except ProviderError as error:
            problem = str(error)
        state['requests'] += self.requests_made(brief['id']) - before
        state['corrections'] = max(0, state['requests'] - 1)
        if problem is None:
            assets = write_assets(self.session.document['directory'], brief['id'], checked, width=BLOG_DISPLAY_WIDTH)
            state.update(status='accepted', answer=answer, result={'assets': assets, 'figure': checked['figure']},
                         issues=[])
        else:
            state.update(status='omitted' if state['requests'] >= budget else 'pending', issues=[problem[:400]])
        state['history'].append({'requests': state['requests'], 'status': state['status'], 'issues': state['issues']})
        self.session.progress('Preparing the Blog')
        return state
