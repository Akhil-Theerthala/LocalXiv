#!/usr/bin/env python3
"""Build a portable LocalXiv app and DMG. No upload occurs without --notarize."""
import argparse
import hashlib
import json
import os
import platform
import plistlib
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from bundle_runtime import bundle, smoke
from sparkle import distribution, FEED, PUBLIC_KEY, VERSION as SPARKLE_VERSION

ROOT = Path(__file__).resolve().parents[2]


def copy_node_modules(source, destination):
    """Copy installed runtime dependencies, retaining npm's nested resolution."""
    source = source.resolve()
    pending = [source / name for name in ('mathjax-full', '@xmldom/xmldom')]
    copied = set()
    while pending:
        package = pending.pop()
        if package in copied:
            continue
        metadata = json.loads((package / 'package.json').read_text())
        def omit(directory, names):
            relative = Path(directory).relative_to(package).as_posix()
            ignored = {'node_modules', '.DS_Store'}
            if metadata['name'] == 'mathjax-full':
                if relative == '.':
                    ignored.update({'ts', 'components'})
                elif relative == 'es5':
                    # math-config.js disables autoload, require and the context menu.
                    ignored.update(set(names) - {'tex-svg.js'})
            return ignored
        shutil.copytree(package, destination / package.relative_to(source), ignore=omit)
        copied.add(package)
        optional = metadata.get('optionalDependencies', {})
        for name in metadata.get('dependencies', {}) | optional:
            parent = package
            while parent != source.parent:
                candidate = parent / 'node_modules' / name if parent != source else source / name
                if (candidate / 'package.json').is_file():
                    pending.append(candidate)
                    break
                parent = parent.parent
            else:
                if name not in optional:
                    raise RuntimeError(f'Missing runtime dependency {name} of {metadata["name"]}')


def file_bytes(root):
    return sum(path.stat().st_size for path in root.rglob('*') if path.is_file() and not path.is_symlink())


def size_inventory(app):
    resources = app / 'Contents/Resources'
    parts = {f'runtime/vendor/{path.name}': file_bytes(path)
             for path in (resources / 'runtime/vendor').iterdir() if path.is_dir()}
    parts.update({name: file_bytes(resources / name) for name in ('runtime/lib', 'app/node_modules')})
    total = file_bytes(app)
    # MiB of file contents, not allocated filesystem blocks or DMG compression.
    limits = {'app': 650, 'runtime/vendor/openjdk': 65, 'runtime/vendor/ghostscript': 55,
              'runtime/vendor/python@3.14': 50, 'app/node_modules': 20}
    for name, limit in limits.items():
        size = total if name == 'app' else parts[name]
        if size > limit * 1024**2:
            raise RuntimeError(f'{name} exceeds its {limit} MiB size budget: {size / 1024**2:.1f} MiB')
    return {'app_bytes': total, 'components_bytes': parts, 'budgets_mib': limits}


def run(*args, **kwargs):
    try:
        return subprocess.run([str(arg) for arg in args], check=True, **kwargs)
    except subprocess.CalledProcessError as error:
        if error.stderr:
            print(error.stderr.decode() if isinstance(error.stderr, bytes) else error.stderr, flush=True)
        raise


