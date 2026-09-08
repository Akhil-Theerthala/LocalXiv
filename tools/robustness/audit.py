"""Read-only source/PDF/reader fidelity checks; counts and anchors are heuristics.
Run with a Python environment containing pypdf. Never executes source TeX.
"""
from __future__ import annotations
import collections
import datetime
import hashlib
import gzip
import io
import json
import re
import tarfile
import tempfile
import sys
import unicodedata
import zipfile
import posixpath
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET
from native.host import _command_values, _reference_id, _braced_argument, _skip_tex_trivia, _searchable_tex_source

ROOT = Path(__file__).resolve().parents[2]
AUDIT_REVISION = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
_COMMENT_ENVIRONMENT = re.compile(
    r"(?<!\\)\\begin\s*\{\s*comment\s*\}.*?"
    r"^[ \t]*(?<!\\)\\end\s*\{\s*comment\s*\}[ \t]*(?=\r?$)",
    re.DOTALL | re.MULTILINE,
)


def searchable_source(text):
    masked = _searchable_tex_source(text)
    return _COMMENT_ENVIRONMENT.sub(
        lambda match: ''.join(char if char in '\r\n' else ' ' for char in match.group(0)),
        masked,
    )


def normalized(text):
    return ' '.join(re.findall(r'[a-z0-9]+', unicodedata.normalize('NFKD', text).lower()))


def prose(tex):
    tex = re.sub(r'(?<!\\)%[^\n]*', '', tex)
    tex = re.sub(r'\\(?:cite\w*|ref|label)\*?(?:\[[^]]*\])*\{[^{}]*\}', '', tex)
    tex = re.sub(r'\\[A-Za-z@]+\*?', '', tex)
    return tex.replace('{', '').replace('}', '')


