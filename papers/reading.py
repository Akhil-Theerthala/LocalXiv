"""Local paper orientation and selective evidence retrieval."""
import base64
import hashlib
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from papers.explanation import validate_selection
from papers.library import document_digest

REVISION = 'reading-v5-selective'

_BIB_HEADING = re.compile(r'^(?:(?:\d+(?:\.\d+)*|[IVX]+)[.)]?\s+)?(?:references|bibliography|works cited|literature cited)\s*[:.]?$', re.I)
_AFTER_BIB = re.compile(r'^(?:(?:\d+(?:\.\d+)*|[A-Z])[.)]?\s+)?(?:appendix|appendices|supplementary (?:material|information)|supplemental material|acknowledg(?:e)?ments)\b', re.I)


def evidence_document(document):
    """A non-mutating AI view. Keep source IDs, but exclude reference-list content."""
    root = Path(document.get('directory', '.')).resolve()
    excluded, loaded = {}, set()
    passages, in_pdf_bibliography = [], False
    for passage in document.get('passages', []):
        href = urlsplit(passage.get('href', ''))
        if document.get('format') == 'pdf' or href.path.lower().endswith('.pdf'):
            # ponytail: PDFKit has no section tree. Recognize explicit headings;
            # unmarked reference lists need richer PDF structure, not guessed cutoffs.
            text = passage.get('text', '')
            # A figure supplement can follow references without an Appendix heading.
            # PDFKit may put its caption before the title, so retain the whole page
            # when it has a figure/table caption and no numbered reference entries.
            if (in_pdf_bibliography and
                    re.search(r'^\s*(?:Figure|Fig\.|Table)\s+(?:[A-Z]\.?\d+|\d+)[.:]', text, re.M) and
                    not re.search(r'^\s*(?:\[\d+\]|\d+[.)])\s+\S', text, re.M)):
                in_pdf_bibliography = False
            kept = []
            for line in text.splitlines():
                heading = line.strip()
                if _BIB_HEADING.fullmatch(heading):
                    in_pdf_bibliography = True
                elif in_pdf_bibliography and (_AFTER_BIB.match(heading) or
                        re.match(r'^[A-Z](?:\.\d+)*[.)]?\s+(?:Proofs?|Additional|Implementation|Experimental|Derivation|Details)\b', heading)):
                    in_pdf_bibliography = False
                    kept.append(line)
                elif not in_pdf_bibliography:
                    kept.append(line)
            text = '\n'.join(kept).strip()
            if text:
                passages.append(dict(passage, text=text))
            continue
        source = (root / unquote(href.path)).resolve()
        if (not href.scheme and not href.netloc and source.is_relative_to(root / 'reader')
                and source.suffix == '.xhtml' and source not in loaded):
            loaded.add(source)
            try:
                tree = ET.parse(source)
            except (OSError, ET.ParseError):
                tree = None
            if tree is not None:
                bibliography_ids = set()
                def visit(element, bibliography=False):
                    markers = set((element.get('class', '') + ' ' + element.get('role', '') + ' ' +
                                   element.get('{http://www.idpf.org/2007/ops}type', '')).split())
                    bibliography = bibliography or bool(markers & {
                        'ltx_bibliography', 'ltx_biblist', 'ltx_bibitem', 'references',
                        'csl-bib-body', 'csl-entry', 'doc-bibliography', 'doc-biblioentry',
                        'bibliography', 'biblioentry'})
                    if bibliography and element.get('id'):
                        bibliography_ids.add(element.get('id'))
                    for child in element:
                        visit(child, bibliography)
                visit(tree.getroot())
                excluded[source] = bibliography_ids
        if (_BIB_HEADING.fullmatch(passage.get('section', '').strip()) or
                unquote(href.fragment) in excluded.get(source, set())):
            continue
        passages.append(passage)
    return dict(document, passages=passages)


