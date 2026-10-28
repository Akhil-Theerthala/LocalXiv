"""The Code link: the Paper's own code repository or project page, from its retained text."""
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from papers.reading import BIBLIOGRAPHY_MARKERS

CODE_HOSTS = {'github.com', 'gitlab.com', 'huggingface.co'}
# Venues, identifiers, and licences are never the Paper's own code or project page.
SKIPPED_HOSTS = {'arxiv.org', 'doi.org', 'dx.doi.org', 'openreview.net', 'aclanthology.org', 'neurips.cc',
                 'proceedings.neurips.cc', 'creativecommons.org', 'scholar.google.com', 'w3.org'}
# One of these phrases in the 80 characters before a link marks it as the Paper's own code or page.
PHRASES = ('our code', 'code is available', 'code available', 'code and models', 'code and notebooks', 'code:', 'code,',
           'we release', 'project page', 'the code we used', 'releasing', 'available at', 'can be found at',
           'implementation', 'open-source')
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}


class Links(HTMLParser):
    """Each link with the text before it and whether it sits in a bibliography or in the arXiv Comments cell."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.links, self.stack = '', [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        markers = set(' '.join(attrs.get(name) or '' for name in ('class', 'role', 'epub:type')).split())
        if tag == 'a' and attrs.get('href'):
            marks = [m for _, m in self.stack] + [markers]
            self.links.append((attrs['href'], self.text[-80:].lower(), any(m & BIBLIOGRAPHY_MARKERS for m in marks),
                               any({'tablecell', 'comments'} <= m for m in marks)))
        if tag not in VOID:
            self.stack.append((tag, markers))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.stack.pop()

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.text = (self.text + re.sub(r'\s+', ' ', data))[-200:]


def normalize(url):
    """Return the link as https, without www., trailing punctuation, a trailing slash, or .git; or '' for no link."""
    url = url.strip().rstrip('.,;:)')
    parts = urlsplit(url)
    host = (parts.hostname or '').removeprefix('www.')
    if parts.scheme not in ('http', 'https') or not host or host in SKIPPED_HOSTS:
        return ''
    path = parts.path.rstrip('/').removesuffix('.git').rstrip('/')
    if host in ('github.com', 'gitlab.com'):
        # A repository is /<owner>/<repo>. An owner alone is often a URL that the PDF text layer cut inside a name.
        path = '/'.join(path.split('/')[:3])
        if path.count('/') < 2:
            return ''
    return f'https://{host}{path}' + (f'?{parts.query}' if parts.query else '')


def link(url):
    url = normalize(url)
    return url and {'url': url, 'kind': 'code' if urlsplit(url).hostname in CODE_HOSTS else 'project'}


def html_links(path):
    try:
        text = Path(path).read_text(errors='replace')
    except OSError:
        return []
    parser = Links()
    parser.feed(text)
    return parser.links


def pdf_links(document):
    found = []
    for passage in document.get('passages', []):
        text = passage.get('text', '')
        # The PDF text layer breaks a long URL after a slash or a hyphen.
        while (joined := re.sub(r'(https?://\S*[/-])\n(?=\S)', r'\1', text)) != text:
            text = joined
        for line in text.splitlines():
            if line.strip() in ('References', 'Bibliography'):
                return found
            found += [(match[0], line[:match.start()][-80:].lower()) for match in re.finditer(r'https?://\S+', line)]
    return found


def merge_code(local, official):
    """Add the stars of the official repository to the same local link, or put it in place of a project page."""
    url = official and normalize(official['url'])
    if not url:
        return local
    if local and local['url'] == url:
        return dict(local, stars=official['stars'])
    if not local or local['kind'] == 'project':
        return {'url': url, 'kind': 'code', 'stars': official['stars'], 'source': 'paperswithcode'}
    return local


def find_code(directory, document):
    """Return the first own-code link, else the first project page, else None."""
    found = []
    for href, before, bibliography, comments in html_links(Path(directory) / 'abstract.html'):
        if comments:
            row = link(href)
            if row and (row['kind'] == 'code' or re.search('website|project|page', before[-40:])):
                found.append(row)
        elif not bibliography and any(phrase in before for phrase in PHRASES):
            found.append(link(href))
    if document.get('format') == 'pdf':
        found += [link(href) for href, before in pdf_links(document) if any(phrase in before for phrase in PHRASES)]
    for chapter in document.get('chapters', []):
        found += [link(href) for href, before, bibliography, _ in html_links(Path(directory) / chapter['path'])
                  if not bibliography and any(phrase in before for phrase in PHRASES)]
    found = [row for row in found if row]
    return next((row for row in found if row['kind'] == 'code'), found[0] if found else None)
