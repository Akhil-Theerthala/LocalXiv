"""Resolve a paper version and retain its original arXiv files."""
from __future__ import annotations

import hashlib
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


def paper_id(url: str) -> str:
    if not isinstance(url, str):
        raise ValueError('Enter an arXiv or alphaXiv paper link.')
    parts = urlsplit(url.strip())
    if (parts.scheme != 'https' or parts.hostname not in
            {'arxiv.org', 'www.arxiv.org', 'alphaxiv.org', 'www.alphaxiv.org'}
            or parts.username or parts.password or parts.port not in (None, 443)):
        raise ValueError('Use an HTTPS paper link on arxiv.org or alphaxiv.org.')
    routes = 'abs|pdf|html|overview' if parts.hostname in {'alphaxiv.org', 'www.alphaxiv.org'} else 'abs|pdf|html'
    match = re.fullmatch(r'/(?:' + routes + r')/(.+?)/?', unquote(parts.path))
    identifier = match[1].removesuffix('.pdf') if match else ''
    if not re.fullmatch(r'(?:\d{4}\.\d{4,5}|[A-Za-z][A-Za-z.\-]*/\d{7})(?:v[1-9]\d*)?', identifier):
        raise ValueError('The link does not contain a valid arXiv paper identifier.')
    return identifier


class ArxivRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        p = urlsplit(newurl)
        if p.scheme != 'https' or p.hostname not in {'arxiv.org', 'www.arxiv.org', 'export.arxiv.org'}:
            raise ValueError('arXiv redirected the download to an unexpected host.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url: str, path: Path, limit: int = 200_000_000) -> None:
    staging = path.with_suffix(path.suffix + '.part')
    try:
        with build_opener(ArxivRedirect()).open(Request(url, headers={
            'User-Agent': 'LocalXiv/0.1 (personal local paper reader)'
        }), timeout=60) as response, staging.open('wb') as output:
            size = 0
            while chunk := response.read(64 * 1024):
                size += len(chunk)
                if size > limit:
                    raise ValueError('The arXiv download exceeds the size limit.')
                output.write(chunk)
        staging.replace(path)
    finally:
        staging.unlink(missing_ok=True)


class Metadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values: dict[str, list[str]] = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and 'name' in attrs:
            self.values.setdefault(attrs['name'], []).append(attrs.get('content', ''))


def acquire(url: str, destination: Path) -> dict:
    requested = paper_id(url)
    destination.mkdir(parents=True, exist_ok=True)
    abstract = destination / 'abstract.html'
    download(f'https://arxiv.org/abs/{quote(requested, safe="/")}', abstract, 4_000_000)
    page = abstract.read_text(encoding='utf-8')
    parser = Metadata()
    parser.feed(page)
    base = re.sub(r'v\d+$', '', requested)
    versions = re.findall(re.escape(base) + r'v([1-9]\d*)', html.unescape(page))
    if re.search(r'v\d+$', requested):
        pinned = requested
    elif versions:
        pinned = base + 'v' + str(max(map(int, versions)))
    else:
        raise ValueError('arXiv did not report a paper version. Retry when its abstract page is available.')
    titles = parser.values.get('citation_title', [])
    if not titles or not titles[0].strip():
        raise ValueError('arXiv did not return paper metadata.')
    # Fetch the pinned abstract again if the original URL resolved to latest.
    if pinned != requested:
        download(f'https://arxiv.org/abs/{quote(pinned, safe="/")}', abstract, 4_000_000)
        parser = Metadata()
        parser.feed(abstract.read_text(encoding='utf-8'))
    metadata = {
        'arxiv_id': pinned, 'title': parser.values.get('citation_title', titles)[0],
        'authors': ', '.join(parser.values.get('citation_author', [])),
        'original_url': url, 'arxiv_url': f'https://arxiv.org/abs/{pinned}',
    }
    try:
        download(f'https://arxiv.org/pdf/{quote(pinned, safe="/")}', destination / 'original.pdf')
        if not (destination / 'original.pdf').read_bytes().startswith(b'%PDF-'):
            raise ValueError('arXiv returned a non-PDF response.')
    except Exception as error:
        metadata['pdf_error'] = str(error)
        (destination / 'original.pdf').unlink(missing_ok=True)
    (destination / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    download(f'https://arxiv.org/src/{quote(pinned, safe="/")}', destination / 'source')
    metadata['source_digest'] = hashlib.sha256((destination / 'source').read_bytes()).hexdigest()
    (destination / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    return metadata
