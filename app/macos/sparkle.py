"""Pinned Sparkle tools and signed release feeds. Private keys never enter arguments."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
VERSION = '2.9.6'
SHA256 = '52bf9e88cdd972fc0c81501377a880e90d47031bd8ca5462488f843e2609e192'
URL = f'https://github.com/sparkle-project/Sparkle/releases/download/{VERSION}/Sparkle-{VERSION}.tar.xz'
CACHE = ROOT / '.sparkle' / VERSION
FEED = 'https://raw.githubusercontent.com/Akhil-Theerthala/LocalXiv/updates/appcast.xml'
PUBLIC_KEY = 'fds9vIE45LBQDh4enNe0rthh8hIYXpZtUxVoaQx+E5g='
NAMESPACE = '{http://www.andymatuschak.org/xml-namespaces/sparkle}'


def distribution():
    if (CACHE / '.verified').is_file() and (CACHE / '.verified').read_text() == SHA256:
        return CACHE
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=CACHE.parent) as temporary:
        stage = Path(temporary)
        archive = stage / 'sparkle.tar.xz'
        with urllib.request.urlopen(URL, timeout=60) as response, archive.open('wb') as output:
            shutil.copyfileobj(response, output)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
            raise ValueError('Sparkle archive checksum mismatch.')
        unpacked = stage / 'unpacked'
        unpacked.mkdir()
        subprocess.run(['tar', '-xf', str(archive), '-C', str(unpacked)], check=True)
        (unpacked / '.verified').write_text(SHA256)
        if CACHE.exists():
            shutil.rmtree(CACHE)
        unpacked.rename(CACHE)
    return CACHE


def validate_feed(path, build_number, archive):
    item = ET.parse(path).find('./channel/item')
    if item is None or item.findtext(NAMESPACE + 'version') != str(build_number):
        raise ValueError('Appcast version does not match the built app.')
    enclosure = item.find('enclosure')
    signature = enclosure.get(NAMESPACE + 'edSignature', '') if enclosure is not None else ''
    if len(base64.b64decode(signature, validate=True)) != 64:
        raise ValueError('Appcast must contain an Ed25519 update signature.')
    if enclosure.get('length') != str(archive.stat().st_size):
        raise ValueError('Appcast size does not match the update archive.')
    return item


def appcast(release_dir):
    release_dir = release_dir.resolve()
    manifest = json.loads((release_dir / 'release.json').read_text())
    info = plistlib.loads((release_dir / 'LocalXiv.app/Contents/Info.plist').read_bytes())
    if info.get('SUPublicEDKey') != PUBLIC_KEY or info.get('SUFeedURL') != FEED:
        raise ValueError('Release does not contain the configured Sparkle trust key and feed.')
    archives = list(release_dir.glob('*.dmg'))
    if len(archives) != 1:
        raise ValueError('Expected exactly one release DMG.')
    tools = distribution() / 'bin'
    public_key = subprocess.run([str(tools / 'generate_keys'), '--account',
                                 'localxiv-sparkle', '-p'], check=True,
                                capture_output=True, text=True).stdout.strip()
    if public_key != PUBLIC_KEY:
        raise ValueError('Local Keychain signing key does not match the app trust key.')
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        archive = work / archives[0].name
        shutil.copyfile(archives[0], archive)
        # Explicit release tag URLs work for GitHub prereleases as well as stable releases.
        download = f'https://github.com/Akhil-Theerthala/LocalXiv/releases/download/v{manifest["version"]}/'
        notes = ROOT / 'docs/releases' / f'v{manifest["version"]}.md'
        if notes.is_file():
            archive.with_suffix('.md').write_text(notes.read_text())
        command = [str(tools / 'generate_appcast'), '--download-url-prefix', download,
                   '--maximum-deltas', '0', '--embed-release-notes', '-o', str(work / 'appcast.xml')]
        command += ['--account', 'localxiv-sparkle']
        subprocess.run(command + [str(work)], check=True)
        item = validate_feed(work / 'appcast.xml', manifest['build'], archive)
        if item.find('enclosure').get('url') != download + archive.name:
            raise ValueError('Appcast download URL does not match the release asset.')
        verify = [str(tools / 'sign_update'), '--account', 'localxiv-sparkle', '--verify']
        subprocess.run(verify + [str(archive), item.find('enclosure').get(NAMESPACE + 'edSignature')], check=True)
        subprocess.run(verify + [str(work / 'appcast.xml')], check=True)
        shutil.copyfile(work / 'appcast.xml', release_dir / 'appcast.xml')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appcast', type=Path)
    args = parser.parse_args()
    if args.appcast:
        appcast(args.appcast)
    else:
        print(distribution())
