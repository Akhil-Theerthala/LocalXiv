"""Private conversion worker. Invoked only through papers.convert."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from native import host
from papers.document import build_document, numeric_latexml


def omit_unused_filler(source: Path) -> int:
    """Avoid loading lorem-ipsum machinery only when no source command uses it."""
    paths = list(source.rglob('*.tex'))
    documents = [(p, host._read_tex_preserving_bytes(p)) for p in paths]
    active = '\n'.join(host._searchable_tex_source(text) for _, text in documents)
    if re.search(r'\\[A-Za-z@]*lipsum[A-Za-z@]*', active, re.I):
        return 0
    count = 0
    pattern = re.compile(r'\\usepackage\s*\{lipsum\}')
    for path, text in documents:
        searchable = host._searchable_tex_source(text)
        matches = list(pattern.finditer(searchable))
        for match in reversed(matches):
            # Preserve offsets and line endings; no paper wording is rewritten.
            text = text[:match.start()] + ' ' * len(match[0]) + text[match.end():]
        if matches:
            host._write_tex_preserving_bytes(path, text)
            count += len(matches)
    return count


def graphic(source: Path, output: Path):
    if source.suffix.lower() in {'.pdf', '.eps', '.ps'}:
        command = ['gs','-dSAFER','-dBATCH','-dNOPAUSE','-sDEVICE=pngalpha','-r180',
                   '-dFirstPage=1','-dLastPage=1', '-dEPSCrop' if source.suffix.lower()=='.eps' else '-dUseCropBox',
                   '-sOutputFile='+str(output),str(source)]
    elif source.suffix.lower()=='.svg':
        command = ['rsvg-convert','-o',str(output),str(source)]
    else:
        command = ['/usr/bin/sips','-s','format','png',str(source),'--out',str(output)]
    subprocess.run(command,check=True,capture_output=True,timeout=30)


def run(command, cwd, log, timeout=300):
    with log.open('w') as output:
        result = subprocess.run(command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
    if result.returncode:
        raise ValueError(log.read_text(errors='replace')[-1800:])
    return log.read_text(errors='replace')


def latexml(source: Path, root: Path, directory: Path):
    omitted = omit_unused_filler(source)
    if omitted:
        print(f'PROGRESS Skipped {omitted} unused lorem-ipsum package import.', flush=True)
    host.prepare_graphics(source, converter=graphic, compilation_dir=root.parent)
    xml = directory / 'paper.xml'
    # Long math-heavy papers need time under ordinary CPU contention. The
    # parent still enforces aggregate memory, CPU, and wall-clock limits.
    log = run(['latexml', '--dest='+str(xml), str(root)], root.parent, directory / 'latexml.log', timeout=180)
    if re.search(r'(?:Fatal|Error):|\d+ errors?\b', log):
        raise ValueError('LaTeXML reported source errors: ' + log[-1200:])
    xml.write_bytes(numeric_latexml(xml.read_bytes()))
    reader = directory / 'reader'
    reader.mkdir()
    # Structured XML retains citation roles and all source sections before packaging.
    log = run(['latexmlpost', '--format=xhtml', '--stylesheet=LaTeXML-epub3.xsl', '--pmml', '--dest='+str(reader / 'main.xhtml'), str(xml)],
              root.parent, directory / 'latexmlpost.log')
    if re.search(r'(?:Fatal|Error):|\d+ errors?\b', log):
        raise ValueError('LaTeXML reported unresolved output: ' + log[-1200:])


def pandoc(source: Path, root: Path, directory: Path):
    def rasterize(svg, png, **_):
        subprocess.run(['rsvg-convert','-w','1200','-h','1600','-o',str(png),str(svg)], check=True, capture_output=True, timeout=30)
    # Keep Quick Look and its GUI services outside the isolated conversion process.
    host.rasterize_cover = rasterize
    host._convert_graphic_to_png = graphic
    host.convert_source(source, json.loads((directory.parent / 'metadata.json').read_text())['arxiv_id'], directory / 'legacy.epub', numeric_citations=True)
    reader = directory / 'reader'
    reader.mkdir()
    with zipfile.ZipFile(directory / 'legacy.epub') as book:
        container = ET.fromstring(book.read('META-INF/container.xml'))
        opf_name = container.find('.//{*}rootfile').get('full-path')
        opf = ET.fromstring(book.read(opf_name))
        base = Path(opf_name).parent
        items = {e.get('id'):e for e in opf.findall('.//{*}manifest/{*}item')}
        order = []
        for e in opf.findall('.//{*}spine/{*}itemref'):
            item = items[e.get('idref')]
            href = item.get('href')
            if href.endswith('cover.xhtml') or 'nav' in item.get('properties','').split(): continue
            order.append(href)
        for item in items.values():
            href = item.get('href')
            path = reader / href
            if not path.resolve().is_relative_to(reader.resolve()):
                raise ValueError('The EPUB contains an unsafe resource path.')
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(book.read(str(base / href)))
        (reader / 'spine.json').write_text(json.dumps(order))


def main():
    directory = Path(sys.argv[1]).resolve()
    metadata = json.loads((directory / 'metadata.json').read_text())
    if '--pdf' in sys.argv[2:]:
        from papers.pdf import build_pdf_document
        print('PROGRESS Reading the original PDF.', flush=True)
        build_pdf_document(directory, metadata)
        print('PROGRESS PDF ready.', flush=True)
        return 0
    attempts = []
    # The corpus exposed TeX Live 2026 incompatibilities in LaTeXML 0.8.8.
    # Keep the faster established reader first, with independent source fallback.
    for engine, function in [('pandoc',pandoc), ('latexml',latexml)]:
        attempt = directory / engine
        if attempt.exists():
            shutil.rmtree(attempt)
        attempt.mkdir(exist_ok=True)
        source = attempt / 'source'
        try:
            print(f'PROGRESS Converting with {engine}.', flush=True)
            host.extract_source(directory / 'source', source)
            root = host.find_root_tex(source)
            function(source, root, attempt)
            print('PROGRESS Checking content and drawing Kindle equations.', flush=True)
            completed = [*attempts, {'engine':engine, 'status':'converted'}]
            document = build_document(attempt, metadata, engine, {'attempts':completed})
            for name in ['reader','paper.epub','semantic.epub','document.json']:
                previous = directory / name
                if previous.is_dir():
                    shutil.rmtree(previous)
                elif previous.exists():
                    previous.unlink()
                shutil.move(str(attempt / name), str(directory / name))
            (directory / 'conversion-report.json').write_text(json.dumps(document['report'], indent=2))
            print('PROGRESS Paper ready.', flush=True)
            return 0
        except Exception as error:
            attempts.append({'engine':engine, 'status':'failed', 'error':str(error)[-2000:]})
            (directory / 'conversion-report.json').write_text(json.dumps({'attempts':attempts},indent=2))
            print(f'{engine}: {str(error)[-1600:]}', flush=True)
    print('Neither source converter produced a validated paper. The original files and conversion report are retained.', flush=True)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
