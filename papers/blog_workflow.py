"""The Blog: select, narrate, outline, write the sections and draw the figures in parallel, then join.

Every stage is one direct structured request through the coordinator, with the rejected answer
carried into the correction. The application checks each section body itself, with exact
messages, the way the Overview checks a Scene; no model reviews the article. ``BlogWorkflow``
orders the stages; the article and its edits and the figures are their own classes, and
``BlogSession`` holds the state they share.
"""
from __future__ import annotations

import copy
import json
from concurrent.futures import ThreadPoolExecutor

from papers.blog_article import Article
from papers.blog_figures import BlogFigures
from papers.blog_prompts import (BLOG_WORKERS, NARRATIVE_PROMPT, OUTLINE_PROMPT, OUTLINE_RESPONSE_SCHEMA,
                                 PROMPT_REVISION, SECTION_PROMPT, SECTION_RESPONSE_SCHEMA, SELECTION_PROMPT)
from papers.blog_session import BlogSession, EvidenceSupplemented
from papers.coordinator import (evidence_text, iso, provenance, request_validated, run_recorded, run_stage,
                                select_evidence, write_json)
from papers.errors import ProviderError
from papers.explanation import (BLOG_FIGURE_COUNTS, CLAIMS, PLAN_SCHEMA, ValidationError, blog_seams, shape,
                                validate_blog_outline, validate_blog_section, validate_plan)
from papers.passages import uncited
from papers.reading import REVISION as READING_REVISION


class _NarrativeRevised(Exception):
    """The outline asked for a narrative revision; the outline request is rebuilt on the new plan."""


class BlogWorkflow:
    """One Blog run in order: evidence, plan, outline, then the sections and figures in parallel, joined once."""

    def __init__(self, provider, document, progress, *, image_overview=None):
        self.session = BlogSession(provider, document, progress)
        self.article = Article(self.session)
        self.figures = BlogFigures(self.session)
        self.overview_basis = self.basis_of(image_overview)
        self.title = None
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
                                                              session.orientation, instruction=instruction)
        session.evidence['coverage']['revision'] = READING_REVISION

    def narrative_messages(self, reason):
        session = self.session
        return [{'role': 'user', 'content': session.stage_prompt('NARRATIVE PLANNING', NARRATIVE_PROMPT)
                 + '\n<source_map>\n' + json.dumps(session.navigation(), ensure_ascii=False)
                 + '\n</source_map>\n<retrieved_evidence>\n' + evidence_text(session.evidence)
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
                        raise ValidationError([{'code': 'plan_validation', 'path': 'plan',
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
        write_json(session.directory / 'plan.json', session.plan)
        return session.plan

    # --- outline, sections, and figures ----------------------------------------------------------

    def outline_messages(self):
        session = self.session
        digest = self.overview_basis['digest'] if self.overview_basis else None
        low, high = BLOG_FIGURE_COUNTS[session.rules.length]
        prompt = OUTLINE_PROMPT.replace('FIGURE_RANGE', f'{low} to {high}')
        return [{'role': 'user', 'content': session.stage_prompt('OUTLINE', prompt)
                 + '\n<accepted_narrative>' + json.dumps(session.plan, ensure_ascii=False) + '</accepted_narrative>'
                 + '\n<retrieved_evidence>' + evidence_text(session.evidence) + '</retrieved_evidence>'
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
                    raise ValidationError([{'code': 'plan_validation', 'path': 'revise_narrative',
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
                 + '\n<retrieved_evidence>' + evidence_text(session.evidence) + '</retrieved_evidence>'
                 + '\nReturn one JSON object of this shape: ' + shape(SECTION_RESPONSE_SCHEMA)}]

    def write_section(self, index):
        """One section body that passes ``validate_blog_section``.

        A section that fails its three attempts gets one more request of its own: six writers make
        one failure likelier than one author did.
        """
        session = self.session

        def validate(value):
            if (not isinstance(value, dict) or set(value) != {'text'} or not isinstance(value['text'], str)
                    or not value['text'].strip()):
                raise ValueError('a section answer is {"text": the section body in Markdown}')
            return validate_blog_section(value['text'], session.outline, index,
                                         {'passages': session.evidence['passages']})

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
        try:
            self.article.join(figures.planned_ids(), blog_seams(session.outline, bodies))
        except ProviderError as error:
            # The sections already passed their checks, so a join that fails twice ships them as written.
            session.coordinator.note('join_skipped', reason=str(error)[:400])
        omitted = [state['id'] for state in figures.states if state['status'] == 'omitted']
        if omitted:
            try:
                self.article.remove_figures(omitted, figures.briefs(), figures.surviving_ids())
            except ProviderError as error:
                # A cleanup that fails twice ships the sections without the omitted markers. The
                # sections already explain everything in prose, and a 2026-09-18 run failed here.
                self.article.text = Article.without_markers(self.article.text, omitted)
                session.coordinator.note('cleanup_skipped', reason=str(error)[:400])

    # --- completion ------------------------------------------------------------------------------

    def run_workflow(self):
        session, figures = self.session, self.figures
        # Figures already fall back to omission and a failed join ships the sections as written, so
        # only the first three stages retry.
        run_stage(session.coordinator, 'selection', self.select)
        run_stage(session.coordinator, 'narrative', self.narrate)
        run_stage(session.coordinator, 'outline', self.outline)
        self.write()
        text, plan = self.article.text, session.plan
        write_json(session.directory / 'candidate.json', {'plan': plan, 'outline': session.outline, 'text': text,
                                                          'figures': self.briefs,
                                                          'figure_states': figures.records()})
        reading = dict(session.evidence['coverage'], revision=READING_REVISION,
                       document_digest=session.source_digest, selection=session.selection)
        session.coordinator.store.update(status='completed', stage='completed', delivery='completed',
                                         finished_at=iso(), figures=figures.outcomes())
        return {'text': uncited(text),
                'explanation': {'paper_type': plan['paper_type'], 'title': self.title,
                                **{key: plan[key]['text'] for key in CLAIMS},
                                'passages': list(dict.fromkeys(ref for item in (*(plan[key] for key in CLAIMS),
                                                                                *plan['relationships'])
                                                               for ref in item['passages']))},
                'plan': plan, 'cited_text': text, 'figures': figures.publish(),
                'evidence': session.evidence['passages'],
                'provenance': {**provenance(session.coordinator, session.document, session.evidence, PROMPT_REVISION),
                               'reading': reading, 'overview_basis': self.overview_basis,
                               'overview_language': session.rules.language,
                               'overview_length': session.rules.length, 'figure_outcomes': figures.outcomes(),
                               'omitted_figures': [{'id': state['id'], 'requests': state['requests'],
                                                    'issues': state['issues']}
                                                   for state in figures.states if state['status'] == 'omitted'],
                               'cleanup_edits': self.article.edits}}


def generate(provider, document, progress, *, image_overview=None):
    """Run the complete Blog. A failed run gets a terminal run record, then raises its original error."""
    workflow = BlogWorkflow(provider, document, progress, image_overview=image_overview)
    return run_recorded(workflow.session.coordinator, workflow.run_workflow)
