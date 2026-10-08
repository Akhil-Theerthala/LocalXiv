"""The Blog's drawings: one state per brief, each a Scene panel the model authors and ``Figure`` lays out."""
import copy
import json
import re

from papers.blog_prompts import BLOG_DISPLAY_WIDTH, MAX_FIGURE_CORRECTIONS, PANEL_EXAMPLE, PANEL_WRAPPER
from papers.coordinator import request_validated
from papers.errors import ProviderError
from papers.explanation import blog_panel_required
from papers.figures import Figure, LayoutError, SceneError
from papers.figures.schema import card as scene_card


class BlogFigures:
    """The figure states of one Blog, in planned order, and the requests that draw them.

    A state is ``pending`` while it has requests left, then ``accepted`` or ``omitted``.
    """

    # A passage citation in a drawing, bracketed as in the article or in parentheses.
    CITATION = re.compile(r'\s*[\[(]\s*p\d+(?:\s*[,;]\s*p\d+)*\s*[\])]')

    def __init__(self, session):
        self.session = session
        self.renderer = Figure(width=BLOG_DISPLAY_WIDTH)
        self.states = []

    @staticmethod
    def new_state(brief):
        """A fresh pending record for one validated brief."""
        return {'id': brief['id'], 'brief': copy.deepcopy(brief), 'status': 'pending', 'requests': 0,
                'corrections': 0, 'panel': None, 'result': None, 'labels': [], 'issues': [], 'history': []}

    @classmethod
    def uncited(cls, value):
        """A panel without passage citations. The article cites the evidence; in a drawing, "[p00026]"
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

    def state(self, figure_id):
        return next(state for state in self.states if state['id'] == figure_id)

    def set(self, state):
        for index, item in enumerate(self.states):
            if item['id'] == state['id']:
                self.states[index] = state
                return
        self.states.append(state)

    def records(self):
        """The states as JSON: the render result becomes its asset paths."""
        records = []
        for state in self.states:
            record = {key: value for key, value in state.items() if key != 'result'}
            record['result_assets'] = state['result'].assets if state['result'] is not None else None
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
            figure.update(result.assets, source_svg=result.svg, checks=result.checks,
                          dimensions=result.checks['canvas'], alt=brief['title'] + '. ' + brief['caption'],
                          brief=copy.deepcopy(brief), panel=copy.deepcopy(state['panel']), labels=list(state['labels']))
            published.append(figure)
        return published

    # --- drawing ---------------------------------------------------------------------------------

    def settle(self, state):
        """Draw one state until it is accepted or omitted. Reads no other state, so it runs on a worker."""
        while state['status'] == 'pending':
            state = self.draw(state)
        return state

    def messages(self, brief):
        return [{'role': 'user', 'content': self.session.rules.text + '\n\nSTAGE: FIGURE\n' + scene_card() + '\n\n'
                 + PANEL_WRAPPER + '\n\nOne complete example of the object:\n' + PANEL_EXAMPLE
                 + '\n\n<brief>\n'
                 + json.dumps({key: brief[key] for key in ('id', 'title', 'purpose', 'entry_context', 'exit_state',
                                                           'content')}, ensure_ascii=False)
                 + '\n</brief>\n<required>\n' + json.dumps(blog_panel_required(brief), ensure_ascii=False)
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

    def build(self, panel):
        """Lay out and render one panel. Returns the result and the problem a correction must fix."""
        try:
            result = self.renderer.build(panel, self.session.document['directory'], panel['id'], frame='panel')
        except LayoutError as error:
            return None, str(error)
        if result.issues:
            return result, 'The panel rendered with defects: ' + '; '.join(result.issues[:3])
        return result, None

    def draw(self, state):
        """One panel request plus corrections, bounded by MAX_FIGURE_CORRECTIONS over the run.

        Validation and required strings are corrected inside ``request_validated``; a panel that
        cannot be laid out or renders with defects gets one more correction naming the problem.
        The returned state is ``accepted``, ``omitted``, or ``pending`` with requests left.
        """
        coordinator = self.session.coordinator
        state = copy.deepcopy(state)
        brief = state['brief']
        required = blog_panel_required(brief)
        budget = 1 + MAX_FIGURE_CORRECTIONS
        remaining = budget - state['requests']
        if remaining <= 0:
            state['status'] = 'omitted'
            return state

        def validate(value):
            panel = self.renderer.validate(value, frame='panel')
            if panel.get('id') != brief['id']:
                raise SceneError([{'code': 'scene_validation', 'path': 'panel.id',
                                   'message': 'must be ' + brief['id']}])
            missing = self.renderer.missing(panel, required, frame='panel')
            if missing:
                raise SceneError([{'code': 'scene_coverage', 'path': 'panel', 'value': item,
                                   'message': 'the panel does not show ' + json.dumps(item) + ' verbatim'}
                                  for item in missing])
            return self.uncited(panel)

        messages = self.messages(brief)
        before = self.requests_made(brief['id'])
        label = 'figure_' + brief['id']
        result = panel = None
        try:
            raw, panel = request_validated(coordinator, label, messages, validate, stage='figures',
                                           attempts=min(remaining, 3), describe='panel object')
            result, problem = self.build(panel)
            if problem and budget - state['requests'] - (self.requests_made(brief['id']) - before) > 0:
                correction = ('The previous panel laid out with a problem: ' + problem + ' Rearrange the panel '
                              '(put connected cards in one row or one column, put sibling groups side by '
                              'side, or drop an arrow that cannot pass). Return the complete corrected panel object.')
                raw, panel = request_validated(coordinator, label + '_layout', messages + [
                    {'role': 'assistant', 'content': json.dumps(raw, ensure_ascii=False)},
                    {'role': 'user', 'content': correction}], validate, stage='figures', attempts=1,
                    describe='panel object')
                result, problem = self.build(panel)
        except ProviderError as error:
            problem = str(error)
        state['requests'] += self.requests_made(brief['id']) - before
        state['corrections'] = max(0, state['requests'] - 1)
        if problem is None:
            state.update(status='accepted', panel=panel, result=result, issues=[],
                         labels=self.renderer.text(panel, frame='panel'))
        else:
            state.update(status='omitted' if state['requests'] >= budget else 'pending', issues=[problem[:400]])
        state['history'].append({'requests': state['requests'], 'status': state['status'], 'issues': state['issues']})
        self.session.progress('Preparing the Blog')
        return state