def source_inventory(path):
    if tarfile.is_tarfile(path):
        with tarfile.open(path) as archive:
            files = {str(PurePosixPath(m.name)): archive.extractfile(m).read().decode('utf-8', 'replace')
                     for m in archive if m.isfile() and (m.name.endswith(('.tex', '.bbl')) or PurePosixPath(m.name).name=='00README.json')}
    else:
        raw = path.read_bytes()
        if raw.startswith(b'\x1f\x8b'):
            raw = gzip.decompress(raw)
        files = {'main.tex': raw.decode('utf-8', 'replace')}
    candidates = [(name, text) for name, text in files.items()
                  if '\\begin{document}' in searchable_source(text)
                  and re.search(r'\\document(?:class|style)', searchable_source(text))]
    if not candidates:
        return {'error': 'No TeX root detected'}, ''
    name, _ = sorted(candidates, key=lambda pair: (len(PurePosixPath(pair[0]).parts), -len(pair[1])))[0]
    root_selection = 'shallowest largest document candidate'
    for readme, text in files.items():
        if PurePosixPath(readme).name != '00README.json':
            continue
        top = [str(PurePosixPath(readme).parent / item['filename'])
               for item in json.loads(text).get('sources', []) if item.get('usage')=='toplevel']
        if len(top)==1 and top[0] in files:
            name = top[0]
            root_selection = 'official 00README.json toplevel'
            break
    visited = set()
    missing = []

    def expand(current):
        if current in visited:
            return ''
        visited.add(current)
        text = searchable_source(files[current])
        def include(match):
            raw = match[1].strip()
            if not PurePosixPath(raw).suffix:
                raw += '.tex'
            choices = [str(PurePosixPath(name).parent / raw), str(PurePosixPath(current).parent / raw), raw]
            target = next((choice for choice in choices if choice in files), None)
            if target is None:
                missing.append(raw)
                return ''
            return expand(target)
        return re.sub(r'\\(?:input|include)\s*\{([^{}]+)\}', include, text)

    text = expand(name)
    body = text.split('\\begin{document}', 1)[-1].split('\\end{document}', 1)[0]
    environments = collections.Counter(re.findall(r'\\begin\s*\{([^{}]+)\}', body))
    headings = []
    for command in ['section', 'subsection', 'subsubsection', 'chapter']:
        headings.extend(_command_values(body.replace('\\'+command+'*', '\\'+command), command))
    captions = _command_values(body, 'caption')
    spanning_cells = []
    searchable = _searchable_tex_source(body)
    for match in re.finditer(r'(?<!\\)\\multicolumn\b', searchable):
        position = match.end()
        arguments = []
        for _ in range(3):
            argument = _braced_argument(searchable, _skip_tex_trivia(searchable, position))
            if argument is None: break
            arguments.append(body[argument[0]:argument[1]])
            position = argument[1] + 1
        if len(arguments) == 3:
            spanning_cells.append(prose(arguments[2]))
    abstracts = _command_values(text,'abstract') + re.findall(r'\\begin\{abstract\}(.*?)\\end\{abstract\}',text,re.DOTALL)
    own_bbl = str(PurePosixPath(name).with_suffix('.bbl'))
    bbl = files.get(own_bbl, '\n'.join(value for key, value in files.items() if key.endswith('.bbl')))
    fragments = {}
    items = list(re.finditer(r'\\bibitem(?:\[[^]]*\])?\s*\{([^{}]+)\}', bbl))
    for index, item in enumerate(items):
        bib_body = bbl[item.end():items[index+1].start() if index+1<len(items) else len(bbl)]
        fragments[_reference_id(item[1])] = [normalized(prose(value)) for value in _command_values(bib_body,'newblock') if normalized(prose(value))]
    info = {'root': name, 'root_selection':root_selection, 'reachable_tex_files': sorted(visited), 'unresolved_includes': missing,
            'counts_are_heuristic': True, 'figures': environments['figure'] + environments['figure*'],
            'graphics_commands': len(re.findall(r'\\(?:includegraphics|epsfbox)\b', body)),
            'distinct_literal_graphics_targets':len(set(re.findall(r'\\(?:includegraphics|epsfbox)(?:\[[^]]*\])?\s*\{\{?([^{}]+)\}', body))),
            'captions': len(captions), 'tables': environments['table'] + environments['table*'],
            'tabular_environments': sum(n for k,n in environments.items() if k.startswith('tabular')),
            'display_math_environments': sum(n for k,n in environments.items() if k.rstrip('*') in {'equation','align','alignat','gather','multline','displaymath','eqnarray'}),
            'inline_dollar_pairs': len(re.findall(r'(?<!\\)\$(?!\$)', body)) // 2,
            'headings': len(headings), 'appendix_commands': len(re.findall(r'\\appendix\b', body)),
            'compiled_bibliography_items': len(re.findall(r'\\bibitem\b', bbl or body)),
            'heading_texts': [prose(h) for h in headings], 'caption_texts': [prose(c) for c in captions]}
    info['abstract_texts'] = [prose(value) for value in abstracts]
    info['spanning_cell_texts'] = spanning_cells
    info['note_texts'] = [{'command':command,'text':prose(value)}
                          for command in ('footnote','footnotetext','tablefootnote','thanks','affiliation','contribution','correspondence')
                          for value in _command_values(text,command)]
    info['_bibliography_fragments'] = fragments
    return info, normalized(prose(body + '\n' + bbl + '\n' + '\n'.join(abstracts)))


def tag(element):
    return element.tag.rsplit('}', 1)[-1]


def visible_text(element):
    """Keep inline words intact; separate block boundaries and whole math expressions."""
    if tag(element) in {'annotation', 'annotation-xml'}:
        return ''
    text = (element.text or '') + ''.join(visible_text(child) + (child.tail or '') for child in element)
    if tag(element) in {'p','h1','h2','h3','h4','h5','h6','li','td','th','caption','figcaption','math','br','title'}:
        return ' ' + text + ' '
    return text


