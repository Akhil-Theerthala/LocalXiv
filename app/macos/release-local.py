"""Download a draft release, sign with local Keychain, and optionally publish it."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

from publish_update_feed import stage
from sparkle import appcast

REPO = 'Akhil-Theerthala/LocalXiv'


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def prepare(tag, directory):
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.]+)?', tag):
        raise ValueError('Use a release tag such as v0.0.5.')
    release = json.loads(run('gh', 'release', 'view', tag, '--repo', REPO,
                             '--json', 'isDraft', capture_output=True, text=True).stdout)
    if not release['isDraft']:
        raise ValueError('Only unpublished drafts can be signed by this command.')
    directory.mkdir(parents=True)  # Never overwrite an earlier signing session.
    run('gh', 'release', 'download', tag, '--repo', REPO, '--dir', str(directory))
    run('shasum', '-a', '256', '--check', 'SHA256SUMS', cwd=directory)
    manifest = json.loads((directory / 'release.json').read_text())
    if manifest['version'] != tag[1:]:
        raise ValueError('Release manifest does not match the requested tag.')
    archives = list(directory.glob('*.dmg'))
    if len(archives) != 1:
        raise ValueError('Expected exactly one release DMG.')
    with tempfile.TemporaryDirectory() as temporary:
        mount = Path(temporary) / 'volume'
        run('hdiutil', 'attach', str(archives[0]), '-readonly', '-nobrowse',
            '-mountpoint', str(mount))
        try:
            (directory / 'LocalXiv.app').symlink_to(mount / 'LocalXiv.app')
            try:
                appcast(directory)
            finally:
                (directory / 'LocalXiv.app').unlink()
        finally:
            run('hdiutil', 'detach', str(mount))
    with (directory / 'SHA256SUMS').open('w') as checksums:
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.name != 'SHA256SUMS':
                with path.open('rb') as source:
                    digest = hashlib.file_digest(source, 'sha256').hexdigest()
                checksums.write(f'{digest}  {path.name}\n')


def publish(tag, directory):
    # Only upload the files changed by local signing. The verified DMG stays intact.
    run('gh', 'release', 'upload', tag, '--repo', REPO, '--clobber',
        str(directory / 'appcast.xml'), str(directory / 'SHA256SUMS'))
    run('gh', 'release', 'edit', tag, '--repo', REPO,
        '--draft=false', '--prerelease', '--latest=false')
    publish_feed(directory / 'appcast.xml')


def publish_feed(feed):
    # A rejected concurrent push leaves the current feed intact. Retry --feed-only.
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        run('git', 'init', str(work))
        run('git', '-C', str(work), 'remote', 'add', 'origin', f'https://github.com/{REPO}.git')
        refs = run('git', '-C', str(work), 'ls-remote', '--heads', 'origin', 'updates',
                   capture_output=True, text=True).stdout
        if refs.strip():
            run('git', '-C', str(work), 'fetch', '--depth=1', 'origin', 'updates')
            run('git', '-C', str(work), 'checkout', '--detach', 'FETCH_HEAD')
        if not stage(feed, work / 'appcast.xml'):
            print('The public feed already has this build or a newer one.')
            return
        run('git', '-C', str(work), 'add', 'appcast.xml')
        run('git', '-C', str(work), '-c', 'user.name=LocalXiv release',
            '-c', 'user.email=release@localxiv.invalid', 'commit', '-m', 'Update signed feed')
        run('git', '-C', str(work), 'push', 'origin', 'HEAD:refs/heads/updates')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag', help='Existing draft release, for example v0.0.5')
    parser.add_argument('directory', type=Path, help='New directory to retain verified signed assets')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--publish', action='store_true', help='Also publish release and update feed')
    mode.add_argument('--feed-only', action='store_true', help='Retry feed publication after a failed push')
    args = parser.parse_args()
    directory = args.directory.resolve()
    if args.feed_only:
        release = json.loads(run('gh', 'release', 'view', args.tag, '--repo', REPO,
                                 '--json', 'isDraft', capture_output=True, text=True).stdout)
        if release['isDraft']:
            raise ValueError('Publish the release before its feed.')
        # Use the published bytes, not a possibly modified local feed.
        with tempfile.TemporaryDirectory() as temporary:
            run('gh', 'release', 'download', args.tag, '--repo', REPO,
                '--pattern', 'appcast.xml', '--dir', temporary)
            publish_feed(Path(temporary) / 'appcast.xml')
    else:
        prepare(args.tag, directory)
        if args.publish:
            publish(args.tag, directory)
        else:
            print(f'Signed assets retained in {directory}. Nothing published.')
