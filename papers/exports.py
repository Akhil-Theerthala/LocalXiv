"""Select and validate Paper exports; format implementations stay behind this module."""
import html
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from native.host import PaperMetadata, build_anthology
from papers.document import XHTML, build_document
from papers.passages import Passages


def pdf_math_macros(text):
    """Rewrite math macros the reader's MathJax accepts but the pandoc/XeLaTeX pipeline does not.

    ``\bm`` needs the bm package, which conflicts with pandoc's default Unicode math setup, so a
    Blog that uses it fails PDF export with "Undefined control sequence". ``\boldsymbol`` is
    provided by amsmath and renders identically. The saved article text is not modified.
    """
    return re.sub(r'\\bm(?![A-Za-z])', r'\\boldsymbol', text)


def figure_source(directory, figure, extension, *, field=None):
    key=field or extension
    relative = figure.get(key)
    if not isinstance(relative, str) or not relative:
        raise ValueError('The requested figure export is unavailable.')
    source = (directory / relative).resolve()
    valid_suffix=(source.name.endswith('.source.svg') if key=='svg_source' else
                  source.suffix=='.'+extension)
    if not source.is_relative_to(directory.resolve() / 'reader' / 'overview-figures') or not valid_suffix:
        raise ValueError('Invalid figure export path.')
    if not source.is_file():
        raise ValueError('The requested figure export is unavailable.')
    return source


def export_pdf(directory, paper, kind, generation):
    if kind == 'paper':
        source = directory / 'original.pdf'
        if not source.is_file() or not source.read_bytes().startswith(b'%PDF-'):
            raise ValueError('The original PDF is unavailable. Retry importing this paper.')
        return source
    if kind == 'both':
        raise ValueError('Download the original paper and blog PDFs separately.')
    if not generation:
        raise ValueError('Generate the requested overview or blog before exporting it.')
    target = directory / ('overview.pdf' if kind == 'overview' else 'blog.pdf')
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        work = Path(temporary)
        candidate = work / 'export.pdf'
        if kind == 'overview':
            if not generation.get('figures'):
                raise ValueError('Generate a visual overview before exporting it.')
            figure = generation['figures'][0]
            if figure.get('pdf'):
                source = figure_source(directory, figure, 'pdf')
                if not source.read_bytes().startswith(b'%PDF-'):
                    raise ValueError('Overview PDF is invalid.')
                shutil.copyfile(source, candidate)
                candidate.replace(target)
                return target
            source = figure_source(directory, figure, 'svg')
            command = ['rsvg-convert', '--format=pdf', '-o', str(candidate), str(source)]
        else:
            xelatex = shutil.which('xelatex')
            if not xelatex and Path('/Library/TeX/texbin/xelatex').is_file():
                xelatex = '/Library/TeX/texbin/xelatex'
            if not xelatex:
                raise ValueError('Blog PDF export requires XeLaTeX. Install MacTeX, then restart LocalXiv.')
            text = pdf_math_macros(Passages.uncited(generation['text']))
            for i, figure in enumerate(generation.get('figures', [])):
                image = work / f'figure-{i}.png'
                if figure.get('png'):
                    shutil.copyfile(figure_source(directory, figure, 'png'), image)
                else:
                    subprocess.run(['rsvg-convert', '-o', str(image), str(figure_source(directory, figure, 'svg'))],
                                   check=True, capture_output=True, timeout=60)
                text = text.replace('{{figure:' + figure['id'] + '}}',
                                     f'\n\n![]({image.name})\n\n' + figure.get('caption', ''))
            # Model Markdown cannot request local files or remote images during PDF rendering.
            parsed = subprocess.run(['pandoc', '--from=markdown-raw_html-raw_tex', '--to=json'], input=text,
                                    text=True, capture_output=True, check=True, timeout=30)
            tree = json.loads(parsed.stdout)
            allowed = {f'figure-{i}.png' for i in range(len(generation.get('figures', [])))}
            def restrict_images(value):
                if isinstance(value, dict):
                    if value.get('t') == 'Image' and value['c'][2][0] not in allowed:
                        value.clear()
                        value.update(t='Str', c='[External image omitted]')
                    for child in value.values():
                        restrict_images(child)
                elif isinstance(value, list):
                    for child in value:
                        restrict_images(child)
            restrict_images(tree)
            markdown = work / 'blog.json'
            markdown.write_text(json.dumps(tree))
            command = ['pandoc', str(markdown), '--from=json', '--standalone',
                       '--pdf-engine=' + xelatex, '--pdf-engine-opt=-no-shell-escape',
                       '-V', 'geometry:margin=25mm', '-o', str(candidate)]
        result = subprocess.run(command, cwd=work, capture_output=True, text=True, timeout=120)
        if result.returncode or not candidate.is_file() or not candidate.read_bytes().startswith(b'%PDF-'):
            raise ValueError('PDF export failed: ' + result.stderr[-1200:])
        candidate.replace(target)
    return target