def _xhtml_target(document, passage, trees):
    """Resolve a retained XHTML fragment without leaving the reader root."""
    root=Path(document.get('directory','.')).resolve()
    href=urlsplit(passage.get('href',''))
    source=(root/unquote(href.path)).resolve()
    if (href.scheme or href.netloc or not href.fragment or
            not source.is_relative_to(root/'reader') or source.suffix.lower()!='.xhtml'):
        return None,None,None
    try:
        if source not in trees:trees[source]=ET.parse(source)
    except (OSError,ET.ParseError):
        return source,None,None
    tree=trees[source]
    target=next((element for element in tree.iter() if element.get('id')==unquote(href.fragment)),None)
    parents={child:parent for parent in tree.iter() for child in parent}
    return source,target,parents


def _markers(element):
    if element is None:return set()
    values=' '.join(str(element.get(name,'')) for name in (
        'id','class','role','{http://www.idpf.org/2007/ops}type'))
    return {token.lower() for token in re.split(r'[^A-Za-z0-9_-]+',values) if token}


def _ancestors(element,parents):
    while element is not None:
        yield element
        element=parents.get(element) if parents else None


def _heading_level(title):
    match=re.match(r'^\s*((?:\d+\.)*\d+|[A-Z](?:\.\d+)*)[.)]?\s+',title or '')
    return len(match.group(1).split('.')) if match else None


