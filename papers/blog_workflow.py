"""The Blog: select, narrate, author, draw each figure as a Scene panel, review, repair.

Every stage is one direct structured request through the coordinator, with the rejected answer
carried into the correction. ``BlogWorkflow`` orders the stages; the article and its edits, the
figures, and the review are their own classes, and ``BlogSession`` holds the state they share.
"""
from __future__ import annotations

import copy
import datetime
import json
from pathlib import Path

from papers.blog_article import Article
from papers.blog_figures import BlogFigures
from papers.blog_prompts import (AUTHOR_RESPONSE_SCHEMA, AUTHORING, FIGURE_SCIENCE_CATEGORIES,
                                 MAX_FIGURE_CORRECTIONS, NARRATIVE_PROMPT, PROMPT_REVISION, SELECTION_PROMPT)
from papers.blog_review import Findings, Reviewer
from papers.blog_session import BlogSession, EvidenceSupplemented
from papers.coordinator import finalize_run, request_validated, select_evidence, write_json
from papers.errors import ProviderError
from papers.explanation import (PLAN_SCHEMA, PlanValidationError, candidate_digest, shape, validate_blog_draft,
                                validate_plan)
from papers.overview import NARRATIVE_TIPS, WRITING_TIPS
from papers.passages import Passages
from papers.reading import REVISION as READING_REVISION


class _NarrativeRevised(Exception):
    """The author asked for a narrative revision; the authoring request is rebuilt on the new plan."""


