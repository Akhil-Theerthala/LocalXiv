#!/usr/bin/env python3
"""Build a relocatable macOS runtime from installed Homebrew tools.

This is an Apple Silicon/macOS 26 release builder, not a cross compiler.
Third-party notices are collected; their corresponding-source obligations
must be fulfilled separately before publishing a release.
"""
import argparse
import json
import hashlib
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import zipfile

FORMULAE = ('python@3.14', 'pandoc', 'latexml', 'librsvg', 'ghostscript', 'epubcheck', 'openjdk')
JAVA_MODULES = 'java.base,java.compiler,java.desktop,java.security.jgss,java.sql,jdk.unsupported,jdk.xml.dom'
MAGIC = {b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca'}


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT).strip()


def macho(path):
    if path.is_symlink() or not path.is_file():
        return False
    with path.open('rb') as stream:
        return stream.read(4) in MAGIC


def files(root):
    for directory, _, names in os.walk(root):
        for name in names:
            yield Path(directory) / name


def bundle(output):
    output = Path(output).resolve()
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise RuntimeError('Build on an Apple Silicon Mac running macOS 26 or later.')
    if int(platform.mac_ver()[0].split('.')[0]) < 26:
        raise RuntimeError('This runtime currently targets macOS 26 or later.')
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f'Refusing to overwrite nonempty runtime: {output}')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'bin').mkdir()
    roots = {name: Path(run('brew', '--prefix', name)).resolve() for name in FORMULAE}
    mapping = {}
    origins = {}
    manifests = []

    def record_license(source):
        # Homebrew Cellar paths identify the exact installed formula version.
        parts = source.parts
        if 'Cellar' not in parts:
            return
        index = parts.index('Cellar')
        root = Path(*parts[:index + 3])
        name, version = parts[index + 1:index + 3]
        if any(entry['name'] == name for entry in manifests):
            return
        dest = output / 'licenses' / name
        dest.mkdir(parents=True, exist_ok=True)
        for item in root.iterdir():
            if item.is_file() and (item.name.upper().startswith(('LICENSE', 'COPYING', 'NOTICE', 'AUTHORS')) or item.name in ('INSTALL_RECEIPT.json', 'sbom.spdx.json')):
                shutil.copy2(item, dest / item.name)
        manifests.append({'name': name, 'version': version})

    for name, root in roots.items():
        dest = output / 'vendor' / name
        record_license(root)
        if name == 'openjdk':
            # Keep EPUBCheck and its image/XML support without shipping a development kit.
            root = root / 'libexec/openjdk.jdk/Contents/Home'
            run(str(root / 'bin/jlink'), '--add-modules', JAVA_MODULES, '--strip-debug',
                '--no-header-files', '--no-man-pages', '--compress=zip-6', '--output', str(dest))
        else:
            def omit(directory, names):
                relative = Path(directory).relative_to(root).as_posix()
                ignored = set(shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store')(directory, names))
                if name == 'ghostscript':
                    if relative == '.':
                        ignored.update({'lib', 'include'})
                    elif relative == 'bin':
                        ignored.update(set(names) - {'gs'})
                if name == 'python@3.14' and relative == 'Frameworks/Python.framework/Versions/3.14/lib/python3.14':
                    ignored.add('test')
                return ignored
            shutil.copytree(root, dest, symlinks=True, ignore=omit)
        mapping[root] = dest
        for item in files(dest):
            if not item.is_symlink():
                origins[item] = root / item.relative_to(dest)

    def mapped(source):
        source = source.resolve()
        for root, dest in mapping.items():
            if source.is_relative_to(root):
                target = dest / source.relative_to(root)
                if target.exists():
                    return target
        return None

    # Make every symlink relative and self-contained. Python's Homebrew
    # site-packages link intentionally becomes an empty directory.
    for directory, dirs, names in os.walk(output / 'vendor'):
        for name in dirs + names:
            item = Path(directory) / name
            if not item.is_symlink():
                continue
            vendor = next(dest for dest in mapping.values() if item.is_relative_to(dest))
            root = next(root for root, dest in mapping.items() if dest == vendor)
            source = root / item.relative_to(vendor)
            target = source.resolve()
            destination = mapped(target)
            if not os.path.isabs(os.readlink(source)) and destination is not None:
                # Framework signatures require their canonical Versions/Current links.
                continue
            item.unlink()
            if item.name == 'site-packages':
                item.mkdir()
            elif destination is not None:
                item.symlink_to(os.path.relpath(destination, item.parent))
            elif target.is_dir():
                shutil.copytree(target, item, symlinks=False)
                for child in files(item):
                    origins[child] = target / child.relative_to(item)
            elif target.is_file():
                shutil.copy2(target, item)
                origins[item] = target
            else:
                raise RuntimeError(f'Unresolved runtime symlink: {source}')

    node = Path(shutil.which('node') or '').resolve()
    if not node.is_file():
        raise RuntimeError('Install Node.js before building.')
    bundled_node = output / 'vendor' / 'node' / 'bin' / 'node'
    bundled_node.parent.mkdir(parents=True)
    shutil.copy2(node, bundled_node)
    origins[bundled_node] = node
    node_notice = node.parent.parent / 'LICENSE'
    if node_notice.exists():
        shutil.copy2(node_notice, output / 'licenses' / 'NODE-LICENSE')
    else:
        # Official Node embeds its full dependency notices in the executable.
        (output / 'licenses' / 'NODE-LICENSE').write_text(run(str(node), '--license') + '\n')
    manifests.append({'name': 'node', 'version': run(str(node), '--version')})

    def dependency(source, reference):
        if reference.startswith('/'):
            return Path(reference).resolve()
        expanded = reference.replace('@loader_path', str(source.parent)).replace('@executable_path', str(source.parent))
        if not expanded.startswith('@rpath/'):
            return Path(expanded).resolve()
        commands = run('otool', '-l', str(source))
        for entry in re.findall(r'cmd LC_RPATH\s+cmdsize \d+\s+path (.*?) \(offset', commands):
            entry = entry.replace('@loader_path', str(source.parent)).replace('@executable_path', str(source.parent))
            candidate = Path(entry) / reference.removeprefix('@rpath/')
            if candidate.exists():
                return candidate.resolve()
        raise RuntimeError(f'Cannot resolve {reference} in {source}')

    pending = [item for item in origins if macho(item)]
    visited = set()
    while pending:
        item = pending.pop()
        if item in visited:
            continue
        visited.add(item)
        source = origins[item]
        item.chmod(item.stat().st_mode | 0o200)
        edits = []
        for line in run('otool', '-L', str(source)).splitlines()[1:]:
            reference = line.strip().split(' (compatibility')[0]
            if reference.startswith(('/usr/lib/', '/System/Library/')):
                continue
            original = dependency(source, reference)
            if original == source.resolve():
                edits.extend(['-id', '@loader_path/' + item.name])
                continue
            target = mapped(original)
            if target is None:
                # Mirror absolute library paths beneath runtime/lib to avoid
                # collisions between identically named libraries.
                target = output / 'lib' / str(original).lstrip('/')
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(original, target)
                    origins[target] = original
                    pending.append(target)
                    record_license(original)
            edits.extend(['-change', reference, '@loader_path/' + os.path.relpath(target, item.parent)])
        for rpath in re.findall(r'cmd LC_RPATH\s+cmdsize \d+\s+path (.*?) \(offset', run('otool', '-l', str(source))):
            if rpath.startswith('/') and not rpath.startswith(('/usr/lib/', '/System/Library/')):
                edits.extend(['-delete_rpath', rpath])
        if edits:
            run('install_name_tool', *edits, str(item))
        # Relocation invalidates signatures. Ad hoc signing permits the smoke
        # check; the release builder subsequently signs with Developer ID.
        run('codesign', '--force', '--sign', '-', str(item))

    containers = [Path(directory) for directory, _, _ in os.walk(output) if directory.endswith(('.app', '.framework', '.jdk'))]
    for container in sorted(containers, key=lambda path: len(path.parts), reverse=True):
        run('codesign', '--force', '--sign', '-', str(container))

    def wrapper(name, command, environment=''):
        path = output / 'bin' / name
        path.write_text('#!/bin/sh\nset -eu\nR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"\n' + environment + '\nexec ' + command + ' "$@"\n')
        path.chmod(0o755)

    pyhome = 'vendor/python@3.14/Frameworks/Python.framework/Versions/3.14'
    ca_root = Path(run('brew', '--prefix', 'ca-certificates')).resolve()
    cert = ca_root / 'share' / 'ca-certificates' / 'cacert.pem'
    if not cert.is_file():
        raise RuntimeError('Install the Homebrew ca-certificates formula before building.')
    # Ship Mozilla's versioned bundle, never locally installed private roots.
    shutil.copy2(cert, output / 'cert.pem')
    record_license(cert)
    ca_entry = next(entry for entry in manifests if entry['name'] == 'ca-certificates')
    ca_entry.update({'sha256': hashlib.sha256(cert.read_bytes()).hexdigest(), 'license': 'MPL-2.0', 'source': f"https://curl.se/ca/cacert-{ca_entry['version']}.pem"})
    (output / 'licenses' / 'ca-certificates' / 'NOTICE.txt').write_text('Mozilla CA certificate bundle, distributed under MPL-2.0.\nSource: ' + ca_entry['source'] + '\nLicense: https://www.mozilla.org/MPL/2.0/\n')
    shutil.copy2(Path(__file__).with_name('licenses') / 'MPL-2.0.txt', output / 'licenses/ca-certificates/MPL-2.0.txt')
    pyenv = f'export PYTHONHOME="$R/{pyhome}"\nexport PYTHONNOUSERSITE=1\nexport SSL_CERT_FILE="$R/cert.pem"'
    wrapper('python3', f'"$R/{pyhome}/bin/python3.14"', pyenv)
    wrapper('python3.14', f'"$R/{pyhome}/bin/python3.14"', pyenv)
    # Homebrew Node otherwise reads OpenSSL configuration from its build prefix.
    # An empty configuration retains OpenSSL defaults without host overrides.
    (output / 'openssl.cnf').write_text('# LocalXiv uses the default OpenSSL configuration.\n')
    wrapper('node', '"$R/vendor/node/bin/node"', 'export OPENSSL_CONF="$R/openssl.cnf"')
    wrapper('pandoc', '"$R/vendor/pandoc/bin/pandoc"')
    wrapper('rsvg-convert', '"$R/vendor/librsvg/bin/rsvg-convert"')
    for name in ('latexml', 'latexmlc', 'latexmlpost', 'latexmlmath', 'latexmlfind'):
        wrapper(name, f'/usr/bin/perl5.34 "$R/vendor/latexml/libexec/bin/{name}"', 'export PERL5LIB="$R/vendor/latexml/libexec/lib/perl5"')
    wrapper('java', '"$R/vendor/openjdk/bin/java"')
    wrapper('epubcheck', '"$R/vendor/openjdk/bin/java" -jar "$R/vendor/epubcheck/libexec/epubcheck.jar"')
    wrapper('gs', '"$R/vendor/ghostscript/bin/gs"', 'export GS_LIB="$R/vendor/ghostscript/share/ghostscript/Resource/Init:$R/vendor/ghostscript/share/ghostscript/lib:$R/vendor/ghostscript/share/ghostscript/Resource/Font:$R/vendor/ghostscript/share/ghostscript/fonts"')
    manifest = {'platform': 'macOS 26+, arm64', 'java_modules': JAVA_MODULES.split(','), 'dependencies': manifests, 'systemDependencies': ['/usr/bin/perl5.34 and macOS Perl Extras', 'macOS system libraries'], 'publicationRequirements': 'Audit notices and provide corresponding source where required, including Ghostscript AGPL. Notices alone do not satisfy source obligations.'}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    for item in files(output):
        if item.is_symlink() and (os.path.isabs(os.readlink(item)) or not item.resolve().is_relative_to(output)):
            raise RuntimeError(f'External runtime symlink: {item}')
    for item in visited:
        for line in run('otool', '-L', str(item)).splitlines()[1:]:
            reference = line.strip().split(' (compatibility')[0]
            if reference.startswith(('/usr/lib/', '/System/Library/')):
                continue
            if not reference.startswith('@loader_path/') or not (item.parent / reference.removeprefix('@loader_path/')).exists():
                raise RuntimeError(f'Nonportable library reference in {item}: {reference}')
    smoke(output)
    return manifest


def smoke(output):
    output = Path(output).resolve()
    blocked = [Path('/opt/homebrew'), Path('/usr/local'), Path.home() / '.nvm']
    if any(output.is_relative_to(path) for path in blocked):
        raise RuntimeError('Place the smoke-test runtime outside Homebrew and the original Node installation.')
    profile = '(version 1)(allow default)(deny file-read* ' + ' '.join('(subpath ' + json.dumps(str(path)) + ')' for path in blocked) + ')'
    with tempfile.TemporaryDirectory(prefix='localxiv-runtime-smoke-') as temporary:
        work = Path(temporary)
        env = {'PATH': str(output / 'bin') + ':/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': str(work), 'TMPDIR': temporary, 'LANG': 'en_US.UTF-8'}
        commands = [('python3', '-c', 'import ssl, sqlite3, ctypes, bz2, lzma; assert ssl.create_default_context().cert_store_stats()["x509_ca"] > 0; print("Python TLS and extensions OK")'), ('pandoc', '--version'), ('latexml', '--VERSION'), ('latexmlpost', '--VERSION'), ('java', '-version'), ('epubcheck', '--version'), ('node', '-e', 'require("node:crypto").randomBytes(16); console.log(process.version)')]
        (work / 'test.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><text x="0" y="12">Hi</text></svg>')
        commands += [('rsvg-convert', '-o', str(work / 'test.png'), str(work / 'test.svg')), ('gs', '-q', '-dBATCH', '-dNOPAUSE', '-sDEVICE=pdfwrite', '-sOutputFile=' + str(work / 'test.pdf'), '-c', '/Helvetica findfont 12 scalefont setfont 20 20 moveto (Hello) show showpage')]
        for extension in ('eps', 'ps'):
            (work / ('test.' + extension)).write_text('%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 100 100\n/Helvetica findfont 12 scalefont setfont 10 20 moveto (Hello) show showpage\n')
        for extension in ('pdf', 'eps', 'ps'):
            commands.append(('gs', '-dSAFER', '-q', '-dBATCH', '-dNOPAUSE', '-sDEVICE=pngalpha', '-r72',
                             '-dFirstPage=1', '-dLastPage=1', '-sOutputFile=' + str(work / (extension + '.png')), str(work / ('test.' + extension))))
        (work / 'test.md').write_text('---\ntitle: Runtime check\nlang: en\n---\n\n# Test\n\nHello.\n')
        commands += [('pandoc', str(work / 'test.md'), '-o', str(work / 'test.epub')), ('epubcheck', str(work / 'test.epub'))]
        (work / 'test.tex').write_text(r'\documentclass{article}\begin{document}Hello $x^2$.\end{document}')
        commands += [('latexml', '--quiet', '--dest=' + str(work / 'test.xml'), str(work / 'test.tex')), ('latexmlpost', '--quiet', '--format=html5', '--dest=' + str(work / 'test.html'), str(work / 'test.xml'))]
        for command in commands:
            result = subprocess.run(['/usr/bin/sandbox-exec', '-p', profile, *command], cwd=work, env=env, capture_output=True, text=True, timeout=120)
            if result.returncode:
                raise RuntimeError(f'Runtime smoke failed: {command}\n{result.stdout}\n{result.stderr}')
        assert 'Hello' in (work / 'test.html').read_text()
        assert (work / 'test.png').stat().st_size > 0
        assert (work / 'test.pdf').stat().st_size > 0
        for extension in ('pdf', 'eps', 'ps'):
            assert (work / (extension + '.png')).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        with zipfile.ZipFile(work / 'test.epub') as source, zipfile.ZipFile(work / 'invalid.epub', 'w') as target:
            for entry in source.infolist():
                target.writestr(entry, b'invalid/type' if entry.filename == 'mimetype' else source.read(entry))
        invalid = subprocess.run(['/usr/bin/sandbox-exec', '-p', profile, 'epubcheck', str(work / 'invalid.epub')],
                                 cwd=work, env=env, capture_output=True, text=True, timeout=120)
        if invalid.returncode != 1 or 'PKG-007' not in invalid.stdout + invalid.stderr:
            raise RuntimeError('EPUBCheck must reject an invalid mimetype: ' + invalid.stdout + invalid.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--smoke-only', action='store_true')
    args = parser.parse_args()
    if args.smoke_only:
        smoke(args.output)
    else:
        bundle(args.output)
    print('Runtime checks passed:', args.output)