def build_orientation(document):
    """Build a deterministic local source map without model calls or image reads."""
    identity=document_digest(document)
    filtered=evidence_document(document)
    passages=filtered.get('passages',[])
    trees={};abstract=[];ambiguous=[];figures=[]
    for passage in passages:
        _,target,parents=_xhtml_target(filtered,passage,trees)
        chain=list(_ancestors(target,parents)) if target is not None else []
        explicit=any('abstract' in _markers(element) or element.tag.split('}')[-1]=='abstract'
                     for element in chain)
        excluded=any(_markers(element)&{'author','authors','affiliation','license','copyright','center'}
                     for element in chain)
        first=next(iter(target),None) if target is not None else None
        labelled_note=(first is not None and first.tag.split('}')[-1] in ('em','strong') and
                       ''.join(first.itertext()).strip().lower().startswith(('author note','license','copyright')))
        if explicit and not excluded and not labelled_note:
            abstract.append({'passage':passage['id'],'text':passage.get('text','')})
        elif passage.get('section','').strip().lower()=='abstract' and target is None:
            ambiguous.append(passage['id'])

    sections=[];stack=[];last_title=None;last_structure=None;current=None;mapped_structures={}
    is_pdf=filtered.get('format')=='pdf' or any(urlsplit(p.get('href','')).path.lower().endswith('.pdf') for p in passages)
    for index,passage in enumerate(passages,1):
        title=(passage.get('section') or ('Page '+str(index))).strip()
        source,target,parents=_xhtml_target(filtered,passage,trees)
        containers=[]
        for element in _ancestors(target,parents) if target is not None else ():
            if element.tag.split('}')[-1] in ('section','article'):containers.append(element)
        containers.reverse()
        structure=(str(source),id(containers[-1])) if containers else None
        if is_pdf:
            title=title if title and title.lower() not in ('paper','document') else 'Page '+str(index)
            current=None
        elif current is not None and ((structure is not None and structure==last_structure) or
                                      (structure is None and last_structure is None and title==last_title)):
            current['passages'].append(passage['id']);current['chars']+=len(passage.get('text',''))
            continue
        level=_heading_level(title)
        structural_parent=next((mapped_structures[(str(source),id(element))]
                                for element in reversed(containers[:-1])
                                if (str(source),id(element)) in mapped_structures),None)
        if structural_parent is not None:
            parent=structural_parent
        elif level is None:
            parent=None;stack=[]
        else:
            while stack and stack[-1][0]>=level:stack.pop()
            parent=stack[-1][1] if stack else None
        section={'id':f's{len(sections)+1:04d}','title':title,'parent':parent,
                 'passages':[passage['id']],'chars':len(passage.get('text','')),
                 'is_appendix':bool(_AFTER_BIB.match(title) or re.match(r'^[A-Z](?:\.\d+)*[.)]?\s+',title))}
        sections.append(section);current=section;last_title=title;last_structure=structure
        if structure is not None:mapped_structures[structure]=section['id']
        if level is not None:stack.append((level,section['id']))

    for passage in passages:
        _,target,parents=_xhtml_target(filtered,passage,trees)
        located=None
        for element in _ancestors(target,parents) if target is not None else ():
            tag=element.tag.split('}')[-1]
            if tag in ('figure','table'):
                located=element;break
        kind=None
        if located is not None:
            kind='table' if located.tag.split('}')[-1]=='table' else 'figure'
        elif is_pdf and re.search(r'^\s*(?:Figure|Fig\.|Table)\s+[^\n:]{0,30}[.:]',passage.get('text',''),re.M|re.I):
            kind='table' if re.search(r'^\s*Table\s+',passage.get('text',''),re.M|re.I) else 'figure'
        if kind is None:continue
        section=next((item['id'] for item in sections if passage['id'] in item['passages']),None)
        text=' '.join(passage.get('text','').split())
        preview=text[:239]+'…' if len(text)>240 else text
        available=False
        if located is not None and kind=='figure':
            source,_,_=_xhtml_target(filtered,passage,trees)
            for image in (item for item in located.iter() if item.tag.split('}')[-1]=='img'):
                src=urlsplit(image.get('src',''));path=(source.parent/unquote(src.path)).resolve()
                if (not src.scheme and not src.netloc and path.is_relative_to(Path(filtered['directory']).resolve()/'reader')
                        and path.is_file()):
                    available=True;break
        figures.append({'id':f'f{len(figures)+1:04d}','passage':passage['id'],'section':section,
                        'kind':kind,'caption_preview':preview,'caption_truncated':len(text)>240,
                        'image_available':available})
    warnings=[]
    if ambiguous:warnings.append('Abstract structure is ambiguous at passages: '+', '.join(ambiguous))
    if not abstract and not ambiguous:warnings.append('No explicit abstract was identified.')
    if is_pdf and not figures:warnings.append('Original figure images are unavailable in the retained PDF text index.')
    return {'revision':REVISION,'document_digest':identity,'abstract':abstract,
            'abstract_status':'identified' if abstract else 'ambiguous' if ambiguous else 'unavailable',
            'abstract_candidates':ambiguous,
            'index_kind':'pages' if is_pdf and all(item['title'].startswith('Page ') for item in sections)
                         else 'mixed' if is_pdf else 'sections',
            'sections':sections,'figures':figures,'warnings':warnings}


def orientation_page(orientation,offset=0,limit=100):
    """Return an explicit, bounded page without changing the complete local orientation."""
    if type(offset) is not int or type(limit) is not int or offset<0 or not 1<=limit<=200:
        raise ValueError('Index offset must be nonnegative and limit must be 1-200.')
    figure_ids={section['id']:[] for section in orientation['sections']}
    for figure in orientation['figures']:
        figure_ids.setdefault(figure.get('section'),[]).append(figure['id'])
    entries=[{'entry_kind':'section',**{key:section[key] for key in ('id','title','parent','chars','is_appendix')},
              'figure_ids':figure_ids.get(section['id'],[])} for section in orientation['sections']]
    entries.extend({'entry_kind':figure['kind'],**{key:figure[key] for key in (
        'id','passage','section','caption_preview','caption_truncated','image_available')}}
        for figure in orientation['figures'])
    page=entries[offset:offset+limit];next_offset=offset+len(page)
    return {'revision':orientation['revision'],'document_digest':orientation['document_digest'],
            'abstract':orientation['abstract'],'abstract_status':orientation['abstract_status'],
            'abstract_candidates':orientation.get('abstract_candidates',[]),
            'index_kind':orientation['index_kind'],'entries':page,'offset':offset,
            'next_offset':next_offset if next_offset<len(entries) else None,'total':len(entries),
            'partial':offset>0 or next_offset<len(entries),'warnings':orientation['warnings']}