def export_overview(directory: Path, document: dict, overview: dict, *, visual=False) -> Path:
    name = 'overview' if visual else 'blog'
    work = directory / (name + '-export')
    reader = work / 'reader'
    reader.mkdir(parents=True, exist_ok=True)
    # Pandoc reads generated Markdown here, never arbitrary TeX from the paper.
    text = Passages.uncited(overview['text'])
    figure_html = {}
    for extension in ('svg', 'png'):
        for old_figure in reader.glob('fig[0-9]*.' + extension):
            old_figure.unlink()
    for figure in overview.get('figures', []):
        identifier = figure.get('id', '')
        if not re.fullmatch(r'fig\d+', identifier):
            raise ValueError('Invalid overview figure identifier.')
        # Older saved overviews may only have a PNG.
        source = figure_source(directory, figure, 'svg' if figure.get('svg') else 'png')
        filename = identifier + source.suffix
        shutil.copyfile(source, reader / filename)
        marker = 'OVERVIEWFIGURE' + identifier.upper()
        text = text.replace('{{figure:' + identifier + '}}', marker)
        figure_html[marker] = ('<figure><img src="' + filename + '" alt="' +
                                html.escape(figure.get('alt', ''), quote=True) + '"/><figcaption>' +
                                html.escape(figure.get('caption', '')) + '</figcaption></figure>')
    result = subprocess.run(['pandoc','--from=markdown-raw_html-raw_tex','--to=html5','--mathml'], input=text,
                            text=True, capture_output=True, timeout=30, check=True)
    body = result.stdout
    for marker, rendered in figure_html.items():
        body = body.replace("<p>" + marker + "</p>", rendered)
    title = ('Overview: ' if visual else 'Blog: ') + document['title']
    provenance = overview.get('provenance', {})
    attribution = ' · '.join(str(value) for value in (provenance.get('model'), provenance.get('created_at')) if value)
    attribution = f'<p>{html.escape(attribution)}</p>' if attribution else ''
    (reader / 'main.xhtml').write_text(
        f'<html xmlns="{XHTML}"><head><title>{html.escape(title)}</title></head>'
        f'<body><h1>{html.escape(title)}</h1><p>Generated explanation of arXiv '
        f'{html.escape(document["arxiv_id"])}. Read the '
        f'<a href="https://arxiv.org/abs/{html.escape(document["arxiv_id"], quote=True)}">original paper</a> '
        f'for the complete evidence.</p>{attribution}{body}</body></html>')
    build_document(work, {**document, 'title':title}, 'overview')
    shutil.copyfile(work / 'paper.epub', directory / (name + '.epub'))
    return directory / (name + '.epub')


def artifact(library, paper, kind, profile):
    if kind not in ('paper', 'overview', 'blog', 'both') or profile not in ('kindle', 'semantic', 'pdf', 'png'):
        raise ValueError('Unknown Paper export kind or profile.')
    directory = Path(paper['directory'])
    if profile == 'pdf':
        generation = library.get_generation(paper['id'], 'blog' if kind == 'both' else kind)
        return export_pdf(directory, paper, kind, generation)
    if profile == 'png':
        if kind != 'overview':
            raise ValueError('PNG export is only available for the Overview.')
        generation = library.get_generation(paper['id'], 'overview')
        if not generation or not generation.get('figures'):
            raise ValueError('Generate a visual overview before exporting it.')
        return figure_source(directory, generation['figures'][0], 'png')
    original = directory / ('semantic.epub' if profile == 'semantic' else 'paper.epub')
    if paper.get('format') == 'pdf':
        original = directory / 'original.pdf'
        if kind == 'both':
            raise ValueError('This paper is a PDF. Download or send the paper PDF and blog EPUB separately.')
        if kind == 'paper':
            return export_pdf(directory, paper, kind, None)
    if kind == 'paper':
        artifact = original
    else:
        overview = library.get_generation(paper['id'], 'blog' if kind == 'both' else kind)
        if not overview:
            raise ValueError('Generate the requested overview or blog before exporting or sending it.')
        artifact = export_overview(directory, paper, overview, visual=kind == 'overview')
        if profile == 'semantic':
            name = 'overview' if kind == 'overview' else 'blog'
            artifact = directory / (name + '-semantic.epub')
            shutil.copyfile(directory / (name + '-export') / 'semantic.epub', artifact)
        if kind == 'both':
            overview_metadata = PaperMetadata(paper['title'] + ' — Blog', paper['authors'], paper['arxiv_id'])
            metadata = PaperMetadata(paper['title'], paper['authors'], paper['arxiv_id'])
            combined = directory / ('combined-semantic.epub' if profile == 'semantic' else 'combined.epub')
            candidate = directory / ('.' + combined.name)
            try:
                build_anthology([(overview_metadata, artifact), (metadata, original)], paper['title'], candidate)
                if not shutil.which('epubcheck'):
                    raise ValueError('Install EPUBCheck to validate the combined book.')
                check = subprocess.run(['epubcheck', str(candidate)], capture_output=True, text=True, timeout=120)
                combined.with_suffix('.epubcheck.log').write_text(check.stdout + check.stderr)
                if check.returncode:
                    raise ValueError('Combined EPUB validation failed: ' + (check.stdout + check.stderr)[-1800:])
                candidate.replace(combined)
            finally:
                candidate.unlink(missing_ok=True)
            artifact = combined
    if not artifact.is_file():
        raise ValueError('The requested file is unavailable. Retry importing the paper.')
    return artifact
