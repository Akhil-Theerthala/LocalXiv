"""Paper search: find arXiv papers by title, author, or topic through Semantic Scholar, then arXiv."""
import http.client
import json
import re
import threading
import time
import xml.etree.ElementTree as ET
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from papers.acquire import ARXIV_ID, ArxivRedirect
from papers.settings import get_key

S2 = 'https://api.semanticscholar.org'
ATOM = '{http://www.w3.org/2005/Atom}'
PREFIX = re.compile(r'\b(?:ti|au|abs|co|jr|cat|rn|all):')
# arXiv's Lucene index drops these words, so an all:<word> term with one of them matches nothing.
STOP_WORDS = frozenset('a an and are as at be but by for if in into is it no not of on or such that the their then '
                       'there these they this to was will with'.split())
GAPS = {'arxiv': 3, 'semantic_scholar': 1}
FAILURES = (OSError, ValueError, http.client.HTTPException, ET.ParseError)
LIMIT = 1_000_000
clock, sleep = time.monotonic, time.sleep
lock = threading.Lock()
cache = {}  # (source, query, limit) -> (expires, rows)
next_call = {'arxiv': 0.0, 'semantic_scholar': 0.0}
s2_resume = 0.0
latest = 0


class Stale(Exception):
    pass


def fetch(url, headers):
    """Send one GET and return its status and body."""
    request = Request(url, headers={'User-Agent': 'LocalXiv/0.1 (personal local paper reader)', **headers})
    try:
        with build_opener(ArxivRedirect()).open(request, timeout=8) as response:
            body = response.read(LIMIT + 1)
            if len(body) > LIMIT:
                raise ValueError('The search response exceeds the size limit.')
            return response.status, body
    except HTTPError as error:
        with error:
            return error.code, b''


def squash(text):
    return ' '.join((text or '').split())


def semantic_scholar(query, limit, key):
    # S2 finds nothing for hyphenated terms.
    status, body = fetch(S2 + '/graph/v1/paper/search?' + urlencode(
        {'query': query.replace('-', ' '), 'limit': 2 * limit, 'fields': 'title,year,authors,externalIds,abstract'},
        safe=','), {'x-api-key': key} if key else {})
    if status != 200:
        raise ValueError(f'Semantic Scholar answered HTTP {status}.')
    rows = []
    for row in json.loads(body).get('data') or []:
        identifier = re.sub(r'v\d+$', '', (row.get('externalIds') or {}).get('ArXiv') or '')
        if ARXIV_ID.fullmatch(identifier):
            rows.append({'arxiv_id': identifier, 'title': squash(row.get('title')),
                         'authors': [a['name'] for a in row.get('authors') or [] if a.get('name')],
                         'year': row.get('year'), 'abstract': squash(row.get('abstract'))})
    return rows[:limit]


def arxiv_query(query, limit):
    """Return the arXiv search_query, or '' when no word is left."""
    if PREFIX.search(query):
        return query
    words = re.sub(r'["()]', ' ', query).split()
    if limit == 8:
        return f'ti:"{" ".join(words)}"' if words else ''
    return ' AND '.join('all:' + word for word in words if word.lower() not in STOP_WORDS)


def arxiv(query, limit):
    status, body = fetch('https://export.arxiv.org/api/query?' + urlencode(
        {'search_query': query, 'max_results': limit, 'sortBy': 'relevance'}), {})
    if status != 200:
        raise ValueError(f'arXiv answered HTTP {status}.')
    rows = []
    for entry in ET.fromstring(body).iter(ATOM + 'entry'):
        match = re.fullmatch(r'https?://arxiv\.org/abs/(.+?)(?:v\d+)?', (entry.findtext(ATOM + 'id') or '').strip())
        if match and ARXIV_ID.fullmatch(match[1]):
            published = entry.findtext(ATOM + 'published') or ''
            rows.append({'arxiv_id': match[1], 'title': squash(entry.findtext(ATOM + 'title')),
                         'authors': [squash(name.text) for name in entry.findall(f'{ATOM}author/{ATOM}name')],
                         'year': int(published[:4]) if published[:4].isdigit() else None,
                         'abstract': squash(entry.findtext(ATOM + 'summary'))})
    return rows


def wait(source, ticket):
    """Hold one service's gate; drop a Suggestions request that a newer one replaced during the wait."""
    while True:
        with lock:
            now = clock()
            if now >= next_call[source]:
                # arXiv allows one connection, so the gap counts from the end of the call. lookup() reopens the gate.
                next_call[source] = float('inf')
                return
            delay = min(next_call[source] - now, GAPS[source])
        sleep(delay)
        if ticket is not None and ticket != latest:
            raise Stale()


def lookup(source, query, limit, ticket, key=''):
    """Return cached or fresh rows, or None when the service fails or S2 cools down."""
    global s2_resume
    s2 = source == 'semantic_scholar'
    with lock:
        hit = cache.get((source, query, limit))
        if hit and clock() < hit[0]:
            return hit[1]
        if s2 and clock() < s2_resume:
            return None
    gated = not s2 or key
    if gated:
        wait(source, ticket)
    try:
        if s2 and clock() < s2_resume:  # Another request's S2 call failed during the wait.
            return None
        rows = semantic_scholar(query, limit, key) if s2 else arxiv(query, limit)
    except FAILURES:
        if s2:
            with lock:
                s2_resume = clock() + 60  # The S2 license forbids working around its rate limits.
        return None
    finally:
        if gated:
            with lock:
                next_call[source] = clock() + GAPS[source]
    with lock:
        cache.pop((source, query, limit), None)
        cache[source, query, limit] = (clock() + 600, rows)
        while len(cache) > 100:
            del cache[next(iter(cache))]
    return rows


def paper_search(query, limit):
    global latest
    with lock:
        if limit == 8:
            latest += 1
        ticket = latest if limit == 8 else None
    try:
        if not PREFIX.search(query):
            try:
                key = get_key(S2)
            except RuntimeError:
                key = ''
            rows = lookup('semantic_scholar', query, limit, ticket, key)
            if rows:
                return {'results': rows, 'source': 'semantic_scholar'}
        search_query = arxiv_query(query, limit)
        rows = lookup('arxiv', search_query, limit, ticket) if search_query else []
    except Stale:
        return {'results': []}
    return {'results': [], 'error': 'unavailable'} if rows is None else {'results': rows, 'source': 'arxiv'}
