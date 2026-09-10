"""Select and validate Paper exports; format implementations stay behind this module."""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from papers.overview import clean_citations


def figure_source(directory, figure, extension):
    relative = figure.get(extension)
    if not isinstance(relative, str) or not relative:
        raise ValueError('The requested figure export is unavailable.')
    source = (directory / relative).resolve()
    if not source.is_relative_to(directory.resolve() / 'reader' / 'overview-figures') or source.suffix != '.' + extension:
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
    target = directory / ('overview.pdf' if kind == 'bento' else 'blog.pdf')
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        work = Path(temporary)
        candidate = work / 'export.pdf'
        if kind == 'bento':
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
            text = clean_citations(generation['text'])
            for i, figure in enumerate(generation.get('figures', [])):
                image = work / f'figure-{i}.png'
                if figure.get('png'):
                    shutil.copyfile(figure_source(directory, figure, 'png'), image)
                else:
                    subprocess.run(['rsvg-convert', '-o', str(image), str(figure_source(directory, figure, 'svg'))], check=True, capture_output=True, timeout=60)
                text = text.replace('{{figure:' + figure['id'] + '}}', f'\n\n![]({image.name})\n\n' + figure.get('caption', ''))
            # Model Markdown cannot request local files or remote images during PDF rendering.
            parsed = subprocess.run(['pandoc', '--from=markdown-raw_html-raw_tex', '--to=json'], input=text, text=True, capture_output=True, check=True, timeout=30)
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


def artifact(library, paper, kind, profile):
    if kind not in ('paper', 'overview', 'bento', 'both') or profile not in ('kindle', 'semantic', 'pdf', 'png'):
        raise ValueError('Unknown Paper export kind or profile.')
    directory = Path(paper['directory'])
    if profile == 'pdf':
        generation = library.get_generation(paper['id'], 'bento' if kind == 'bento' else 'overview')
        return export_pdf(directory, paper, kind, generation)
    if profile == 'png':
        if kind != 'bento':
            raise ValueError('PNG export is only available for the bento overview.')
        generation = library.get_generation(paper['id'], 'bento')
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
        from papers.document import export_overview
        overview = library.get_generation(paper['id'], 'bento' if kind == 'bento' else 'overview')
        if not overview:
            raise ValueError('Generate the requested overview or blog before exporting or sending it.')
        artifact = export_overview(directory, paper, overview, **({'visual': True} if kind == 'bento' else {}))
        if profile == 'semantic':
            name = 'bento' if kind == 'bento' else 'overview'
            artifact = directory / (name + '-semantic.epub')
            shutil.copyfile(directory / (name + '-export') / 'semantic.epub', artifact)
        if kind == 'both':
            from native.host import build_anthology, PaperMetadata
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