def reader_inventory(work, document, archive=None):
    counts = collections.Counter()
    texts, headings, empty_figures, figure_details = [], [], [], []
    references = {}
    for chapter in document['chapters']:
        path = work / chapter['path']
        root = ET.fromstring(archive.read(chapter['path'])) if archive else ET.parse(path).getroot()
        for element in root.iter():
            local = tag(element); counts[local] += 1
            classes = element.get('class', '').split()
            if local=='table' and 'ltx_eqn_table' not in classes:
                counts['data_tables'] += 1
            if local=='table' and 'ltx_eqn_table' in classes:
                counts['equation_layout_tables'] += 1
            if local=='div' and 'tabular' in classes:
                counts['unparsed_tabular_blocks'] += 1
            if 'ltx_bibitem' in classes or 'csl-entry' in classes or element.get('id','').startswith('ref-'):
                counts['bibliography_items'] += 1
                references[element.get('id','')] = normalized(visible_text(element))
            if 'ltx_appendix' in classes:
                counts['appendix_sections'] += 1
            if local in {'h1','h2','h3','h4','h5','h6'}:
                headings.append(' '.join(''.join(element.itertext()).split()))
            if local == 'figure':
                images = [e.get('src', e.get('data','')) for e in element.iter() if tag(e) in {'img','object'}]
                noncaption = ' '.join(''.join(child.itertext()) for child in element if tag(child) != 'figcaption').strip()
                caption = ' '.join(''.join(e.itertext()) for e in element.iter() if tag(e) == 'figcaption')
                detail = {'chapter':chapter['path'],'id':element.get('id'), 'images':images,'caption':caption[:200]}
                figure_details.append(detail)
                if not images and not any(tag(e) in {'svg','table'} for e in element.iter()) and len(normalized(noncaption)) < 20:
                    empty_figures.append(detail)
        for parent in root.iter():
            for child in list(parent):
                if tag(child) in {'annotation','script','style'}:
                    parent.remove(child)
        texts.append(visible_text(root))
    return {'mathml':counts['math'], 'images':counts['img'], 'figures':counts['figure'],
            'captions':counts['figcaption']+counts['caption'], 'figure_captions':counts['figcaption'],
            'table_captions':counts['caption'], 'tables':counts['data_tables'],
            'unparsed_tabular_blocks':counts['unparsed_tabular_blocks'],
            'equation_layout_tables':counts['equation_layout_tables'], 'headings':len(headings),
            'explicit_appendix_sections':counts['appendix_sections'],
            'bibliography_items':counts['bibliography_items'], 'heading_texts':headings,
            '_bibliography_text':references,
            'empty_figures':empty_figures,'figure_details':figure_details}, normalized('\n'.join(texts))


def semantic_inventory(work):
    with zipfile.ZipFile(work/'semantic.epub') as archive:
        container = ET.fromstring(archive.read('META-INF/container.xml'))
        opf_path = next(e.get('full-path') for e in container.iter() if tag(e)=='rootfile')
        opf = ET.fromstring(archive.read(opf_path))
        manifest = {e.get('id'):e.get('href') for e in opf.iter() if tag(e)=='item'}
        excluded = {e.get('href') for e in opf.iter() if tag(e)=='reference' and e.get('type')=='cover'}
        excluded.update(e.get('href') for e in opf.iter() if tag(e)=='item' and 'nav' in e.get('properties','').split())
        chapters = [{'path':posixpath.normpath(posixpath.join(posixpath.dirname(opf_path),manifest[e.get('idref')]))}
                    for e in opf.iter() if tag(e)=='itemref' and e.get('linear','yes')!='no' and manifest[e.get('idref')] not in excluded]
        return reader_inventory(work, {'chapters':chapters}, archive)


