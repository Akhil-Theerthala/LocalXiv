#!/usr/bin/env python3
"""Explicit, potentially billable smoke run of the production Overview / Blog workflow.

    python3 tests/test_live.py openrouter 1706.03762 --model YOUR_MODEL --section both
    python3 tests/test_live.py openrouter hep-th/9901001 --document /path/to/document.json \
        --env-file /path/to/original/checkout/.env --output .scratch/live --section blog

Example .env (never commit real credentials):
    OPENROUTER_API_KEY="YOUR_KEY"
    OPENROUTER_MODEL="YOUR_MODEL"

Other presets: openai, deepseek, gemini; use <PROVIDER>_API_KEY and
<PROVIDER>_MODEL. Names are case-insensitive; OS environment overrides .env,
--model overrides the model environment setting. There is no default paid model.
Dotenv supports export, comments and quotes, but no expansion or shell execution.
The default .env is at this worktree's root; a missing file allows OS-only setup.

Requires the existing native HTML renderer; Blog also requires smolagents.
Nothing is installed automatically. --document uses its containing directory in
place (generation may add workflow artifacts there); it does not move the paper
or discover/change your personal library. Each run gets a new output directory.
Importing this module or unittest discovery never starts a live run.
"""
import argparse
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PRESETS = {
    'openrouter': 'https://openrouter.ai/api/v1',
    'openai': 'https://api.openai.com/v1',
    'deepseek': 'https://api.deepseek.com/v1',
    'gemini': 'https://generativelanguage.googleapis.com/v1beta/openai',
}


def read_env(path):
    """Read literal dotenv values without evaluating anything or reporting values."""
    if not path.exists():
        return {}
    values = {}
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        line = re.sub(r'^export\s+', '', line)
        name, separator, value = line.partition('=')
        if not separator or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name.strip()):
            raise ValueError(f'Invalid dotenv assignment on line {number}.')
        value = value.strip()
        if value.startswith(('"', "'")):
            end = value.find(value[0], 1)
            if end < 0 or (value[end + 1:].strip() and not value[end + 1:].strip().startswith('#')):
                raise ValueError(f'Invalid dotenv quotes on line {number}.')
            value = value[1:end]
        else:
            value = re.split(r'\s+#', value, maxsplit=1)[0].rstrip()
        values[name.strip().lower()] = value
    return values


def credentials(provider, model, values):
    values = {name.lower(): value for name, value in values.items()}
    values.update({name.lower(): value for name, value in os.environ.items()})
    key = values.get(provider + '_api_key', '').strip()
    chosen_model = (model if model is not None else values.get(provider + '_model', '')).strip()
    if not key:
        raise ValueError(f'Set {provider.upper()}_API_KEY in the environment or dotenv file (missing key).')
    if not chosen_model:
        raise ValueError(f'Choose --model or set {provider.upper()}_MODEL; no billable model is selected automatically.')
    return key, chosen_model


def paper_identifier(value):
    from papers.acquire import paper_id
    return paper_id(value if '://' in value else 'https://arxiv.org/abs/' + value)


def preflight(section):
    from papers import html_figures
    # Match html_figures.render's renderer lookup; do not build or install it here.
    renderer = Path(os.environ.get('LOCALXIV_HTML_RENDERER') or
                    Path(html_figures.__file__).with_name('html-snapshot'))
    if not renderer.is_file() or not os.access(renderer, os.X_OK):
        raise ValueError('Native HTML renderer is missing or not executable. See development instructions.')
    if section in ('blog', 'both') and importlib.util.find_spec('smolagents') is None:
        raise ValueError('Blog requires smolagents; see requirements-ai.txt. No dependencies were installed.')


def sanitized(value, key):
    """Remove credential fields and redact the chosen key, including in nested diagnostics."""
    if isinstance(value, str):
        return value.replace(key, '[REDACTED]') if key else value
    if isinstance(value, list):
        return [sanitized(item, key) for item in value]
    if isinstance(value, dict):
        return {sanitized(name, key): sanitized(item, key) for name, item in value.items()
                if not re.search(r'(^|_)(api_key|key|authorization|token|secret)$', name, re.I)}
    return value


