"""The Blog: select, narrate, outline, write the sections and draw the figures in parallel, join, review.

Every stage is one direct structured request through the coordinator, with the rejected answer
carried into the correction. ``BlogWorkflow`` orders the stages; the article and its edits, the
figures, and the review are their own classes, and ``BlogSession`` holds the state they share.
"""
from __future__ import annotations

import copy
import datetime
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from papers.blog_article import Article
from papers.blog_figures import BlogFigures
from papers.blog_prompts import (BLOG_WORKERS, ERROR_CATEGORIES, FIGURE_SCIENCE_CATEGORIES, MAX_FIGURE_CORRECTIONS,
                                 NARRATIVE_PROMPT, OUTLINE_PROMPT, OUTLINE_RESPONSE_SCHEMA, PROMPT_REVISION,
                                 SECTION_PROMPT, SECTION_RESPONSE_SCHEMA, SELECTION_PROMPT)
from papers.blog_review import Findings, Reviewer
from papers.blog_session import BlogSession, EvidenceSupplemented
from papers.coordinator import finalize_run, request_validated, run_stage, select_evidence, write_json
from papers.errors import ProviderError
from papers.explanation import (BLOG_FIGURE_COUNTS, PLAN_SCHEMA, PlanValidationError, candidate_digest, shape,
                                validate_blog_outline, validate_plan)
from papers.passages import Passages
from papers.reading import REVISION as READING_REVISION


class _NarrativeRevised(Exception):
    """The outline asked for a narrative revision; the outline request is rebuilt on the new plan."""


