"""Numeric Pandoc citations, preserving parsed prefixes, suffixes, and authors."""
import json
import re
from pathlib import Path


def citation_options(source: Path, bibliography: list) -> list[str]:
    if not bibliography:
        return ['--csl', str(Path(__file__).parent / 'assets/ieee.csl')]
    entries = []
    for number, entry in enumerate(bibliography, 1):
        author = re.sub(r'\s*\(?\b(?:19|20)\d{2}[a-z]?\)?.*$', '', entry.label).strip()
        if author.isdecimal():
            author = ''
        entries.append(f'[{json.dumps(entry.key,ensure_ascii=False)}] = {{number={number}, author={json.dumps(author,ensure_ascii=False)}}}')
    path = source / '.numeric-citations.lua'
    path.write_text('local references = {' + ',\n'.join(entries) + '}\n' + r'''
function Cite(el)
  local output = pandoc.List()
  local function append(inlines)
    for _, inline in ipairs(inlines or {}) do output:insert(inline) end
  end
  local keys = {}
  for index, citation in ipairs(el.citations) do
    local entry = references[citation.id]
    if not entry then error('Missing bibliography key: ' .. citation.id) end
    keys[#keys+1] = citation.id
    if index > 1 then output:insert(pandoc.Str(';')); output:insert(pandoc.Space()) end
    append(citation.prefix)
    if #citation.prefix > 0 then output:insert(pandoc.Space()) end
    if citation.mode == 'AuthorInText' then
      if entry.author == '' then error('A narrative citation has no retained author label: ' .. citation.id) end
      output:insert(pandoc.Str(entry.author)); output:insert(pandoc.Space())
    end
    output:insert(pandoc.Str('['))
    local anchor = citation.id:gsub('[^%w_.:-]+','-'):gsub('^-',''):gsub('-$','')
    output:insert(pandoc.Link(tostring(entry.number), '#ref-' .. anchor))
    if #citation.suffix > 0 then output:insert(pandoc.Str(',')); output:insert(pandoc.Space()); append(citation.suffix) end
    output:insert(pandoc.Str(']'))
  end
  return pandoc.Span(output, pandoc.Attr('', {'citation'}, {['data-cites']=table.concat(keys,' '), ['data-numeric']='true'}))
end
''')
    return ['--lua-filter', str(path)]
