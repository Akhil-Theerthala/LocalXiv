#!/usr/bin/env python3
"""Check a moved app, isolated service, and real sandboxed EPUB conversion."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.request
import zipfile


def verify(app, move=True):
    app = app.resolve()
    with tempfile.TemporaryDirectory(prefix='LocalXiv release check ') as temp:
        work = Path(temp)
        if move:
            target = work / 'Moved app' / app.name
            target.parent.mkdir()
            shutil.copytree(app, target, symlinks=True)
            app = target
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
        code = app / 'Contents/Resources/app'
        runtime = app / 'Contents/Resources/runtime'
        home = work / 'home'
        home.mkdir()
        library = work / 'library'
        env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': str(home), 'TMPDIR': str(work), 'LANG': 'en_US.UTF-8',
               'PYTHONDONTWRITEBYTECODE': '1'}
        denied = ['/opt/homebrew', '/usr/local', str(Path.home() / '.nvm')]
        profile = '(version 1)(allow default)(deny file-read* ' + ' '.join('(subpath ' + json.dumps(p) + ')' for p in denied) + ')'
        isolated = ['/usr/bin/sandbox-exec', '-p', profile]
        log = work / 'service.log'
        with log.open('w') as stream:
            service = subprocess.Popen(isolated + ['/bin/bash', str(code / 'launch.command'), '--serve', '--port', '0',
                                        '--data-dir', str(library)], env=env, stdout=stream, stderr=stream)
        try:
            # A fresh macOS runner can spend longer loading the signed runtime.
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                session_file = library / 'session.json'
                if session_file.exists():
                    session = json.loads(session_file.read_text())
                    break
                if service.poll() is not None:
                    raise RuntimeError(log.read_text())
                time.sleep(0.1)
            else:
                raise RuntimeError('Timed out after 120 seconds starting bundled service: ' + log.read_text())
            base = f'http://127.0.0.1:{session["port"]}'
            request = urllib.request.Request(base + '/api/health', headers={'Authorization': 'Bearer ' + session['token']})
            with urllib.request.urlopen(request, timeout=5) as response:
                health = json.load(response)
            assert health['application'] == 'papers-to-kindle', health
            with urllib.request.urlopen(base + '/', timeout=5) as response:
                assert b'LocalXiv' in response.read()
            print('Moved bundled service and reader HTTP checks passed.', flush=True)
        finally:
            service.terminate()
            try:
                service.wait(timeout=10)
            except subprocess.TimeoutExpired:
                service.kill()
                service.wait()
        paper = work / 'paper'
        paper.mkdir()
        source = work / 'source'
        source.mkdir()
        (source / 'main.tex').write_text(r'''\documentclass{article}
\title{Portable LocalXiv Check}\author{LocalXiv}
\begin{document}\maketitle
\begin{abstract}A local packaging check with no external services.\end{abstract}
\section{Method}The equation $x^2+1$ must remain readable. See \cite{test}.
\begin{equation} y = \frac{1}{2} \end{equation}
\begin{thebibliography}{1}\bibitem{test} A reference. 2026.\end{thebibliography}
\end{document}''')
        with tarfile.open(paper / 'source', 'w:gz') as archive:
            archive.add(source / 'main.tex', arcname='main.tex')
        command = '''import json, sys, subprocess
from pathlib import Path
from papers import convert
original_profile = convert.sandbox_profile
denial = '(deny file-read* ' + ' '.join('(subpath ' + json.dumps(p) + ')' for p in json.loads(sys.argv[2])) + ')'
convert.sandbox_profile = lambda work, app: original_profile(work, app) + denial
result = convert.convert_paper(Path(sys.argv[1]), {'arxiv_id':'2601.00001v1', 'title':'Portable LocalXiv Check', 'authors':'LocalXiv'})
import shutil
latexml = Path(sys.argv[1]) / 'latexml-check'
latexml.mkdir()
shutil.copy2(Path(sys.argv[1]) / 'source', latexml / 'source')
alternate = convert.convert_paper(latexml, {'arxiv_id':'2601.00003v1', 'title':'LaTeXML check', 'authors':'LocalXiv'}, source_engine='latexml')
assert alternate['converter'] == 'latexml' and alternate['passages']
from papers.overview import render_figure
figure = render_figure(Path(sys.argv[1]), 'check', {'title':'Portable renderer', 'takeaway':'The renderer works inside the bundled app.', 'scope':'Local packaging check.', 'layout':'comparison', 'focus':0, 'arrows':[], 'nodes':[{'title':'Input', 'body':'A small diagram specification.'}, {'title':'Output', 'body':'An SVG figure.'}]})
import xml.etree.ElementTree as ET
assert ET.parse(Path(sys.argv[1]) / figure['svg']).getroot().tag == '{http://www.w3.org/2000/svg}svg'
pdf = Path(sys.argv[1]).parent / 'pdf'
pdf.mkdir()
subprocess.run(['gs', '-q', '-dBATCH', '-dNOPAUSE', '-sDEVICE=pdfwrite', '-sOutputFile='+str(pdf/'original.pdf'), '-c', '/Helvetica findfont 12 scalefont setfont 20 20 moveto (LocalXiv PDF check) show showpage'], check=True, capture_output=True)
document = convert.convert_paper(pdf, {'arxiv_id':'2601.00002v1', 'title':'PDF check', 'authors':'LocalXiv'}, pdf_only=True)
assert document['format'] == 'pdf' and document['passages']
print(json.dumps(result, default=str))
'''
        # No inherited Python/Homebrew/nvm environment. The bundled wrapper
        # supplies Python's own prefix and CA roots.
        env['PATH'] = str(runtime / 'bin') + ':' + env['PATH']
        env['PYTHONPATH'] = str(code)
        # The supervisor must invoke macOS's setuid ps for its memory limit;
        # Seatbelt forbids that under an outer sandbox. Deny developer paths
        # inside the existing conversion-worker sandbox instead.
        result = subprocess.run([str(runtime / 'bin/python3'), '-c', command, str(paper), json.dumps(denied)],
                                cwd=code, env=env, capture_output=True, text=True, timeout=700)
        if result.returncode:
            raise RuntimeError('Bundled conversion failed:\n' + result.stdout + result.stderr)
        books = list(paper.rglob('*.epub'))
        if len(books) < 2:
            raise RuntimeError('Expected semantic and Kindle EPUBs. ' + result.stdout)
        for book in books:
            with zipfile.ZipFile(book) as archive:
                assert archive.testzip() is None
        print('Sandboxed conversion and EPUB validation passed: ' + ', '.join(p.name for p in books), flush=True)
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
        return {'moved_app': move, 'service': 'passed', 'sandboxed_epub_conversion': 'passed',
                'latexml_conversion': 'passed',
                'pdf_text_extraction': 'passed', 'overview_figure_rendering': 'passed',
                'clean_machine': 'not tested', 'mail_delivery': 'not tested', 'live_ai': 'not tested'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app', type=Path)
    parser.add_argument('--in-place', action='store_true', help='Skip copying the app to a path containing spaces')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = verify(args.app, move=not args.in_place)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n')