class BlogWorkflow:
    """One Blog run in order: evidence, plan, article, figures, then review until approval."""

    def __init__(self, provider, document, progress, *, image_overview=None):
        self.session = BlogSession(provider, document, progress)
        self.article = Article(self.session)
        self.figures = BlogFigures(self.session)
        self.reviewer = Reviewer(self.session)
        self.overview_basis = self.basis_of(image_overview)
        self.plan_digest = None
        self.title = None
        self.briefs = []
        self.revised_narrative = False
        # Review findings the Blog ships with: advice left open, and errors whose sentences were deleted.
        self.open_advice = []
        self.deleted_errors = []

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
        session.checkpoint('outline', accepted_plan=session.plan, plan_digest=self.plan_digest,
                           evidence=session.evidence)
        return session.plan

    # --- outline, sections, and figures ----------------------------------------------------------

    def outline_messages(self):
        session = self.session
        digest = self.overview_basis['digest'] if self.overview_basis else None
        low, high = BLOG_FIGURE_COUNTS[session.rules.length]
        prompt = OUTLINE_PROMPT.replace('FIGURE_RANGE', f'{low} to {high}')
        return [{'role': 'user', 'content': session.stage_prompt('OUTLINE', prompt)
                 + '\n<accepted_narrative>' + json.dumps(session.plan, ensure_ascii=False) + '</accepted_narrative>'
                 + '\n<retrieved_evidence>' + session.evidence_text() + '</retrieved_evidence>'
                 + '\n<overview_digest>' + json.dumps(digest, ensure_ascii=False) + '</overview_digest>'
                 + '\nReturn one JSON object of this shape: ' + shape(OUTLINE_RESPONSE_SCHEMA)}]

    def outline(self):
        """Plan the title, through-line, terms, sections, and figure briefs, with one narrative revision.

        A revision request runs ``narrate`` again and rebuilds the outline request around the new
        plan; a second revision request fails the run.
        """
        session = self.session
        self.revised_narrative = False

        def validate(value):
            if isinstance(value, dict) and value.get('action') == 'revise_narrative':
                if self.revised_narrative:
                    raise ProviderError('The outline requested a second narrative revision. Draft retained.')
                known = {item['id'] for item in session.evidence['passages']}
                refs = value.get('passage_ids')
                if (not isinstance(value.get('reason'), str) or not value['reason'].strip()
                        or not isinstance(refs, list) or not refs or set(refs) - known):
                    raise PlanValidationError([{'code': 'plan_validation', 'path': 'revise_narrative',
                                                'message': 'a revision needs a reason and known passage ids'}])
                self.revised_narrative = True
                self.narrate(value['reason'])
                raise _NarrativeRevised()
            return validate_blog_outline(value, {'passages': session.evidence['passages']}, session.rules.length)

        for _ in range(2):
            try:
                _, outline = request_validated(session.coordinator, 'outline', self.outline_messages(), validate,
                                               stage='outline', attempts=3, describe='outline object')
                break
            except _NarrativeRevised:
                continue
        else:
            raise ProviderError('The outline was not planned. Draft retained.')
        # A cited title leaves the reader's fallback heading; it never costs a correction.
        title = ' '.join(outline['title'].split())
        self.title = title[:120] if title and '[' not in title else None
        session.outline = outline
        self.briefs = copy.deepcopy(outline['figures'])
        write_json(session.directory / 'outline.json', outline)
        session.checkpoint('sections', accepted_plan=session.plan, plan_digest=self.plan_digest, outline=outline)
        return outline

    def section_messages(self, index):
        """One section's request: the whole outline, the section, its entry, and the terms it may use."""
        session, outline = self.session, self.session.outline
        section = outline['sections'][index]
        earlier = {item['id'] for item in outline['sections'][:index]}
        entry = (outline['sections'][index - 1]['leaves_with'] if index
                 else 'The reader has glanced at the Overview and knows the basics of the field.')
        own = [term for term in outline['terms'] if term['section'] == section['id']]
        known = [term['term'] for term in outline['terms'] if term['section'] in earlier]
        story = {key: outline[key] for key in ('title', 'rationale', 'example', 'sections')}
        return [{'role': 'user', 'content': session.stage_prompt('SECTION ' + section['id'], SECTION_PROMPT)
                 + '\n<outline>' + json.dumps(story, ensure_ascii=False) + '</outline>'
                 + '\n<section>' + json.dumps(section, ensure_ascii=False) + '</section>'
                 + '\n<entry>' + entry + '</entry>'
                 + '\n<terms_to_explain>' + json.dumps(own, ensure_ascii=False) + '</terms_to_explain>'
                 + '\n<known_terms>' + json.dumps(known, ensure_ascii=False) + '</known_terms>'
                 + '\n<retrieved_evidence>' + session.evidence_text() + '</retrieved_evidence>'
                 + '\nReturn one JSON object of this shape: ' + shape(SECTION_RESPONSE_SCHEMA)}]

    def write_section(self, index):
        """One section body with known citations and its own figure marker exactly when it has a figure.

        A section that fails its three attempts gets one more request of its own: six writers make
        one failure likelier than one author did.
        """
        session = self.session
        section = session.outline['sections'][index]
        expected = [section['figure']] if section['figure'] else []

        def validate(value):
            if (not isinstance(value, dict) or set(value) != {'text'} or not isinstance(value['text'], str)
                    or not value['text'].strip()):
                raise ValueError('a section answer is {"text": the section body in Markdown}')
            # The application writes the heading; a body that repeats it keeps the body only.
            body = re.sub(r'\A#+ [^\n]*\n+', '', value['text'].strip())
            markers = re.findall(r'\{\{figure:([^}]+)\}\}', body)
            if markers != expected:
                needed = ('{{figure:' + expected[0] + '}} once') if expected else 'no figure marker'
                raise ValueError('the section has figure markers ' + json.dumps(markers) + '; it needs ' + needed)
            try:
                Passages(session.evidence['passages']).cited_in(body)
            except ProviderError as error:
                raise ValueError(str(error)) from None
            return body

        try:
            _, body = request_validated(session.coordinator, 'section', self.section_messages(index), validate,
                                        stage='section', attempts=3, describe='section object')
        except ProviderError:
            # A cancelled job raises Cancelled, which is not a ProviderError and stops here.
            _, body = request_validated(session.coordinator, 'section', self.section_messages(index), validate,
                                        stage='section', attempts=3, describe='section object')
        return body

    def write(self):
        """Write every section and draw every figure in one pool, then assemble and join the article."""
        session, figures = self.session, self.figures
        sections = session.outline['sections']
        figures.states = [figures.new_state(brief) for brief in self.briefs]
        pool = ThreadPoolExecutor(max_workers=BLOG_WORKERS)
        try:
            section_futures = [pool.submit(self.write_section, index) for index in range(len(sections))]
            figure_futures = [pool.submit(figures.settle, state) for state in figures.states]
            bodies = [future.result() for future in section_futures]
            settled = [future.result() for future in figure_futures]
        except BaseException:
            # A cancelled job or a failed section stops the requests still waiting.
            pool.shutdown(wait=True, cancel_futures=True)
            raise
        pool.shutdown()
        for state in settled:
            figures.set(state)
        self.article.text = '\n\n'.join('## ' + section['heading'] + '\n\n' + body
                                        for section, body in zip(sections, bodies))
        self.article.join(figures.planned_ids())
        for state in figures.states:
            if state['status'] == 'omitted' and state['id'] not in figures.omitted:
                self.omit(state)
        if figures.omitted:
            self.article.remove_figures(sorted(figures.omitted), figures.briefs(), figures.surviving_ids())
        write_json(session.directory / 'draft.json', {'outline': session.outline, 'text': self.article.text})
        self.persist_figures()

    # --- review ------------------------------------------------------------------------------------

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
        """Verdicts until no error is open: a figure finding is one Scene correction, a prose finding exact edits.

        Advice gets one correction for each target, the article or a figure; errors get one every
        round. The Blog ships when nothing is left to answer, with the open advice recorded. Errors
        left after two prose corrections lose their sentences. A live haiku-5.5 run on 2026-10-08
        redrew a figure first and then shipped twelve article advice findings never answered.
        """
        figures, reviewer = self.figures, self.reviewer
        planned = figures.planned_ids()
        ceiling = 1 + (MAX_FIGURE_CORRECTIONS + 2) * len(self.briefs) + 2
        prose_corrections = 0
        corrected_briefs = set()
        # Advice gets one answer for each target: 'article' or a figure ID.
        answered = set()
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
            findings = review['issue_details']
            self.open_advice = [issue for issue in findings if issue.get('category') not in ERROR_CATEGORIES]
            surviving = figures.surviving_ids()
            drawing, article_issues = [], []
            for issue in findings:
                target = Findings.figure_target(issue.get('path', ''), planned)
                # A finding about a missing drawing is a prose problem now: fix the article,
                # never reopen an omitted or exhausted figure.
                target = target if target is not None and target in surviving else 'article'
                if issue.get('category') in ERROR_CATEGORIES or target not in answered:
                    (article_issues if target == 'article' else drawing).append(
                        issue if target == 'article' else (target, issue))
            if review['approved'] or not (drawing or article_issues):
                return
            if len(reviewer.reviews) > ceiling:
                raise ProviderError('The review budget of ' + str(ceiling) + ' verdicts was exhausted. Draft retained.')
            if self.correct_round(drawing, article_issues, answered, corrected_briefs, prose_corrections):
                return
            prose_corrections += 1 if article_issues else 0

    def correct_round(self, drawing, article_issues, answered, corrected_briefs, prose_corrections):
        """Answer one verdict at once: every flagged figure redraws on the pool while the article is
        repaired. On 2026-10-08 one figure per verdict left the article findings waiting three verdicts.

        Returns True when the errors left after two prose corrections lost their sentences.
        """
        figures = self.figures
        targets = list(dict.fromkeys(target for target, _ in drawing))
        answered.update(targets)
        surviving = figures.surviving_ids()
        pool = ThreadPoolExecutor(max_workers=BLOG_WORKERS)
        deleted = False
        try:
            futures = {target: pool.submit(self.redrawn, target, [issue for figure_id, issue in drawing
                                                                  if figure_id == target],
                                           target not in corrected_briefs)
                       for target in targets}
            # The article is the last job, so one worker answers figures first, as tests expect.
            if article_issues and prose_corrections >= 2:
                self.deleted_errors = article_issues
                deleted = True
                article = pool.submit(self.article.delete_errors, article_issues, surviving)
            elif article_issues:
                answered.add('article')
                article = pool.submit(self.article.repair, article_issues, surviving)
            else:
                article = None
            results = {target: future.result() for target, future in futures.items()}
            if article is not None:
                article.result()
        except BaseException:
            pool.shutdown(wait=True, cancel_futures=True)
            raise
        pool.shutdown()
        omitted = []
        for target, (state, corrected) in results.items():
            if corrected:
                corrected_briefs.add(target)
            figures.set(state)
            if state['status'] == 'omitted':
                self.omit(state)
                omitted.append(target)
        if omitted:
            self.article.remove_figures(omitted, figures.briefs(), figures.surviving_ids())
        self.persist_figures()
        return deleted

    def redrawn(self, target, issues, may_correct_brief):
        """One figure's answer to its findings, off the main thread: one brief correction when the
        science is wrong, then a new panel; a figure with no request left is omitted.

        Returns the new state and whether its brief was corrected.
        """
        figures = self.figures
        state = copy.deepcopy(figures.state(target))
        corrected = False
        if state['requests'] < 1 + MAX_FIGURE_CORRECTIONS:
            if may_correct_brief and any(issue.get('category') in FIGURE_SCIENCE_CATEGORIES for issue in issues):
                state['brief'] = figures.correct_brief(state, issues)
                corrected = True
            state['status'] = 'pending'
            state = figures.settle(figures.draw(state, issues=issues))
        elif any(issue.get('category') in ERROR_CATEGORIES for issue in issues):
            # No request remains: an error on an exhausted figure omits it.
            state.update(status='omitted', issues=[str(issue.get('message')) for issue in issues])
        # Advice on an exhausted figure keeps the figure as drawn: on 2026-10-08 one readability
        # note omitted a figure whose first draw had used every request.
        return state, corrected

    # --- completion ------------------------------------------------------------------------------

    def run_workflow(self):
        session, figures, reviewer = self.session, self.figures, self.reviewer
        session.checkpoint('selection')
        # Figures already fall back to omission, and a second review loop would double the
        # costliest stage, so only the first three stages retry.
        run_stage(session.coordinator, 'selection', self.select)
        run_stage(session.coordinator, 'narrative', self.narrate)
        run_stage(session.coordinator, 'outline', self.outline)
        self.write()
        self.review_loop()
        text, plan = self.article.text, session.plan
        write_json(session.directory / 'candidate.json', {'plan': plan, 'outline': session.outline, 'text': text,
                                                          'figures': self.briefs,
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
                'explanation': {'paper_type': plan['paper_type'], 'title': self.title,
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
                               'open_advice': self.open_advice, 'deleted_errors': self.deleted_errors,
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