def macho(path):
    if path.is_symlink() or not path.is_file():
        return False
    with path.open('rb') as stream:
        return stream.read(4) in (b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca')


def sign_app(app, identity):
    # Sign from the inside out; --deep is only used for verification.
    base = ['codesign', '--force', '--sign', identity]
    if identity != '-':
        base += ['--timestamp', '--options', 'runtime']
    for path in sorted(app.rglob('*'), key=lambda p: len(p.parts), reverse=True):
        if macho(path):
            flags = []
            if path.name in ('node', 'java'):
                flags = ['--entitlements', str(ROOT / 'app/macos/jit-entitlements.plist')]
            elif path.name in ('Python', 'python3.14', 'LocalXiv'):
                flags = ['--entitlements', str(ROOT / 'app/macos/app-entitlements.plist')]
            run(*base, *flags, path, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    for path in sorted(app.rglob('*'), key=lambda p: len(p.parts), reverse=True):
        if not path.is_symlink() and path.is_dir() and path.suffix in ('.app', '.framework', '.jdk', '.xpc'):
            run(*base, path, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    run(*base, '--entitlements', ROOT / 'app/macos/app-entitlements.plist', app)
    run('codesign', '--verify', '--deep', '--strict', '--verbose=2', app)


def notarize(path, profile, log):
    result = subprocess.run(['xcrun', 'notarytool', 'submit', str(path), '--keychain-profile',
                             profile, '--wait', '--output-format', 'json'], capture_output=True, text=True)
    log.write_text(result.stdout + '\n' + result.stderr)
    if result.returncode or json.loads(result.stdout).get('status') != 'Accepted':
        raise SystemExit(f'Apple did not accept notarization. Inspect {log}.')


def build(args):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise SystemExit('The initial release build requires an Apple Silicon Mac.')
    if int(platform.mac_ver()[0].split('.')[0]) < 26:
        raise SystemExit('Build with macOS 26 or newer. Initial release target is macOS 26.')
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?', args.version):
        raise SystemExit('Version must look like 0.1.0 or 0.1.0-beta.1.')
    if not re.fullmatch(r'[1-9][0-9]*', args.build_number):
        raise SystemExit('Build number must be a positive integer.')
    if args.identity != '-' and not args.identity.startswith('Developer ID Application:'):
        raise SystemExit('Use a Developer ID Application identity, or omit it for local testing.')
    if args.notarize and (args.identity == '-' or not args.keychain_profile):
        raise SystemExit('--notarize requires --identity and --keychain-profile.')
    if args.notarize and not (ROOT / 'LICENSE').is_file():
        raise SystemExit('Settle the app license and dependency source distribution before public release. See docs/macos-release.md.')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    label = 'notarized' if args.notarize else 'signed-unnotarized' if args.identity != '-' else 'unsigned-local'
    stem = f'LocalXiv-{args.version}-macOS26-arm64-{label}'
    final = output / stem
    if final.exists():
        raise SystemExit(f'Refusing to replace {final}; use a new output directory or version.')
    if not (ROOT / 'node_modules/mathjax-full').is_dir():
        raise SystemExit('Run npm ci --ignore-scripts --omit=dev first.')
    sparkle = distribution()
    with tempfile.TemporaryDirectory(prefix='.localxiv-build-', dir=output) as temp:
        stage = Path(temp)
        app = stage / 'LocalXiv.app'
        contents = app / 'Contents'
        resources = contents / 'Resources'
        code = resources / 'app'
        code.mkdir(parents=True)
        (contents / 'MacOS').mkdir()
        frameworks = contents / 'Frameworks'
        frameworks.mkdir()
        shutil.copytree(sparkle / 'Sparkle.framework', frameworks / 'Sparkle.framework', symlinks=True)
        shutil.copy2(sparkle / 'LICENSE', resources / 'Sparkle-LICENSE.txt')
        for name in ('app', 'papers', 'native'):
            shutil.copytree(ROOT / name, code / name, symlinks=True,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'prototypes', '.DS_Store'))
        copy_node_modules(ROOT / 'node_modules', code / 'node_modules')
        for name in ('launch.command', 'package.json', 'package-lock.json'):
            shutil.copy2(ROOT / name, code / name)
        (code / 'release-id.txt').write_text(str(uuid.uuid4()) + '\n')
        for name in ('LICENSE', 'NOTICE'):
            if (ROOT / name).is_file():
                shutil.copy2(ROOT / name, resources / name)
        shutil.copy2(ROOT / 'app/assets/AppIcon.icns', resources / 'AppIcon.icns')
        runtime = resources / 'runtime'
        if args.runtime:
            shutil.copytree(args.runtime.resolve(), runtime, symlinks=True)
        else:
            bundle(runtime)
        smoke(runtime)
        # Install the pinned AI dependency closure using the bundled Python ABI.
        run(str(runtime / 'bin/python3'), '-B', '-m', 'pip', 'install', '--no-compile', '--target',
            code / 'python-packages', '-r', ROOT / 'requirements-ai.txt')
        run('xcrun', 'swiftc', '-module-cache-path', stage / 'swift-cache', '-O',
            ROOT / 'papers/HTMLSnapshot.swift', '-o', code / 'papers/html-snapshot')
        run('xcrun', 'swiftc', '-module-cache-path', stage / 'swift-cache',
            '-target', 'arm64-apple-macosx26.0', '-O', ROOT / 'app/macos/PapersToKindle.swift',
            '-F', frameworks, '-framework', 'Sparkle', '-Xlinker', '-rpath', '-Xlinker', '@executable_path/../Frameworks',
            '-o', contents / 'MacOS/LocalXiv')
        info = dict(CFBundleName='LocalXiv', CFBundleDisplayName='LocalXiv',
                    CFBundleIdentifier='local.paperstokindle.reader', CFBundlePackageType='APPL',
                    CFBundleExecutable='LocalXiv', CFBundleShortVersionString=args.version.split('-')[0],
                    CFBundleVersion=args.build_number, CFBundleIconFile='AppIcon',
                    NSHighResolutionCapable=True, LSMinimumSystemVersion='26.0',
                    NSAppleEventsUsageDescription='LocalXiv uses Mail to send the paper you choose to your Kindle.',
                    NSAppTransportSecurity={'NSAllowsLocalNetworking': True},
                    SUFeedURL=FEED, SUPublicEDKey=PUBLIC_KEY, SUVerifyUpdateBeforeExtraction=True, SURequireSignedFeed=True,
                    SUAllowsAutomaticUpdates=False, SUEnableInstallerLauncherService=False)
        (contents / 'Info.plist').write_bytes(plistlib.dumps(info))
        manifest = dict(version=args.version, build=args.build_number, platform='macOS 26 arm64',
                        status=label, source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                        source_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all', '--',
                                                                  'app', 'papers', 'native', 'launch.command', 'package.json',
                                                                  'package-lock.json', 'LICENSE', 'NOTICE'], cwd=ROOT)),
                        automatic_updates=False, updater='Sparkle', sparkle_version=SPARKLE_VERSION,
                        update_feed=FEED, in_app_updates=True)
        (resources / 'release.json').write_text(json.dumps(manifest, indent=2) + '\n')
        for path in app.rglob('*'):
            if path.is_symlink() and (not path.exists() or not path.resolve().is_relative_to(app.resolve())):
                raise SystemExit(f'App contains an unresolved or external symlink: {path}')
        # Build-time imports and pip caches are reproducible from the shipped Python source.
        for cache in app.rglob('__pycache__'):
            if cache.is_dir() and not cache.is_symlink():
                shutil.rmtree(cache)
        sign_app(app, args.identity)
        smoke(runtime)
        run('codesign', '--verify', '--deep', '--strict', app)
        sizes = size_inventory(app)
        if args.notarize:
            archive = stage / 'notarization.zip'
            run('ditto', '-c', '-k', '--keepParent', app, archive)
            notarize(archive, args.keychain_profile, output / (stem + '-app-notarization.json'))
            run('xcrun', 'stapler', 'staple', app)
            run('xcrun', 'stapler', 'validate', app)
            run('spctl', '--assess', '--type', 'execute', '--verbose=2', app)
        image_root = stage / 'image'
        image_root.mkdir()
        shutil.move(app, image_root / app.name)
        (image_root / 'Applications').symlink_to('/Applications')
        (image_root / 'Read me.txt').write_text(
            'LocalXiv requires Apple Silicon and macOS 26 or newer.\n\n'
            'Drag LocalXiv to Applications, then open it from Applications.\n'
            'Your papers are saved in ~/Library/Application Support/LocalXiv/library.\n'
            'Before replacing an older version, let jobs finish and stop its background service.\n'
            'Removing the app does not remove your papers.\n\n'
            + ('AD HOC SIGNED PREVIEW: not notarized by Apple.\n' if args.identity == '-' else ''))
        dmg = stage / (stem + '.dmg')
        run('hdiutil', 'create', '-volname', 'LocalXiv', '-srcfolder', image_root, '-format', 'UDZO', dmg)
        if args.identity != '-':
            run('codesign', '--sign', args.identity, '--timestamp', dmg)
        if args.notarize:
            notarize(dmg, args.keychain_profile, output / (stem + '-dmg-notarization.json'))
            run('xcrun', 'stapler', 'staple', dmg)
            run('xcrun', 'stapler', 'validate', dmg)
        run('hdiutil', 'verify', dmg)
        sizes['dmg_bytes'] = dmg.stat().st_size
        if sizes['dmg_bytes'] > 350 * 1024**2:
            raise RuntimeError('DMG exceeds its 350 MiB size budget.')
        final.mkdir()
        shutil.move(dmg, final / dmg.name)
        shutil.move(image_root / 'LocalXiv.app', final / 'LocalXiv.app')
        (final / 'release.json').write_text(json.dumps(manifest, indent=2) + '\n')
        (final / 'size-report.json').write_text(json.dumps(sizes, indent=2) + '\n')
        if not manifest['source_dirty']:
            run('git', '-C', ROOT, 'archive', '--format=tar.gz', '--prefix=LocalXiv-source/',
                '-o', final / (stem + '-source.tar.gz'), manifest['source_commit'])
        checksums = []
        for path in sorted(final.iterdir()):
            if path.is_file():
                with path.open('rb') as stream:
                    checksums.append(f'{hashlib.file_digest(stream, "sha256").hexdigest()}  {path.name}\n')
        (final / 'SHA256SUMS').write_text(''.join(checksums))
    print(f'Built {final}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--build-number', default='1')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    parser.add_argument('--runtime', type=Path, help='Reuse a previously built portable runtime; copied and rechecked')
    parser.add_argument('--identity', default='-', help='Developer ID Application identity; default is ad hoc local testing')
    parser.add_argument('--notarize', action='store_true', help='Upload to Apple, staple tickets and assess Gatekeeper')
    parser.add_argument('--keychain-profile', help='Existing notarytool Keychain profile name; never a password')
    build(parser.parse_args())