class BlogWorkflow:
    """One Blog run in order: evidence, plan, article, figures, then review until approval."""

    def __init__(self, provider, document, progress, *, image_overview=None):
        self.session = BlogSession(provider, document, progress)
        self.article = Article(self.session)
        self.figures = BlogFigures(self.session)
        self.reviewer = Reviewer(self.session)
        self.overview_basis = self.basis_of(image_overview)
        self.plan_digest = None
        self.briefs = []
        self.revised_narrative = False

    @staticmethod
    def basis_of(image_overview):
        """The saved Overview's digest and run, when it has a Scene-era plan; otherwise None."""
        if not isinstance(image_overview, dict):
            return None
        plan = image_overview.get('plan')
        if not isinstance(plan, dict) or not plan.get('components'):
            return None
        provenance = image_overview.get('provenance') or {}
        return {'digest': plan, 'run': provenance.get('run'), 'created_at': provenance.get('created_at')}

    # --- selection and narrative ----------------------------------------------------------------

    def select(self):
        """One validated selection request, then local retrieval."""
        session = self.session
        instruction = session.stage_prompt('EVIDENCE SELECTION', SELECTION_PROMPT)
        session.selection, session.evidence = select_evidence(session.coordinator, session.document,
                                                              session.orientation, vision=session.vision,
                                                              instruction=instruction)
        session.evidence['coverage']['revision'] = READING_REVISION
        session.checkpoint('narrative', selection=session.selection, evidence=session.evidence)

    def narrative_messages(self, reason):
        session = self.session
        return [{'role': 'user', 'content': session.stage_prompt('NARRATIVE PLANNING', NARRATIVE_PROMPT)
                 + '\n<source_map>\n' + json.dumps(session.navigation(), ensure_ascii=False)
                 + '\n</source_map>\n<retrieved_evidence>\n' + session.evidence_text()
                 + '\n</retrieved_evidence>\n<narrative_reason>' + reason + '</narrative_reason>'
                 + '\nReturn one JSON object of this shape: ' + shape(PLAN_SCHEMA)}]

    def narrate(self, reason=''):
        """One validated plan request with the coordinator's correction loop and one evidence supplement.

        ``request_validated`` re-sends a fixed message list, so a supplement rebuilds the request
        instead of going through the correction: the retry must carry the new evidence.
        """
        session = self.session
        supplemented = False
        for _ in range(2):
            messages = self.narrative_messages(reason)

            def validate(value):
                nonlocal supplemented
                if isinstance(value, dict) and value.get('action') == 'read_evidence':
                    if supplemented:
                        raise PlanValidationError([{'code': 'plan_validation', 'path': 'plan',
                                                    'message': 'one evidence supplement per plan; return the plan'}])
                    supplemented = True
                    session.supplement(value)
                    raise EvidenceSupplemented()
                return validate_plan(value, {'passages': session.evidence['passages']})

            try:
                _, session.plan = request_validated(session.coordinator, 'narrative', messages, validate,
                                                    stage='narrative', attempts=3, describe='plan object')
                break
            except EvidenceSupplemented:
                continue
        else:
            raise ProviderError('The narrative was not planned after one evidence supplement. Draft retained.')
        self.plan_digest = candidate_digest(session.plan)
        write_json(session.directory / 'plan.json', session.plan)
        session.checkpoint('author', accepted_plan=session.plan, plan_digest=self.plan_digest,
                           evidence=session.evidence)
        return session.plan

    # --- authoring -------------------------------------------------------------------------------

    def author_messages(self):
        session = self.session
        digest = self.overview_basis['digest'] if self.overview_basis else None
        return [{'role': 'user', 'content': session.stage_prompt('AUTHOR', AUTHORING + '\n' + NARRATIVE_TIPS + '\n'
                                                                 + WRITING_TIPS)
                 + '\n<accepted_narrative>' + json.dumps(session.plan, ensure_ascii=False) + '</accepted_narrative>'
                 + '\n<retrieved_evidence>' + session.evidence_text() + '</retrieved_evidence>'
                 + '\n<overview_digest>' + json.dumps(digest, ensure_ascii=False) + '</overview_digest>'
                 + '\nReturn one JSON object of this shape: ' + shape(AUTHOR_RESPONSE_SCHEMA)}]

    def author(self):
        """Author the cited article plus zero to three briefs, with one narrative revision allowed.

        A revision request runs ``narrate`` again and rebuilds the authoring request around the
        new plan; a second revision request fails the run.
        """
        session = self.session

        def validate(value):
            if isinstance(value, dict) and value.get('action') == 'revise_narrative':
                if self.revised_narrative:
                    raise ProviderError('The author requested a second narrative revision. Draft retained.')
                known = {item['id'] for item in session.evidence['passages']}
                refs = value.get('passage_ids')
                if (not isinstance(value.get('reason'), str) or not value['reason'].strip()
                        or not isinstance(refs, list) or not refs or set(refs) - known):
                    raise PlanValidationError([{'code': 'plan_validation', 'path': 'revise_narrative',
                                                'message': 'a revision needs a reason and known passage ids'}])
                self.revised_narrative = True
                self.narrate(value['reason'])
                raise _NarrativeRevised()
            if not isinstance(value, dict):
                raise PlanValidationError([{'code': 'plan_validation', 'path': 'draft',
                                            'message': 'draft must be an object'}])
            # The application holds the accepted plan. Echoing it back failed runs without reasoning,
            # which changed the plan while copying it. Length is cut afterwards by ``Article.shorten``.
            draft = {key: item for key, item in value.items() if key != 'plan'}
            return validate_blog_draft(dict(draft, plan=session.plan), {'passages': session.evidence['passages']},
                                       session.rules.length, word_limit=False)

        for _ in range(2):
            try:
                _, draft = request_validated(session.coordinator, 'author', self.author_messages(), validate,
                                             stage='author', attempts=3, describe='draft object')
                break
            except _NarrativeRevised:
                continue
        else:
            raise ProviderError('The author did not submit a valid Blog draft. Draft retained.')
        self.article.text = draft['text']
        self.briefs = copy.deepcopy(draft['figures'])
        self.article.shorten([brief['id'] for brief in self.briefs])
        draft['text'] = self.article.text
        write_json(session.directory / 'draft.json', draft)
        session.checkpoint('figures', accepted_plan=session.plan, plan_digest=self.plan_digest,
                           article_digest=candidate_digest(self.article.text), briefs=self.briefs)
        return draft

    # --- figures and review ----------------------------------------------------------------------

    def draw_all(self):
        """Draw every pending figure, record the omissions, and clean the prose that depended on them."""
        figures = self.figures
        figures.draw_pending(self.briefs)
        for state in figures.states:
            if state['status'] == 'omitted' and state['id'] not in figures.omitted:
                self.omit(state)
        if figures.omitted:
            self.article.remove_figures(sorted(figures.omitted), figures.briefs(), figures.surviving_ids())
        self.persist_figures()

    def omit(self, state):
        """Record an omitted figure and open the finding that its prose still explains the idea."""
        self.figures.omitted[state['id']] = state
        self.reviewer.close_omitted(state, self.figures.planned_ids())

    def persist_figures(self):
        self.session.checkpoint('figures', figure_states=self.figures.records(),
                                omitted_figures=sorted(self.figures.omitted),
                                cleanup_edits=copy.deepcopy(self.article.edits),
                                open_findings=copy.deepcopy(list(self.reviewer.open_findings.values())))

    def review_loop(self):
        """Verdicts until approval: a figure finding is one Scene correction, a prose finding exact edits."""
        figures, reviewer = self.figures, self.reviewer
        planned = figures.planned_ids()
        ceiling = 1 + (MAX_FIGURE_CORRECTIONS + 2) * len(self.briefs) + 2
        prose_corrections = 0
        prose_counts = {}
        corrected_briefs = set()
        while True:
            review = reviewer.review(self.article.text, figures)
            reviewer.open_findings = {item['id']: item for item in review['issue_details']}
            reviewer.reviews.append(review)
            write_json(self.session.directory / 'reviews.json', reviewer.reviews)
            self.session.checkpoint('review', reviews=reviewer.reviews,
                                    article_digest=candidate_digest(self.article.text),
                                    figure_states=figures.records(), omitted_figures=sorted(figures.omitted),
                                    cleanup_edits=copy.deepcopy(self.article.edits),
                                    open_findings=copy.deepcopy(list(reviewer.open_findings.values())))
            if len(reviewer.reviews) > ceiling:
                raise ProviderError('The review budget of ' + str(ceiling) + ' verdicts was exhausted. Draft retained.')
            if review['approved']:
                return
            surviving = figures.surviving_ids()
            drawing, article_issues = [], []
            for issue in review['issue_details']:
                target = Findings.figure_target(issue.get('path', ''), planned)
                if target is not None and target in surviving:
                    drawing.append((target, issue))
                else:
                    # A finding about a missing drawing is a prose problem now: fix the article,
                    # never reopen an omitted or exhausted figure.
                    article_issues.append(issue)
            if drawing:
                self.redraw(drawing, corrected_briefs)
                continue
            if article_issues:
                if prose_corrections >= 2:
                    raise ProviderError('The article still has unresolved review findings after two '
                                        'corrections. Draft retained.')
                current = {issue['id'] for issue in article_issues}
                prose_counts = {key: value + 1 for key, value in prose_counts.items() if key in current}
                prose_counts.update({key: prose_counts.get(key, 1) for key in current})
                if any(value >= 2 for value in prose_counts.values()):
                    raise ProviderError('A review finding did not improve after one prose correction. '
                                        'Draft retained.')
                self.article.repair(article_issues, surviving)
                prose_corrections += 1
                continue
            raise ProviderError('The review reported no addressable finding. Draft retained.')

    def redraw(self, drawing, corrected_briefs):
        """Answer the findings on the first figure they name: one brief correction when the science is
        wrong, then a new panel; a figure with no request left is omitted."""
        figures = self.figures
        target = drawing[0][0]
        state = copy.deepcopy(figures.state(target))
        target_issues = [issue for figure_id, issue in drawing if figure_id == target]
        if state['requests'] < 1 + MAX_FIGURE_CORRECTIONS:
            if (target not in corrected_briefs
                    and any(issue.get('category') in FIGURE_SCIENCE_CATEGORIES for issue in target_issues)):
                state['brief'] = figures.correct_brief(state, target_issues)
                corrected_briefs.add(target)
            state['status'] = 'pending'
            state = figures.draw(state, issues=target_issues)
            while state['status'] == 'pending':
                state = figures.draw(state)
        else:
            # No request remains: a finding on an exhausted figure omits it.
            state.update(status='omitted', issues=[str(issue.get('message')) for issue in target_issues])
        figures.set(state)
        if state['status'] == 'omitted':
            self.omit(state)
            self.article.remove_figures([target], figures.briefs(), figures.surviving_ids())
        self.persist_figures()

    # --- completion ------------------------------------------------------------------------------

    def run_workflow(self):
        session, figures, reviewer = self.session, self.figures, self.reviewer
        session.checkpoint('selection')
        self.select()
        self.narrate()
        self.author()
        self.draw_all()
        self.review_loop()
        text, plan = self.article.text, session.plan
        write_json(session.directory / 'candidate.json', {'plan': plan, 'text': text, 'figures': self.briefs,
                                                          'figure_states': figures.records()})
        reading = dict(session.evidence['coverage'], revision=READING_REVISION,
                       document_digest=session.source_digest, selection=session.selection)
        events = session.coordinator.events
        document = session.document
        session.coordinator.store.update(status='completed', stage='completed', delivery='completed',
                                         finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                         figures=figures.outcomes(), verdicts=len(reviewer.reviews))
        claims = ('question', 'contribution', 'finding', 'limitation')
        return {'text': Passages.uncited(text),
                'explanation': {'paper_type': plan['paper_type'],
                                **{key: plan[key]['text'] for key in claims},
                                'passages': list(dict.fromkeys(ref for item in (*(plan[key] for key in claims),
                                                                                *plan['relationships'])
                                                               for ref in item['passages']))},
                'plan': plan, 'cited_text': text, 'figures': figures.publish(),
                'evidence': session.evidence['passages'],
                'provenance': {'model': session.provider.settings.get('model'),
                               'document_digest': session.source_digest,
                               'source_digest': document.get('source_digest'), 'arxiv_id': document.get('arxiv_id'),
                               'evidence_format': document.get('format', 'epub'),
                               'pdf_digest': document.get('pdf_digest'),
                               'passages': [item['id'] for item in session.evidence['passages']],
                               'prompt_revision': PROMPT_REVISION, 'reading': reading,
                               'usage': [event for event in events if event.get('usage')], 'events': events,
                               'overview_basis': self.overview_basis, 'overview_language': session.rules.language,
                               'overview_length': session.rules.length, 'reviews': reviewer.reviews,
                               'vision_review': session.vision, 'figure_outcomes': figures.outcomes(),
                               'omitted_figures': [{'id': state['id'], 'requests': state['requests'],
                                                    'issues': state['issues']}
                                                   for state in figures.states if state['status'] == 'omitted'],
                               'cleanup_edits': self.article.edits, 'verdict_count': len(reviewer.reviews),
                               'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                               'run': str(session.directory.relative_to(Path(document['directory'])))}}

    def run(self):
        """Run the complete Blog. A failed run leaves a terminal record and raises ProviderError."""
        try:
            return self.run_workflow()
        except BaseException as error:
            try:
                finalize_run(self.session.coordinator.store, error, stage=self.session.coordinator.active_stage)
            except Exception:
                # Diagnostic writing must never replace the original exception.
                pass
            if isinstance(error, ProviderError):
                raise
            raise ProviderError(str(error)) from None


def generate(provider, document, progress, *, image_overview=None):
    return BlogWorkflow(provider, document, progress, image_overview=image_overview).run()
