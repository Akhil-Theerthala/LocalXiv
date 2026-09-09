#!/usr/bin/env python3
"""Collect release source inputs. An inventory is not a compliance certificate."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
# Ask Homebrew to interpret its own installed recipe, including resources.
RECIPE = r'''
require "formulary"
f = Formulary.factory(ARGV.fetch(0))
resource = ->(r) { {name: r.name, url: r.url, sha256: r.checksum.to_s} }
puts JSON.generate({version: f.pkg_version.to_s, source: resource.call(f.stable),
  resources: f.resources.map { |r| resource.call(r) },
  patches: f.patchlist.map { |p| p.respond_to?(:resource) ? resource.call(p.resource) : {embedded: p.class.name, file: (p.respond_to?(:file) ? p.file.to_s : nil)} }})
'''


def run(*args):
    return subprocess.check_output(args, text=True, env={**os.environ, 'HOMEBREW_NO_AUTO_UPDATE': '1', 'HOMEBREW_DEVELOPER': '0'}).strip()


def digest(path, algorithm='sha256'):
    value = hashlib.new(algorithm)
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value


def fetch(url, destination, expected=None, algorithm='sha256'):
    if urllib.parse.urlsplit(url).scheme != 'https':
        raise ValueError(f'Only HTTPS archives are supported: {url}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        partial = destination.with_suffix(destination.suffix + '.partial')
        try:
            with urllib.request.urlopen(url, timeout=30) as source, partial.open('wb') as target:
                shutil.copyfileobj(source, target)
            if expected and digest(partial, algorithm).hexdigest() != expected:
                raise ValueError(f'Checksum mismatch for {url}')
            partial.replace(destination)
        finally:
            partial.unlink(missing_ok=True)
    if expected and digest(destination, algorithm).hexdigest() != expected:
        raise ValueError(f'Checksum mismatch for cached file {destination}')
    return digest(destination).hexdigest()


def installed_resource(root, destination, expected):
    """Recover unchanged recipe inputs from the exact installed keg."""
    for candidate in root.rglob(destination.name):
        if candidate.is_file() and not candidate.is_symlink() and digest(candidate).hexdigest() == expected:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate, destination)
            return 'installed:' + str(candidate.relative_to(root))
    return None


def formula_version(metadata):
    version = metadata['versions']['stable']
    return version + (f"_{metadata['revision']}" if metadata['revision'] else '')


def collect(runtime, output, metadata_only=False):
    runtime, output = runtime.resolve(), output.resolve()
    manifest = json.loads((runtime / 'manifest.json').read_text())
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(runtime / 'manifest.json', output / 'runtime-manifest.json')
    if (runtime / 'licenses').exists():
        shutil.copytree(runtime / 'licenses', output / 'notices', dirs_exist_ok=True)
    brew_license = Path(run('brew', '--repository')) / 'LICENSE.txt'
    shutil.copy2(brew_license, output / 'HOMEBREW-LICENSE.txt')
    lock = json.loads((ROOT / 'package-lock.json').read_text())
    shutil.copy2(ROOT / 'package-lock.json', output / 'package-lock.json')
    report = {'status': 'metadata-only' if metadata_only else 'review-required',
              'correspondingSourceComplete': False, 'archives': [], 'errors': [],
              'reviewRequired': [
                  'Audit statically bundled libraries, fonts, certificates, JARs and Perl modules against the runtime inventory.',
                  'Confirm npm package tarballs contain preferred source and preserve their license notices in the app.',
                  'Supply the exact LocalXiv source revision and build/installation scripts with the release.',
                  'Confirm LGPL replacement/relinking requirements and upstream build instructions for this binary distribution.']}

    def archive(record, directory, label, installed=None):
        url, checksum = record.get('url'), record.get('sha256')
        if not url or not checksum or not re.fullmatch(r'[0-9a-f]{64}', checksum):
            raise ValueError(f'{label}: no hash-pinned source archive; resolve manually')
        name = Path(urllib.parse.unquote(urllib.parse.urlsplit(url).path)).name
        if not name or name in ('.', '..'):
            raise ValueError(f'Invalid archive URL: {url}')
        destination = directory / name
        entry = {'component': label, 'url': url, 'sha256': checksum, 'kind': 'formula-input',
                 'path': str(destination.relative_to(output)), 'downloaded': False}
        report['archives'].append(entry)
        if not metadata_only:
            candidates = [url]
            if url.startswith('https://ftpmirror.gnu.org/'):
                candidates.append(url.replace('https://ftpmirror.gnu.org/', 'https://ftp.gnu.org/'))
            if label == 'latexml':
                candidates.append('https://dlmf.nist.gov/LaTeXML/releases/' + name)
                candidates.append('https://cpan.metacpan.org/authors/id/B/BR/BRMILLER/' + name)
            failures = []
            for candidate in candidates:
                try:
                    fetch(candidate, destination, checksum)
                    entry['downloadedFrom'] = candidate
                    entry['downloaded'] = True
                    break
                except Exception as error:
                    failures.append(f'{candidate}: {error}')
            if not entry['downloaded'] and installed is not None:
                recovered = installed_resource(installed, destination, checksum)
                if recovered:
                    entry.update(downloaded=True, downloadedFrom=recovered)
            if not entry['downloaded']:
                report['errors'].append(f'{label}: ' + '; '.join(failures))

    for dep in manifest['dependencies']:
        name, version = dep['name'], dep['version']
        print(f'Collecting {name} {version}', flush=True)
        try:
            if name == 'node':
                if not re.fullmatch(r'v\d+\.\d+\.\d+', version):
                    raise ValueError(f'Unsupported Node version: {version}')
                base = f'https://nodejs.org/dist/{version}'
                directory = output / 'node'
                if metadata_only:
                    report['reviewRequired'].append(f'Node {version} source and SHASUMS256.txt still need downloading.')
                else:
                    sums = directory / 'SHASUMS256.txt'
                    fetch(base + '/SHASUMS256.txt', sums)
                    filename = f'node-{version}.tar.xz'
                    checksum = next(line.split()[0] for line in sums.read_text().splitlines() if line.split()[-1] == filename)
                    archive({'url': base + '/' + filename, 'sha256': checksum}, directory, name)
                continue
            metadata = json.loads(run('brew', 'info', '--json=v2', name))['formulae'][0]
            directory = output / 'homebrew' / name
            directory.mkdir(parents=True, exist_ok=True)
            (directory / 'formula.json').write_text(json.dumps(metadata, indent=2) + '\n')
            if formula_version(metadata) != version:
                raise ValueError(f'{name}: installed {version}, current recipe {formula_version(metadata)}; restore exact version metadata or rebuild runtime before collecting sources')
            keg = Path(run('brew', '--cellar', name)) / version
            recipe = keg / '.brew' / f'{name}.rb'
            shutil.copy2(recipe, directory / recipe.name)
            shutil.copy2(keg / 'INSTALL_RECEIPT.json', directory / 'INSTALL_RECEIPT.json')
            exact = json.loads(run('brew', 'ruby', '-e', RECIPE, str(recipe)))
            if exact['version'] != version:
                raise ValueError(f'{name}: installed recipe does not match runtime version {version}')
            (directory / 'source-inputs.json').write_text(json.dumps(exact, indent=2) + '\n')
            archive(exact['source'], directory / 'source', name)
            if name == 'pandoc':
                report['reviewRequired'].append('Pandoc: Homebrew recipe resolves Cabal dependencies at build time without a frozen dependency list; recover the exact Haskell source versions embedded in this bottle.')
            if name in ('epubcheck', 'latexml'):
                # EPUBCheck is binary-only; NIST's LaTeXML archive can be unavailable.
                repository = 'w3c/epubcheck' if name == 'epubcheck' else 'brucemiller/LaTeXML'
                tag = 'v' + metadata['versions']['stable']
                url = f'https://github.com/{repository}/archive/refs/tags/{tag}.tar.gz'
                target = directory / 'source' / f'{name}-{tag}-source.tar.gz'
                entry = {'component': f'{name} upstream source', 'url': url,
                         'path': str(target.relative_to(output)), 'downloaded': False}
                report['archives'].append(entry)
                if not metadata_only:
                    entry['sha256'] = fetch(url, target)
                    entry['downloaded'] = True
                if name == 'epubcheck':
                    report['reviewRequired'].append('EPUBCheck: its Homebrew URL is a binary ZIP. Matching upstream source tag is collected separately; audit dependency JAR sources and notices against that ZIP.')
                else:
                    report['reviewRequired'].append('LaTeXML: confirm the GitHub source tag matches the NIST release archive used by the bottle if the original archive remains unavailable.')
            for index, resource in enumerate(exact['resources']):
                archive(resource, directory / 'resources' / str(index), f"{name} resource {resource['name']}", installed=keg)
            for index, patch in enumerate(exact['patches']):
                if patch.get('embedded') in ('DATAPatch', 'StringPatch'):
                    continue  # The complete installed recipe already contains these patches.
                if patch.get('embedded') == 'LocalPatch':
                    commit = metadata.get('tap_git_head', '')
                    relative = Path(patch['file'])
                    if metadata.get('tap') != 'homebrew/core' or not re.fullmatch(r'[0-9a-f]{40}', commit) or relative.is_absolute() or '..' in relative.parts:
                        raise ValueError(f'{name}: cannot locate local patch {relative}')
                    url = f'https://raw.githubusercontent.com/Homebrew/homebrew-core/{commit}/{relative.as_posix()}'
                    target = directory / 'patches' / relative.name
                    entry = {'component': f'{name} local patch', 'url': url,
                             'path': str(target.relative_to(output)), 'downloaded': False}
                    report['archives'].append(entry)
                    if not metadata_only:
                        entry['sha256'] = fetch(url, target)
                        entry['downloaded'] = True
                    report['reviewRequired'].append(f'{name}: confirm local patch {relative} at {commit} matches the installed bottle; receipt lacks a source commit.')
                    continue
                archive(patch, directory / 'patches' / str(index), f'{name} patch {index}')
        except Exception as error:
            report['errors'].append(f'{name} {version}: {error}')

    for location, package in lock['packages'].items():
        if not location or package.get('dev'):
            continue
        try:
            integrity = package.get('integrity', '').split()[0]
            algorithm, encoded = integrity.split('-', 1)
            if algorithm not in ('sha256', 'sha384', 'sha512'):
                raise ValueError(f'{location}: unsupported integrity algorithm {algorithm}')
            expected = base64.b64decode(encoded, validate=True).hex()
            # Use the full lockfile path to disambiguate nested package versions.
            filename = hashlib.sha256(location.encode()).hexdigest()[:16] + '.tgz'
            destination = output / 'npm' / filename
            entry = {'component': location, 'version': package['version'], 'license': package.get('license'),
                     'url': package['resolved'], 'integrity': integrity,
                     'path': str(destination.relative_to(output)), 'downloaded': False}
            report['archives'].append(entry)
            if not metadata_only:
                entry['sha256'] = fetch(package['resolved'], destination, expected, algorithm)
                entry['downloaded'] = True
        except Exception as error:
            report['errors'].append(f'{location}: {error}')
    if report['errors']:
        report['status'] = 'blocked'
    (output / 'source-inventory.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'archives': len(report['archives']), 'errors': report['errors'], 'inventory': str(output / 'source-inventory.json')}, indent=2))
    return not report['errors']


def self_test():
    assert formula_version({'versions': {'stable': '1.2'}, 'revision': 2}) == '1.2_2'
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / 'archive'
        path.write_bytes(b'known source')
        expected = hashlib.sha256(b'known source').hexdigest()
        installed = Path(temporary) / 'keg'
        installed.mkdir()
        (installed / 'resource').write_bytes(b'known source')
        recovered = Path(temporary) / 'collected/resource'
        assert installed_resource(installed, recovered, '0' * 64) is None
        assert not recovered.exists()
        assert installed_resource(installed, recovered, expected) == 'installed:resource'
        assert recovered.read_bytes() == b'known source'

        assert fetch('https://example.org/source', path, expected) == expected
        try:
            fetch('https://example.org/source', path, '0' * 64)
        except ValueError:
            pass
        else:
            raise AssertionError('Corrupt cached archive accepted')
    print('Source collector self-check passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime', type=Path, nargs='?')
    parser.add_argument('output', type=Path, nargs='?')
    parser.add_argument('--metadata-only', action='store_true', help='Check provenance without downloading archives')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
    elif args.runtime is None or args.output is None:
        parser.error('runtime and output are required')
    else:
        raise SystemExit(0 if collect(args.runtime, args.output, args.metadata_only) else 1)