def export_generation(directory, run, stem, generation, *, visual):
    from papers.exports import figure_source
    figures = generation.get('figures', [])
    if visual and len(figures) != 1:
        raise ValueError('Overview must contain exactly one image.')
    text = generation.get('cited_text') or generation.get('text', '')
    identifiers = [figure.get('id') for figure in figures]
    if any(not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', identifier)
           for identifier in identifiers) or len(set(identifiers)) != len(identifiers):
        raise ValueError('Invalid or duplicate figure identifier.')
    if not visual:
        if not isinstance(text, str) or not text.strip():
            raise ValueError('Blog has no Markdown text.')
        if sorted(re.findall(r'\{\{figure:([^}]+)\}\}', text)) != sorted(identifiers):
            raise ValueError('Unresolved, duplicate, or missing Blog figure marker.')
    # Validate all source paths before copying any assets.
    sources = []
    for figure in figures:
        png = figure_source(directory, figure, 'png')
        field = 'svg_source' if figure.get('svg_source') else 'svg'
        svg = figure_source(directory, figure, 'svg', field=field) if visual or figure.get(field) else None
        sources.append((figure, png, svg))
    run.mkdir(parents=True, exist_ok=True)
    assets = run if visual else run / (stem + '_assets')
    assets.mkdir(exist_ok=True)
    for figure, png, svg in sources:
        name = stem + '_overview' if visual else figure['id']
        shutil.copyfile(png, assets / (name + '.png'))
        if svg:
            shutil.copyfile(svg, assets / (name + '.svg'))
        if not visual:
            image = (assets / (name + '.png')).relative_to(run).as_posix()
            text = text.replace('{{figure:' + figure['id'] + '}}',
                                '![](' + image + ')\n\n' + figure.get('caption', ''))
    if not visual:
        if '{{figure:' in text:
            raise ValueError('Unresolved Blog figure marker.')
        (run / (stem + '.md')).write_text(text + '\n', encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('provider', choices=PRESETS)
    parser.add_argument('paper', help='arXiv identifier or HTTPS paper URL')
    parser.add_argument('--model', help='explicit billable provider model (or <PROVIDER>_MODEL)')
    parser.add_argument('--section', choices=('overview', 'blog', 'both'), default='both')
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    parser.add_argument('--output', type=Path, default=ROOT / '.scratch' / 'live', help='parent for unique run folders')
    parser.add_argument('--document', type=Path, help='existing local document.json; its parent holds retained assets')
    parser.add_argument('--length', choices=('short', 'medium', 'large'), default='medium')
    parser.add_argument('--vision', action='store_true')
    args = parser.parse_args(argv)
    key = ''
    run = None
    stdout, stderr = sys.stdout, sys.stderr
    def progress(message):
        print(sanitized(str(message), key), file=stdout, flush=True)
    try:
        # Direct script execution starts with tests/, not the repository, on sys.path.
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        key, model = credentials(args.provider, args.model, read_env(args.env_file))
        identifier = paper_identifier(args.paper)
        preflight(args.section)
        from papers.ai import Provider, generate_overview
        settings = {'endpoint': PRESETS[args.provider], 'model': model,
                    'overview_length': args.length, 'overview_language': 'casual',
                    'overview_vision': args.vision}
        provider = Provider(settings, key)
        if args.document:
            document_path = args.document.resolve(strict=True)
            document = json.loads(document_path.read_text(encoding='utf-8'))
            retained = document.get('arxiv_id')
            if not isinstance(retained, str):
                raise ValueError('Local document needs a valid arXiv identifier.')
            retained = paper_identifier(retained)
            requested_base = re.sub(r'v[1-9]\d*$', '', identifier)
            retained_base = re.sub(r'v[1-9]\d*$', '', retained)
            if requested_base != retained_base or (identifier != requested_base and identifier != retained):
                raise ValueError('Local document arXiv identifier/version does not match the requested paper.')
            document['directory'] = str(document_path.parent)
        args.output.mkdir(parents=True, exist_ok=True)
        stem = identifier.replace('/', '_')
        run = Path(tempfile.mkdtemp(prefix=stem + '-', dir=args.output)).resolve()
        progress('Run directory: ' + str(run))
        # Only our redacted progress reaches the terminal; dependencies may print raw errors.
        with open(os.devnull, 'w') as quiet, contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
            if not args.document:
                from papers.acquire import acquire
                from papers.convert import convert_import
                directory = run / 'paper'
                directory.mkdir()
                source_error = None
                progress('Downloading the exact paper version')
                try:
                    metadata = acquire('https://arxiv.org/abs/' + identifier, directory)
                except Exception as error:
                    metadata_path = directory / 'metadata.json'
                    if not metadata_path.is_file():
                        raise
                    metadata = json.loads(metadata_path.read_text())
                    source_error = error
                document = convert_import(directory, metadata, progress, source_error=source_error)
                document['directory'] = str(directory)
            directory = Path(document['directory'])
            overview = None
            for section in (('overview', 'blog') if args.section == 'both' else (args.section,)):
                visual = section == 'overview'
                progress('Generating ' + section + ' (live provider calls)')
                generation = generate_overview(provider, document, progress, visual=visual, image_overview=overview)
                generation = sanitized(generation, key)
                (run / (section + '.json')).write_text(json.dumps(generation, ensure_ascii=False, indent=2), encoding='utf-8')
                export_generation(directory, run, stem, generation, visual=visual)
                if visual:
                    overview = generation
        progress('Saved outputs to ' + str(run))
        return 0
    except (Exception, KeyboardInterrupt) as error:
        message = sanitized(str(error), key) or 'Interrupted.'
        print('Live run failed: ' + message, file=stderr)
        if run is not None:
            try:
                (run / 'error.json').write_text(json.dumps({'error': message}), encoding='utf-8')
            except OSError:
                print('Could not save error diagnostics.', file=stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