def audit(paper, work=None):
    from pypdf import PdfReader
    work = work or ROOT / '.verification/converted' / paper['id']
    entry = {'id':paper['id'], 'title':paper['title'], 'audit_revision':AUDIT_REVISION}
    if not (work/'document.json').exists():
        return {**entry,'status':'no_completed_document'}
    document = json.loads((work/'document.json').read_text())
    entry['converter'] = document['converter']
    entry['document_sha256'] = hashlib.sha256((work/'document.json').read_bytes()).hexdigest()
    entry['semantic_epub_sha256'] = hashlib.sha256((work/'semantic.epub').read_bytes()).hexdigest()
    entry['source'], source_text = source_inventory(ROOT / paper['directory'] / paper.get('source_file', 'source.tar'))
    entry['reader'], reader_text = reader_inventory(work, document)
    entry['semantic_epub'], semantic_text = semantic_inventory(work)
    source_fragments = entry['source'].pop('_bibliography_fragments',{})
    references = entry['reader'].pop('_bibliography_text',{})
    entry['semantic_epub'].pop('_bibliography_text',None)
    missing_bibliography = [{'reference_id':key,'source_fragment':fragment}
                           for key,fragments in source_fragments.items() if key in references
                           for fragment in fragments if fragment not in references[key]]
    pdf = PdfReader(ROOT / paper['directory'] / paper.get('pdf_file', 'paper.pdf'))
    pdf_pages = [page.extract_text() or '' for page in pdf.pages]
    pdf_text = normalized(' '.join(pdf_pages))
    anchors, missing, seen = [], [], set()
    title = normalized(paper['title'])
    for page_number, page in enumerate(pdf_pages, 1):
        # Only exact 10-word anchors independently present in original TeX and PDF.
        words = normalized(page).split()
        for start in range(0,len(words)-10,10):
            sample = words[start:start+10]
            anchor = ' '.join(sample)
            if anchor in seen or anchor in title or sum(w.isalpha() and len(w)>2 for w in sample)<7 or anchor not in source_text:
                continue
            seen.add(anchor)
            anchors.append(anchor)
            if anchor not in reader_text:
                fragments_present = any(' '.join(sample[i:i+6]) in reader_text for i in range(5))
                missing.append({'pdf_page':page_number,'text':anchor,
                                'classification':'partial_phrase_present_check_formatting_or_boundary' if fragments_present else 'needs_context_review'})
    missing_captions = []
    for caption in entry['source'].get('caption_texts',[]):
        words = normalized(caption).split()
        anchor = ' '.join(words[:10])
        if len(words)>=10 and anchor in pdf_text and anchor not in reader_text:
            missing_captions.append(anchor)
    missing_notes = []
    for note in entry['source'].get('note_texts',[]):
        words = normalized(note['text']).split()
        anchor = ' '.join(words[:10])
        minimum = 2 if note['command'] in {'affiliation','contribution','correspondence'} else 7
        if len(words)>=minimum and anchor in pdf_text and anchor not in reader_text:
            missing_notes.append({'command':note['command'],'anchor':anchor})
    missing_abstracts = []
    for abstract in entry['source'].get('abstract_texts',[]):
        words = normalized(abstract).split()
        anchor = ' '.join(words[:10])
        if len(words)>=10 and anchor in pdf_text and anchor not in reader_text:
            missing_abstracts.append(anchor)
    missing_table_text = []
    for value in entry['source'].get('spanning_cell_texts', []):
        words = normalized(value).split()
        anchor = ' '.join(words[:10])
        if sum(word.isalpha() for word in words) >= 2 and len(anchor) >= 12 and anchor in pdf_text and anchor not in reader_text:
            missing_table_text.append(anchor)
    flags = []
    if entry['source'].get('error'):flags.append('source_inventory_unavailable')
    if entry['reader']['empty_figures']:flags.append('empty_figure')
    if entry['reader']['unparsed_tabular_blocks']:flags.append('unparsed_tabular_blocks')
    if missing_bibliography:flags.append('braced_bibliography_fragment_missing')
    if missing_captions:flags.append('source_pdf_caption_anchor_missing')
    if missing_notes:flags.append('source_pdf_note_anchor_missing')
    if missing_abstracts:flags.append('source_pdf_abstract_anchor_missing')
    if missing_table_text:flags.append('source_pdf_table_text_missing')
    if len(missing)>=5:flags.append('source_pdf_prose_anchors_missing')
    if entry['source'].get('graphics_commands',0)>0 and entry['reader']['images']==0:flags.append('all_images_missing')
    elif entry['source'].get('distinct_literal_graphics_targets',0)>entry['reader']['images']:flags.append('distinct_source_graphics_count_exceeds_reader_images')
    if entry['source'].get('display_math_environments',0)>0 and entry['reader']['mathml']==0:flags.append('all_mathml_missing')
    for key in ('mathml','images','figures','tables'):
        if entry['reader'][key] != entry['semantic_epub'][key]:
            flags.append('reader_semantic_' + key + '_count_differs')
    entry.update(status='needs_review' if flags else 'no_flags_in_checks',flags=flags,
                 pdf_pages=len(pdf.pages),shared_source_pdf_anchors=len(anchors),
                 missing_reader_anchors=len(missing), missing_reader_anchor_examples=missing,
                 anchor_review_classifications=dict(collections.Counter(m['classification'] for m in missing)),
                 missing_caption_anchors=missing_captions,
                 missing_note_anchors=missing_notes,
                 missing_abstract_anchors=missing_abstracts,
                 missing_table_text_anchors=missing_table_text,
                 bibliography_fragment_checks=sum(len(v) for k,v in source_fragments.items() if k in references),
                 missing_bibliography_fragments=missing_bibliography,
                 reader_anchor_coverage=round(1-len(missing)/len(anchors),4) if anchors else None)
    return entry