def _selected_image_bytes(document,passage):
    trees={};source,target,parents=_xhtml_target(document,passage,trees)
    if target is None:return [],'missing retained figure location'
    figure=next((item for item in _ancestors(target,parents)
                 if item.tag.split('}')[-1]=='figure'),None)
    if figure is None:return [],'selected source is not a raster figure'
    root=Path(document['directory']).resolve();images=[];problem='missing image asset'
    for element in figure.iter():
        if element.tag.split('}')[-1]!='img':continue
        src=urlsplit(element.get('src',''));path=(source.parent/unquote(src.path)).resolve()
        if src.scheme or src.netloc or not path.is_relative_to(root/'reader'):
            problem='external or unsafe image path';continue
        try:data=path.read_bytes()
        except OSError:continue
        mime='image/png' if data.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if data.startswith(b'\xff\xd8\xff') else None
        if not mime:problem='unsupported image format';continue
        if len(data)>2_000_000:problem='image exceeds 2 MB';continue
        images.append({'passage':passage['id'],'digest':hashlib.sha256(data).hexdigest(),
                       'url':'data:'+mime+';base64,'+base64.b64encode(data).decode()})
    return images,None if images else problem


def retrieve_evidence(document,orientation,selection,*,vision):
    """Resolve a validated selection and load only explicitly selected images."""
    if orientation.get('revision')!=REVISION or orientation.get('document_digest')!=document_digest(document):
        raise ValueError('Orientation does not match the retained paper and reading revision.')
    selection=validate_selection(selection,orientation)
    chosen_sections=set(selection['section_ids'])
    by_id={section['id']:section for section in orientation['sections']}
    def selected_section(section):
        current=section
        while current is not None:
            if current['id'] in chosen_sections:return True
            current=by_id.get(current.get('parent'))
        return False
    passage_ids=set(selection['passage_ids'])
    for section in orientation['sections']:
        if selected_section(section):passage_ids.update(section['passages'])
    figures={item['id']:item for item in orientation['figures']}
    passage_ids.update(figures[item]['passage'] for item in selection['figure_ids'])
    filtered=evidence_document(document)
    passages=[copy for copy in filtered.get('passages',[]) if copy['id'] in passage_ids]
    images=[];unavailable=[];attached_ids=[]
    if vision:
        passage_map={passage['id']:passage for passage in passages}
        for figure_id in selection['figure_ids']:
            found,reason=_selected_image_bytes(filtered,passage_map[figures[figure_id]['passage']])
            if reason:unavailable.append({'figure_id':figure_id,'reason':reason})
            for image in found:
                if len(images)>=6:
                    unavailable.append({'figure_id':figure_id,'reason':'six-image attachment limit'})
                    break
                images.append(image)
                if figure_id not in attached_ids:attached_ids.append(figure_id)
    else:
        unavailable.extend({'figure_id':figure_id,'reason':'vision disabled'} for figure_id in selection['figure_ids'])
    return {'document_digest':orientation['document_digest'],'passages':passages,'images':images,
            'coverage':{'available_section_ids':[item['id'] for item in orientation['sections']],
                        'available_passage_ids':[pid for item in orientation['sections'] for pid in item['passages']],
                        'available_figure_ids':[item['id'] for item in orientation['figures']],
                        'requested_section_ids':selection['section_ids'],
                        'requested_passage_ids':selection['passage_ids'],
                        'requested_figure_ids':selection['figure_ids'],
                        'retrieved_passage_ids':[item['id'] for item in passages],
                        'attached_image_ids':attached_ids,
                        'attached_image_digests':[item['digest'] for item in images],
                        'unavailable_images':unavailable}}
